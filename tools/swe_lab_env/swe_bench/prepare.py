"""Stage SWE-bench Verified instances for the containerless swe_bench taskset.

Downloads the Verified split, keeps the instances that can actually be scored on
this host, clones each repository at its base_commit into a per-commit cache
directory, and writes manifest.json.

The filters are deliberate, not cosmetic:

  * clean test names. A handful of Verified rows record FAIL_TO_PASS/PASS_TO_PASS
    as a test docstring rather than a test name; those cannot be addressed to a
    runner, so they are dropped rather than guessed at.
  * a capped PASS_TO_PASS count. Each oracle test is one subprocess that builds a
    test database, so the cap bounds per-rollout verification time.
  * a single repo. One interpreter holds one set of test dependencies; mixing repos
    (or even commits with different requirements) into it is where a containerless
    setup silently breaks. Restricting the pilot to one repo keeps the dependency
    set one variable instead of many.

Each instance's checkout lives at CACHE/repos/<repo>-<commit12>, so instances with
different base commits never share a directory; re-running is idempotent (an
existing checkout at the right commit is reused).

usage:
  SWE_REAL_PY=/tmp/swe_deps/django_env/bin/python \
  uv run python tools/swe_lab_env/swe_bench/prepare.py --count 4 --npass 6
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

CACHE = Path(os.environ.get("SWE_REAL_CACHE", "/tmp/swe_deps"))
REPOS = CACHE / "repos"
MANIFEST = Path(__file__).resolve().parent / "manifest_candidates.json"
DATASET = ("princeton-nlp/SWE-bench_Verified", "data/test-00000-of-00001.parquet")
FILE_LINE = re.compile(r"^diff --git a/(.+?) b/(.+)$")
def _name_ok(entry: str) -> bool:
    """A test name, not a docstring: pytest node ids or django `m (C.m)` names."""
    return "test_" in entry or ".test" in entry


def _list_ok(raw: str) -> bool:
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError:
        return False
    return len(entries) > 0 and all(_name_ok(e) for e in entries)


def _load_rows():
    try:
        import pandas as pd
        from huggingface_hub import hf_hub_download
    except ImportError:
        sys.exit("prepare.py needs pandas and huggingface_hub: uv pip install pandas huggingface-hub")
    parquet = hf_hub_download(*DATASET, repo_type="dataset")
    return pd.read_parquet(parquet)


def _oracle_files(test_patch: str) -> list[str]:
    files = []
    for line in test_patch.splitlines():
        m = FILE_LINE.match(line)
        if m:
            files.append(m.group(2))
    return sorted(set(files))


def _resolve_nodeids(entry: dict) -> dict | None:
    """Address every oracle test by pytest nodeid, or None if any cannot be located.

    SWE-bench records sympy's tests as bare function names (`test_point3D`), which
    pytest cannot run as-is; the official harness runs them by selecting the name
    inside the test files its own test_patch touches. We do the same and keep the
    one-process-per-test invariant by resolving each name to the single oracle file
    that defines it.
    """
    if entry.get("profile") != "pytest":
        return entry

    def locate(name: str) -> str | None:
        if "::" in name or "/" in name:
            return name
        for rel in entry["oracle_files"]:
            path = Path(entry["cached_repo"]) / rel
            if not path.is_file():
                continue
            if re.search(rf"^\s*def\s+{re.escape(name)}\b", path.read_text(errors="replace"), re.M):
                return f"{rel}::{name}"
        return None

    resolved = dict(entry)
    for key in ("FAIL_TO_PASS", "PASS_TO_PASS"):
        names = [locate(n) for n in entry[key]]
        if any(n is None for n in names):
            return None
        resolved[key] = names
    return resolved


def _clone(repo: str, commit: str) -> Path:
    dest = REPOS / f"{repo.replace('/', '-')}-{commit[:12]}"
    if dest.is_dir():
        head = subprocess.run(
            ["git", "-C", str(dest), "rev-parse", "HEAD"], capture_output=True, timeout=60
        )
        if head.returncode == 0 and head.stdout.decode().strip() == commit:
            return dest
        shutil.rmtree(dest, ignore_errors=True)
    REPOS.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
         f"https://github.com/{repo}.git", str(dest)],
        check=True, capture_output=True, timeout=900,
    )
    subprocess.run(["git", "checkout", "-q", commit], cwd=str(dest), check=True, timeout=300)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=str(dest), capture_output=True)
    if status.stdout.strip():
        sys.exit(f"{repo}@{commit[:9]} did not check out clean")
    return dest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="django/django", help="single repo to stage")
    ap.add_argument("--count", type=int, default=5, help="instances to keep")
    ap.add_argument("--npass", type=int, default=8, help="max PASS_TO_PASS count")
    ap.add_argument("--include", default="", help="comma-separated instance ids (overrides --count)")
    ap.add_argument("--profile", default="django", help="test runner profile: django|pytest")
    ap.add_argument(
        "--python",
        default="",
        help="interpreter holding this repo's test deps (default: SWE_REAL_PY)",
    )
    ap.add_argument("--out", type=Path, default=MANIFEST, help="candidates file to write")
    args = ap.parse_args()

    rows = _load_rows()
    rows["npass"] = rows["PASS_TO_PASS"].apply(len)
    rows["nfail"] = rows["FAIL_TO_PASS"].apply(len)
    usable = []
    for _, r in rows.iterrows():
        if r["repo"] != args.repo:
            continue
        f2p, p2p = json.loads(r["FAIL_TO_PASS"]), json.loads(r["PASS_TO_PASS"])
        if len(f2p) == 0 or len(p2p) > args.npass:
            continue
        if not (_list_ok(r["FAIL_TO_PASS"]) and _list_ok(r["PASS_TO_PASS"])):
            continue
        usable.append(r)
    if not usable:
        sys.exit("no instance matches the filters")
    if args.include:
        wanted = set(args.include.split(","))
        usable = [r for r in usable if r["instance_id"] in wanted]
        if not usable:
            sys.exit("none of --include matched the filters")
    else:
        usable = usable[: args.count]

    entries = []
    for r in usable:
        dest = _clone(r["repo"], r["base_commit"])
        entry = {
            "instance_id": r["instance_id"],
            "repo": r["repo"],
            "base_commit": r["base_commit"],
            "environment_setup_commit": r["environment_setup_commit"],
            "version": r["version"],
            "cached_repo": str(dest),
            "profile": args.profile,
            "python": args.python or os.environ.get("SWE_REAL_PY", "python"),
            "problem_statement": r["problem_statement"],
            "FAIL_TO_PASS": json.loads(r["FAIL_TO_PASS"]),
            "PASS_TO_PASS": json.loads(r["PASS_TO_PASS"]),
            "oracle_files": _oracle_files(r["test_patch"]),
            "test_patch": r["test_patch"],
        }
        entry = _resolve_nodeids(entry)
        if entry is None:
            print(f"  {r['instance_id']:<28} DROPPED (no nodeid for every oracle test)")
            continue
        entries.append(entry)

    args.out.write_text(
        json.dumps(
            {"python": args.python or os.environ.get("SWE_REAL_PY", "python"), "instances": entries}, indent=1
        )
    )
    for e in entries:
        print(
            f"  {e['instance_id']:<28} nfail={len(e['FAIL_TO_PASS'])} "
            f"npass={len(e['PASS_TO_PASS'])} oracle={e['oracle_files']}"
        )
    print(f"\n{args.out}: {len(entries)} candidates (verify.py gates them into manifest.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
