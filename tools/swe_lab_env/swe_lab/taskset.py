"""swe-lab: the tiered code-repair taskset, scored by an executing verifier.

Two task modes share one audited verifier:

  reply  (default) the model sees the tier's files in the prompt and answers with
         the corrected contents, one fenced block per file behind a
         `### FILE: <path>` line. The reward parses that reply.
  patch  the tier's repository is staged INTO the agent's runtime, the model is
         told to fix the failing tests in place with its tools, and the reward
         reads the runtime's final tree. Nothing is parsed from the reply.

The modes exist because a harness comparison is meaningless in `reply` mode: the
`null` loop exposes no tools, so a tool-using harness and a chat loop differ only
in prompt wrapping. `patch` is the mode where `bash`/`edit` and the runtime
actually do the work, so harness differences can show up.

Both modes score through tools/swe_lab/terrain.py: `target_fix_fraction` is the
fraction of the tier's target tests actually fixed, gated to zero when a test file
was modified or a previously passing test regressed. `shaped` is recorded
alongside at weight 0.

Needs no container: `null` and `bash` both run on the subprocess runtime.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import verifiers.v1 as vf

SWE_LAB = Path(__file__).resolve().parents[2] / "swe_lab"
sys.path.insert(0, str(SWE_LAB))

import ladder as ladder_defs
import terrain as terrain_verifier

FILE_MARKER = re.compile(r"^###\s*FILE:\s*(\S+)\s*$", re.MULTILINE)
CODE_BLOCK = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)

SYSTEM_REPLY = (
    "You are a careful Python engineer. Reply with the complete corrected contents "
    "of every file you change, one fenced code block per file, each preceded by a "
    "line `### FILE: <relative path>`. Change nothing else."
)
SYSTEM_PATCH = (
    "You are a coding agent working in a repository in your current working "
    "directory. Use your tools to inspect the code, run the test suite, and fix the "
    "defect. Do not weaken or modify any test file."
)

_BASELINES: dict[str, dict] = {}


def _baseline(tier_id: str, files: dict) -> dict:
    """Baseline verdict for a tier, computed once and cached."""
    if tier_id in _BASELINES:
        return _BASELINES[tier_id]
    with TemporaryDirectory() as tmp:
        tree = _write_tree(Path(tmp) / "repo", files)
        _, _, per_test = terrain_verifier.run_repo(tree)
    baseline = {
        "per_test": per_test,
        "passing": [t for t, v in per_test.items() if v == "PASSED"],
        "failing": [t for t, v in per_test.items() if v != "PASSED"],
    }
    _BASELINES[tier_id] = baseline
    return baseline


def _write_tree(tree: Path, files: dict) -> Path:
    for rel, content in files.items():
        path = tree / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return tree


def build_prompt(tier_id: str, tier: dict, mode: str) -> str:
    baseline = _baseline(tier_id, tier["files"])
    failures = ["  " + name for name in baseline["failing"]]
    if mode == "patch":
        return "\n".join(
            [
                "The repository in your working directory has a failing test suite.",
                "",
                "Files:",
                *["  " + rel for rel in sorted(tier["files"])],
                "",
                "Running `python -m pytest` reports these failures:",
                *failures,
                "",
                "Fix the defect(s) in place with your tools so that every test passes. "
                "Do not weaken or modify any test file.",
            ]
        )
    parts = ["This repository has a failing test suite.", ""]
    for rel, content in sorted(tier["files"].items()):
        parts += ["--- %s ---" % rel, content]
    parts += [
        "Running `python -m pytest` reports these failures:",
        *failures,
        "",
        "Fix the defect(s) without breaking any test that currently passes. You may "
        "change or add non-test files, including new helper modules. Do not modify "
        "any test file.",
        "Reply with the complete corrected contents of every file you change, one "
        "fenced code block per file, each preceded by a line `### FILE: <relative path>`.",
    ]
    return "\n".join(parts)


def parse_proposals(reply: str, known: dict) -> dict:
    """Map a reply to {relative path: contents} (reply mode only)."""
    proposals: dict[str, str] = {}
    markers = list(FILE_MARKER.finditer(reply or ""))
    if markers:
        for index, marker in enumerate(markers):
            start = marker.end()
            end = markers[index + 1].start() if index + 1 < len(markers) else len(reply)
            segment = reply[start:end]
            block = CODE_BLOCK.search(segment)
            # Tolerance matters: models often emit the file body after the marker
            # without the requested fence. Rejecting that would score a correct
            # repair as zero, which is a measurement error rather than a model one.
            body = block.group(1) if block else segment
            body = "\n".join(line for line in body.splitlines() if not line.strip().startswith("```"))
            if body.strip():
                proposals[marker.group(1).strip()] = body.strip() + "\n"
        return proposals
    block = CODE_BLOCK.search(reply or "")
    if block:
        primary = next((rel for rel in sorted(known) if not Path(rel).name.startswith("test_")), None)
        if primary:
            proposals[primary] = block.group(1)
    return proposals


def look_like_test(rel: str) -> bool:
    return Path(rel).name.startswith("test_")


class SweLabData(vf.TaskData):
    tier: str = ""
    files: dict[str, str] = {}
    """The tier's initial repository contents."""
    targets: list[str] = []
    """Baseline-failing tests the repair must fix."""
    budgets: dict = {}
    mode: str = "reply"
    """`reply` scores the answer text; `patch` scores the runtime's final tree."""


