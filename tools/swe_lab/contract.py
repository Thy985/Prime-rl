"""SWE task/environment contract: the fixed facts of one task, plus state hashing.

This is the experiment-control layer. It owns only what verifiers.v1 does not
carry: the initial world's hash, the environment fingerprint, the run directory
layout and the diff between initial and final state. Task semantics (prompt,
timeouts, network and resource policy) deliberately mirror verifiers' TaskData /
TaskTimeout / TaskResources so this maps onto a real Taskset later.

run_dir layout:
    task.json  env_fingerprint.json  initial/  work/  final/
    initial_state.json  final_state.json  diff.patch
"""

from __future__ import annotations

import difflib
import hashlib
import json
import locale
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixture"

TASK_ID = "swe_lab-fixture-2defect"
TASK_DESCRIPTION = (
    "The test suite in this repository fails for two independent reasons: "
    "median() ignores the even-length average, and parse_ranges() uses an "
    "exclusive upper bound."
)
TARGET_TESTS = [
    "test_median_even",
    "test_parse_ranges_one_range",
    "test_parse_ranges_two_ranges",
]
BASELINE_PASSING = ["test_chunk_basic", "test_chunk_empty", "test_median_odd", "test_parse_ranges_single"]
TIMEOUTS = {"setup": 30.0, "agent": 600.0, "finalize": 30.0, "scoring": 60.0}
RESOURCES = {"cpu": 1.0, "memory": 1024.0, "gpu": None, "disk": None}
TOOL_POLICY = {"shell": True, "edit": True, "search": False}
NETWORK_POLICY = {"allow": ["*"], "block": []}
TEST_FILE_PATTERNS = ("test_",)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree_hash(root: Path) -> str:
    """Content hash of a tree: sorted relative paths plus each file's digest.

    Ignores volatile artifacts so a hash change always means a real source change.
    """
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if "__pycache__" in rel or rel.endswith(".pyc"):
            continue
        entries.append(f"{rel}:{sha256_bytes(path.read_bytes())}")
    return sha256_bytes("\n".join(entries).encode())


def file_hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes()) if path.is_file() else ""


def tests_modified(initial: Path, final: Path) -> bool:
    """Tampering = any test file whose content differs from the initial world."""
    for path in initial.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(initial).as_posix()
        if not Path(rel).name.startswith(TEST_FILE_PATTERNS):
            continue
        if file_hash(path) != file_hash(final / rel):
            return True
    for path in final.rglob("*"):
        if path.is_file() and Path(path.relative_to(final).as_posix()).name.startswith(TEST_FILE_PATTERNS):
            if not (initial / path.relative_to(final).as_posix()).exists():
                return True
    return False


def env_fingerprint(agent: str, harness: str, runtime: str, workdir: str) -> dict:
    """Everything that could silently differ between two runs of the same task."""
    crlf = sum(
        1
        for path in FIXTURE.rglob("*")
        if path.is_file() and b"\r\n" in path.read_bytes()
    )
    try:
        pytest_version = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pytest_version = "unknown"
    try:
        git_version = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=60).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        git_version = "unknown"
    return {
        "os": platform.platform(),
        "path_policy": "windows" if os.name == "nt" else "posix",
        "shell": os.environ.get("SHELL", "unknown"),
        "locale": ".".join(part or "" for part in locale.getlocale()),
        "line_endings": "crlf" if crlf else "lf",
        "python": platform.python_version(),
        "pytest": pytest_version,
        "git": git_version,
        "agent": agent,
        "harness": harness,
        "runtime": runtime,
        "workdir": workdir,
        "fixture_hash": tree_hash(FIXTURE),
        "task_hash": task_hash(),
        "tool_policy": TOOL_POLICY,
        "network_policy": NETWORK_POLICY,
    }


def task_hash() -> str:
    """Stable identity of the task definition (mirrors verifiers' Task.hash())."""
    payload = json.dumps(
        {
            "task_id": TASK_ID,
            "description": TASK_DESCRIPTION,
            "target_tests": TARGET_TESTS,
            "baseline_passing": BASELINE_PASSING,
            "timeouts": TIMEOUTS,
            "resources": RESOURCES,
            "tool_policy": TOOL_POLICY,
            "network_policy": NETWORK_POLICY,
            "fixture_hash": tree_hash(FIXTURE),
        },
        sort_keys=True,
    )
    return sha256_bytes(payload.encode())


def task_json() -> dict:
    return {
        "task_id": TASK_ID,
        "description": TASK_DESCRIPTION,
        "prompt": (
            "The test suite in this repository fails. Fix the defects in "
            "calculator.py so that all tests pass. Do not modify any test file. "
            "Run the tests to verify."
        ),
        "workdir": "work",
        "base_repo_hash": tree_hash(FIXTURE),
        "initial_tree_hash": None,
        "bug_spec": {
            "median": "ignores the even-length average",
            "parse_ranges": "exclusive upper bound in range expansion",
        },
        "expected_target_tests": TARGET_TESTS,
        "expected_baseline_passing": BASELINE_PASSING,
        "timeouts": TIMEOUTS,
        "resources": RESOURCES,
        "tool_policy": TOOL_POLICY,
        "network_policy": NETWORK_POLICY,
    }


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=1, sort_keys=True))


def init_run_dir(run_root: Path, run_id: str) -> Path:
    """Materialise the initial world once; work/ is what an agent may touch."""
    run_dir = run_root / run_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    (run_dir / "initial").mkdir(parents=True)
    shutil.copytree(FIXTURE, run_dir / "initial", dirs_exist_ok=True)
    shutil.copytree(run_dir / "initial", run_dir / "work")
    (run_dir / "final").mkdir()
    return run_dir


def snapshot_final(run_dir: Path) -> Path:
    """Freeze work/ into final/ so the verifier scores an immutable state."""
    final = run_dir / "final"
    if final.exists():
        shutil.rmtree(final)
    shutil.copytree(run_dir / "work", final)
    return final


def unified_diff(initial: Path, final: Path) -> str:
    chunks = []
    rels = sorted(
        {p.relative_to(initial).as_posix() for p in initial.rglob("*") if p.is_file()}
        | {p.relative_to(final).as_posix() for p in final.rglob("*") if p.is_file()}
    )
    for rel in rels:
        if "__pycache__" in rel or rel.endswith(".pyc"):
            continue
        before = (initial / rel).read_text().splitlines(keepends=True) if (initial / rel).is_file() else []
        after = (final / rel).read_text().splitlines(keepends=True) if (final / rel).is_file() else []
        if before == after:
            continue
        chunks.extend(
            difflib.unified_diff(before, after, fromfile=f"a/{rel}", tofile=f"b/{rel}")
        )
    return "".join(chunks)