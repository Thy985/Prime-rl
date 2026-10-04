"""swe-bench: real SWE-bench Verified instances, scored by an executing verifier.

Distinct from swe-lab in three ways that matter for the measurement:

  * the repository is a real GitHub checkout staged from a local cache -- no
    container, and the prompt carries the issue text rather than file contents;
  * the oracle `test_patch` is never exposed to the model and is applied only at
    scoring time. The agent sees a repository whose visible tests still pass,
    which is the condition the harness effect is meant to be tested under;
  * the reward gates to zero when the agent edits a file the oracle touches --
    the only way that happens is by knowing the test patch.

Test runners differ per repository, so each instance carries a profile:

  django  `python tests/runtests.py <target> --parallel=1`, names recorded as
          `method (module.tests.Class.method)` -- normalised to the dotted form
  pytest  `python -m pytest -q <nodeid>`, names as `path/file.py::test`

One process per test, so pass/fail is the exit code and no output is parsed.

Scoring mirrors the official swebench eval script: oracle test files are first
reset to the base commit (an agent's edits to them are discarded, not rewarded),
then the test patch is applied with `git apply`, then each oracle test runs once.
`git apply` works on the plain snapshot tree -- no git metadata needed.

No container: runs on the subprocess runtime. Set SWE_REAL_PY to the interpreter
holding the repos' test dependencies.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import verifiers.v1 as vf

_MANIFEST = Path(__file__).resolve().parent / "manifest.json"

SYSTEM_PATCH = (
    "You are a coding agent working in a real open-source repository, checked out "
    "in your current working directory. Its test dependencies are installed, and "
    "the repo's own test suite is runnable -- django repos use "
    "`PYTHONPATH=. python tests/runtests.py <test>`, others use pytest. Use your "
    "tools to inspect the code and fix the reported defect in place. Do not change "
    "or weaken any test file: a fix that edits tests does not count."
)

_DJANGO_NAME = re.compile(r"^\s*(\S+)\s+\((.+?)\)\s*$")


def _norm_django(name: str) -> str:
    """`test_x (mod.tests.Class.test_x)` -> `mod.tests.Class.test_x`."""
    m = _DJANGO_NAME.match(name)
    return m.group(2) if m else name


class SWERealData(vf.TaskData):
    instance_id: str = ""
    repo: str = ""
    cached_repo: str = ""
    """Local checkout of the repo at the instance's base_commit."""
    profile: str = "django"
    """`django` or `pytest` -- selects the runner and the test-name format."""
    problem_statement: str = ""
    fail_to_pass: list[str] = []
    """Oracle tests failing at base that must pass after the fix."""
    pass_to_pass: list[str] = []
    """Oracle tests passing at base that must not regress."""
    oracle_files: list[str] = []
    """Paths the test_patch touches; editing one voids the reward."""
    test_patch: str = ""