class SweLabTask(vf.Task[SweLabData]):
    async def setup(self, trace: vf.Trace, runtime) -> None:
        """Stage the repository into the agent's runtime (patch mode)."""
        if self.data.mode != "patch":
            return
        for rel, content in self.data.files.items():
            await runtime.write(rel, content.encode())

    @vf.stop
    async def single_turn(self, trace: vf.Trace) -> bool:
        # Patch mode needs room to inspect and iterate; reply mode answers once.
        return self.data.mode != "patch" and trace.num_turns >= 1

    async def _score_patch(self, runtime) -> dict | None:
        """Snapshot the runtime's final tree on the host and score it."""
        listing = await runtime.run(
            ["bash", "-lc", "find . -type f -not -path '*/__pycache__/*' | sed 's|^\\./||' | sort"], {}
        )
        rels = [line for line in listing.stdout.split("\n") if line.strip()]
        if not rels:
            return None
        baseline = _baseline(self.data.tier, self.data.files)
        with TemporaryDirectory() as tmp:
            tree = Path(tmp) / "repo"
            for rel in rels:
                path = tree / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(await runtime.read(rel))
            tampered = any(
                look_like_test(rel) and (tree / rel).read_text() != self.data.files.get(rel)
                for rel in rels
                if look_like_test(rel)
            )
            return terrain_verifier.verdict_for_tree(tree, baseline, tampered=tampered)

    def _score_reply(self, reply: str) -> dict | None:
        baseline = _baseline(self.data.tier, self.data.files)
        proposals = parse_proposals(reply, self.data.files)
        if not proposals:
            return None
        with TemporaryDirectory() as tmp:
            tree = Path(tmp) / "repo"
            _write_tree(tree, self.data.files)
            for rel, content in proposals.items():
                if rel in self.data.files:
                    (tree / rel).write_text(content)
            tampered = any(
                look_like_test(rel) and proposals.get(rel, self.data.files[rel]) != self.data.files[rel]
                for rel in self.data.files
            )
            return terrain_verifier.verdict_for_tree(tree, baseline, tampered=tampered)

    async def _verdict(self, trace: vf.Trace, runtime):
        if self.data.mode == "patch":
            return await self._score_patch(runtime) if runtime is not None else None
        return self._score_reply(trace.last_reply or "")

    @vf.reward(weight=1.0)
    async def target_fix_fraction(self, trace: vf.Trace, runtime=None) -> float:
        verdict = await self._verdict(trace, runtime)
        return 0.0 if verdict is None else terrain_verifier.REWARDS["target_fix_fraction"](verdict)

    @vf.reward(weight=0.0)
    async def shaped(self, trace: vf.Trace, runtime=None) -> float:
        verdict = await self._verdict(trace, runtime)
        return 0.0 if verdict is None else terrain_verifier.REWARDS["shaped"](verdict)


class SweLabConfig(vf.TasksetConfig):
    tiers: list[str] = []
    """Restrict the taskset to these tier ids; empty means every tier."""
    mode: str = "reply"
    """Task mode for every tier: `reply` or `patch`."""


class SweLabTaskset(vf.Taskset[SweLabTask, SweLabConfig]):
    def load(self) -> list[SweLabTask]:
        tiers = ladder_defs.build_tiers()
        wanted = self.config.tiers or list(tiers)
        mode = self.config.mode
        tasks = []
        for index, tier_id in enumerate(wanted):
            tier = tiers[tier_id]
            tasks.append(
                SweLabTask(
                    SweLabData(
                        idx=index,
                        name="%s-%s" % (tier_id, mode) if mode != "reply" else tier_id,
                        prompt=build_prompt(tier_id, tier, mode),
                        system_prompt=SYSTEM_PATCH if mode == "patch" else SYSTEM_REPLY,
                        tier=tier_id,
                        files=dict(tier["files"]),
                        targets=list(tier["targets"]),
                        budgets=dict(tier["budgets"]),
                        mode=mode,
                    ),
                    self.config.task,
                )
            )
        return tasks