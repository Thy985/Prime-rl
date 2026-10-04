"""Gate swe-bench candidates: keep only instances whose scoring is provably sound.

Each candidate must satisfy every check (the same contract the official swebench
harness validates):

  1. test_patch applies on the base checkout (`git apply`);
  2. every FAIL_TO_PASS test FAILS at base+test_patch -- otherwise there is no
     signal and a no-op agent would score 1.0;
  3. every PASS_TO_PASS test PASSES at the pristine base -- the tests are not
     broken by the environment;
  4. the gold patch applies and every FAIL_TO_PASS test PASSES with it;
  5. every PASS_TO_PASS test still PASSES with gold -- no oracle regression.

Check 3 makes the environment sound; the others make the measurement meaningful.
The informational line (P2P at base+test_patch) may legitimately be False: a
test_patch that adds database infrastructure the gold fix enables makes those
tests fail until the bug is fixed, which is expected, not a disqualifier.

usage:
  SWE_REAL_PY=/tmp/swe_deps/django_env/bin/python \
  uv run python tools/swe_lab_env/swe_bench/verify.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from huggingface_hub import hf_hub_download

CANDIDATES = Path(__file__).resolve().parent / "manifest_candidates.json"
MANIFEST = Path(__file__).resolve().parent / "manifest.json"
DATASET = ("princeton-nlp/SWE-bench_Verified", "data/test-00000-of-00001.parquet")
NAME = re.compile(r"^\s*(\S+)\s+\((.+?)\)\s*$")

SWE_REAL_PY = os.environ.get("SWE_REAL_PY", "python")


def _norm_django(name: str) -> str:
    m = NAME.match(name)
    return m.group(2) if m else name


def _run_test(tree: Path, target: str) -> bool:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(tree),
        "HOME": os.environ.get("HOME", "/root"),
        "LANG": "C.UTF-8",
    }
    proc = subprocess.run(
        [SWE_REAL_PY, "tests/runtests.py", target, "--parallel=1"],
        cwd=str(tree), env=env, capture_output=True, timeout=300,
    )
    return proc.returncode == 0


def _gate(row: dict, gold: dict) -> dict:
    src = Path(row["cached_repo"])
    iid = row["instance_id"]
    norm = _norm_django
    with tempfile.TemporaryDirectory() as td:
        tree = Path(td) / "repo"
        shutil.copytree(src, tree)

        # 3. pristine base: P2P must pass
        p2p_pristine = [(n, _run_test(tree, norm(n))) for n in row["PASS_TO_PASS"]]

        # 1. test_patch applies
        (tree / ".oracle.patch").write_text(row["test_patch"])
        apply_ = subprocess.run(
            ["git", "apply", ".oracle.patch"], cwd=str(tree), capture_output=True, timeout=120
        )
        if apply_.returncode != 0:
            return {"instance_id": iid, "ok": False, "reason": "test_patch does not apply"}

        # 2. F2P must fail at base+test_patch
        f2p_base = [(n, _run_test(tree, norm(n))) for n in row["FAIL_TO_PASS"]]
        # info: P2P at base+test_patch (may fail when the patch adds infra)
        p2p_base = [(n, _run_test(tree, norm(n))) for n in row["PASS_TO_PASS"]]

        # 4+5. gold: F2P passes, P2P passes
        (tree / ".gold.patch").write_text(gold[iid])
        gold_apply = subprocess.run(
            ["git", "apply", ".gold.patch"], cwd=str(tree), capture_output=True, timeout=120
        )
        f2p_gold = [(n, _run_test(tree, norm(n))) for n in row["FAIL_TO_PASS"]]
        p2p_gold = [(n, _run_test(tree, norm(n))) for n in row["PASS_TO_PASS"]]

    checks = {
        "p2p_pristine": all(ok for _, ok in p2p_pristine),
        "f2p_fail_at_base": all(not ok for _, ok in f2p_base),
        "gold_applies": gold_apply.returncode == 0,
        "f2p_pass_with_gold": all(ok for _, ok in f2p_gold),
        "p2p_pass_with_gold": all(ok for _, ok in p2p_gold),
    }
    ok = all(checks.values())
    detail = {
        "instance_id": iid,
        "ok": ok,
        "checks": checks,
        "p2p_base_info": all(ok for _, ok in p2p_base),
        "n_f2p": len(row["FAIL_TO_PASS"]),
        "n_p2p": len(row["PASS_TO_PASS"]),
    }
    return detail


def main() -> int:
    rows = json.loads(CANDIDATES.read_text())["instances"]
    if not rows:
        sys.exit("no candidates; run prepare.py first")
    try:
        import pandas as pd
    except ImportError:
        sys.exit("verify.py needs pandas: uv pip install pandas")
    df = pd.read_parquet(hf_hub_download(*DATASET, repo_type="dataset"))
    gold = {r["instance_id"]: r["patch"] for _, r in df.iterrows()}

    results = [_gate(row, gold) for row in rows]
    for r in results:
        chk = r["checks"]
        flags = "".join(
            "✓" if v else "✗"
            for v in [chk["p2p_pristine"], chk["f2p_fail_at_base"], chk["gold_applies"],
                      chk["f2p_pass_with_gold"], chk["p2p_pass_with_gold"]]
        )
        info = "P2P@base+tp" + ("=pass" if r["p2p_base_info"] else "=fail(info)")
        print(f"  {r['instance_id']:<26} {flags}  {info}  ({r['n_f2p']}F2P/{r['n_p2p']}P2P)"
              + ("" if r["ok"] else "  DROPPED"))

    passed = [row for row, r in zip(rows, results) if r["ok"]]
    MANIFEST.write_text(json.dumps({"python": SWE_REAL_PY, "instances": passed}, indent=1))
    print(f"\n{MANIFEST}: {len(passed)}/{len(rows)} instances passed the gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