class SWERealTask(vf.Task[SWERealData]):
    @vf.stop
    async def single_turn(self, trace: vf.Trace) -> bool:
        # Patch mode needs room to inspect and iterate; max_turns bounds it.
        return False

    async def setup(self, trace: vf.Trace, runtime) -> None:
        """Stage the real checkout into the agent's runtime workdir."""
        src = Path(self.data.cached_repo)
        if not src.is_dir():
            raise RuntimeError(f"{self.data.instance_id}: no cached repo at {src}")
        await runtime.run(["bash", "-lc", "cp -a %s/. ." % str(src)], {})
        # The gold fix is a descendant of base_commit in the public history; strip
        # every ref that could reveal it, as the official swebench setup does.
        await runtime.run(
            ["bash", "-lc",
             'git remote remove origin 2>/dev/null; '
             'git tag -l | while read t; do '
             'C=$(git rev-list -n 1 "$t"); '
             'T=$(git show -s --format=%ci "$C"); '
             'B=$(git show -s --format=%ci HEAD); '
             '[[ "$T" > "$B" ]] && git tag -d "$t"; done 2>/dev/null; '
             'git reflog expire --expire=now --all 2>/dev/null; true'],
            {},
        )

    async def _snapshot(self, runtime, root: Path) -> list[str]:
        """Copy the runtime's final tree onto the host; return the file list."""
        listing = await runtime.run(
            [
                "bash",
                "-lc",
                "find . -type f -not -path '*/.git/*' -not -path '*/__pycache__/*' "
                "-not -name '*.pyc' | sed 's|^\\./||' | sort",
            ],
            {},
        )
        rels = [line for line in listing.stdout.splitlines() if line.strip()]
        for rel in rels:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(await runtime.read(rel))
        return rels

    def _run_test(self, tree: Path, target: str) -> bool:
        """One test as one process; pass/fail is the exit code."""
        argv = (
            [SWE_REAL_PY, "tests/runtests.py", target, "--parallel=1"]
            if self.data.profile == "django"
            else [SWE_REAL_PY, "-m", "pytest", "-q", target]
        )
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(tree),
            "HOME": os.environ.get("HOME", "/root"),
            "LANG": "C.UTF-8",
        }
        proc = subprocess.run(argv, cwd=str(tree), env=env, capture_output=True, timeout=300)
        return proc.returncode == 0

    def _verdict(self, snapshot: list[str], tree: Path, src: Path) -> dict:
        norm = _norm_django if self.data.profile == "django" else (lambda n: n)
        # Tampering is judged against the base commit BEFORE the oracle lands.
        oracle = set(self.data.oracle_files)
        tampered = [
            rel
            for rel in snapshot
            if rel in oracle
            and src.joinpath(rel).is_file()
            and tree.joinpath(rel).read_bytes() != src.joinpath(rel).read_bytes()
        ]
        # Swebench semantics: oracle test files are reset to base, so an agent's
        # edits to them are discarded and the test patch applies deterministically.
        for rel in oracle:
            if src.joinpath(rel).is_file():
                path = tree / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(src.joinpath(rel).read_bytes())
        # The oracle is applied on this host copy only, never in the agent's runtime.
        (tree / ".oracle.patch").write_text(self.data.test_patch)
        apply_ = subprocess.run(
            ["git", "apply", ".oracle.patch"], cwd=str(tree), capture_output=True, timeout=120
        )
        if apply_.returncode != 0:
            return {"oracle_apply": False, "tampered": tampered}
        f2p = [(n, self._run_test(tree, norm(n))) for n in self.data.fail_to_pass]
        p2p = [(n, self._run_test(tree, norm(n))) for n in self.data.pass_to_pass]
        return {"oracle_apply": True, "tampered": tampered, "f2p": f2p, "p2p": p2p}

    @vf.reward(weight=1.0)
    async def resolve(self, trace: vf.Trace, runtime=None) -> float:
        if runtime is None:
            return 0.0
        with TemporaryDirectory() as tmp:
            tree = Path(tmp) / "repo"
            tree.mkdir()
            snapshot = await self._snapshot(runtime, tree)
            verdict = self._verdict(snapshot, tree, Path(self.data.cached_repo))
        if not verdict["oracle_apply"] or verdict["tampered"]:
            return 0.0
        return 1.0 if all(ok for _, ok in verdict["f2p"]) and all(ok for _, ok in verdict["p2p"]) else 0.0

    @vf.reward(weight=0.0)
    async def f2p_fraction(self, trace: vf.Trace, runtime=None) -> float:
        if runtime is None:
            return 0.0
        with TemporaryDirectory() as tmp:
            tree = Path(tmp) / "repo"
            tree.mkdir()
            snapshot = await self._snapshot(runtime, tree)
            verdict = self._verdict(snapshot, tree, Path(self.data.cached_repo))
        if not verdict["oracle_apply"]:
            return 0.0
        fixed = sum(1 for _, ok in verdict["f2p"] if ok)
        return fixed / len(verdict["f2p"]) if verdict["f2p"] else 0.0


class SWERealConfig(vf.TasksetConfig):
    instances: list[str] = []
    """Restrict to these instance_ids; empty means every instance in the manifest."""


# H_A' control: the behavioural content of the three H_D phase prompts, with no
# phase numbering, no per-turn gating and no edit-tool removal. It isolates how much of
# the H_D effect is static instruction ("inspect, then edit early, then verify") versus
# runtime-enforced structure. Set SWE_REAL_H_A_PRIME=1 to append it.
H_A_PRIME_INSTRUCTION = (
    "How to spend these turns: first spend a turn or two with bash locating the code "
    "that matters, then make the edit on disk as early as possible instead of only "
    "describing the change, then re-run the failing tests, read what they print, and "
    "repair whatever still fails before you run out of turns."
)


def system_prompt() -> str:
    if os.environ.get("SWE_REAL_H_A_PRIME") == "1":
        return SYSTEM_PATCH + "\n\n" + H_A_PRIME_INSTRUCTION
    return SYSTEM_PATCH


class SWERealTaskset(vf.Taskset[SWERealTask, SWERealConfig]):
    def load(self) -> list[SWERealTask]:
        rows = json.loads(_MANIFEST.read_text())["instances"]
        wanted = set(self.config.instances)
        tasks = []
        prompt = system_prompt()
        for index, row in enumerate(rows):
            if wanted and row["instance_id"] not in wanted:
                continue
            tasks.append(
                SWERealTask(
                    SWERealData(
                        idx=index,
                        name=row["instance_id"],
                        prompt=row["problem_statement"],
                        system_prompt=prompt,
                        instance_id=row["instance_id"],
                        repo=row["repo"],
                        cached_repo=row["cached_repo"],
                        profile=row["profile"],
                        problem_statement=row["problem_statement"],
                        fail_to_pass=list(row["FAIL_TO_PASS"]),
                        pass_to_pass=list(row["PASS_TO_PASS"]),
                        oracle_files=list(row["oracle_files"]),
                        test_patch=row["test_patch"],
                    ),
                    self.config.task,
                )
            )
        return tasks


SWE_REAL_PY = os.environ.get("SWE_REAL_PY", "python")
__all__ = ["SWERealTaskset"]
