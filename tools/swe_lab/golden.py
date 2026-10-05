"""Phase 1A: the Golden Episode — prove the closure before any live agent runs.

A known task, a known correct repair, a known final state and a known verdict. The
record, the verifier and the replay must all reproduce it exactly. If they do not,
a later live failure cannot be attributed to agent, adapter, environment or
verifier -- which is the trap that already cost one wrong conclusion in
reverse-text.

Acceptance:
  1. the golden repair scores the known verdict (all target tests fixed, no
     regression, not tampered, target_fix_fraction 1.0)
  2. rescoring the frozen final state reproduces the identical verdict
  3. negative controls are caught: a no-op, a test-tampering edit and a
     regression-introducing edit must NOT score as success
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import contract
import terrain

OUT_ROOT = Path(__file__).resolve().parents[2] / "outputs" / "swe_runs"


def score(run_dir: Path, baseline, label: str) -> dict:
    final = run_dir / "final"
    tampered = contract.tests_modified(run_dir / "initial", final)
    verdict = terrain.verdict_for_tree(final, baseline, tampered=tampered)
    reward = {name: fn(verdict) for name, fn in terrain.REWARDS.items()}
    print(
        "  %-10s passed=%d failed=%d fixed=%d regressions=%d tampered=%s -> target_fix_fraction=%.3f shaped=%.3f"
        % (
            label,
            verdict["passed"],
            verdict["failed"],
            len(verdict["fixed_targets"]),
            len(verdict["regressions"]),
            verdict["tampered"],
            reward["target_fix_fraction"],
            reward["shaped"],
        )
    )
    return {"verdict": verdict, "reward": reward, "tampered": tampered}


def main() -> int:
    baseline = terrain.baseline_outcome()
    print("baseline: %d passing, %d failing" % (len(baseline["passing"]), len(baseline["failing"])))

    run_dir = contract.init_run_dir(OUT_ROOT, "run_0001_golden")
    initial = run_dir / "initial"
    work = run_dir / "work"

    contract.write_json(run_dir / "task.json", contract.task_json())
    contract.write_json(
        run_dir / "env_fingerprint.json",
        contract.env_fingerprint(
            agent="golden",
            harness="none",
            runtime="none",
            workdir=str(work),
        ),
    )

    initial_hash = contract.tree_hash(initial)
    print("initial_state_hash:", initial_hash[:16])

    # 1. the known-correct repair
    (work / "calculator.py").write_text(terrain.with_ranges(terrain.with_median()))
    final = contract.snapshot_final(run_dir)
    final_hash = contract.tree_hash(final)
    diff = contract.unified_diff(initial, final)
    (run_dir / "diff.patch").write_text(diff)

    contract.write_json(run_dir / "initial_state.json", {"tree_hash": initial_hash, "files": sorted(
        p.relative_to(initial).as_posix() for p in initial.rglob("*") if p.is_file()
    )})
    contract.write_json(run_dir / "final_state.json", {"tree_hash": final_hash, "files": sorted(
        p.relative_to(final).as_posix() for p in final.rglob("*") if p.is_file()
    )})

    print("golden:")
    golden = score(run_dir, baseline, "golden")

    # 2. replay: rescore the frozen final state from disk
    replay = terrain.verdict_for_tree(final, baseline, tampered=contract.tests_modified(initial, final))
    replay_equal = replay == golden["verdict"]
    print("  replay verdict == live verdict:", replay_equal)

    contract.write_json(run_dir / "verdict.json", golden["verdict"])
    contract.write_json(run_dir / "reward.json", golden["reward"])
    contract.write_json(
        run_dir / "record.json",
        {
            "run_id": "run_0001_golden",
            "task_id": contract.TASK_ID,
            "task_hash": contract.task_hash(),
            "episode_ref": None,
            "raw_ref": None,
            "initial_state_hash": initial_hash,
            "final_state_hash": final_hash,
            "verdict": golden["verdict"],
            "reward": golden["reward"],
            "replay_equal": replay_equal,
        },
    )

    print("negative controls:")
    checks = []

    # no-op must not score as success
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as tmp:
        ctl = contract.init_run_dir(Path(tmp), "noop")
        contract.snapshot_final(ctl)
        noop = score(ctl, baseline, "no-op")
        checks.append(("no-op not success", noop["reward"]["target_fix_fraction"] == 0.0))

    # tampering with the tests must not be paid
    with TemporaryDirectory() as tmp:
        ctl = contract.init_run_dir(Path(tmp), "tamper")
        dropped = terrain.drop_tests(terrain.BASE_TEST, terrain.FAILING)
        (ctl / "work" / "test_calculator.py").write_text(dropped)
        contract.snapshot_final(ctl)
        tamper = score(ctl, baseline, "tamper")
        checks.append(("tamper not paid", tamper["reward"]["target_fix_fraction"] == 0.0))

    # a regression must be caught
    with TemporaryDirectory() as tmp:
        ctl = contract.init_run_dir(Path(tmp), "regression")
        broken = terrain.with_median().replace(terrain.CHUNK_BUG, terrain.CHUNK_REGRESSION)
        (ctl / "work" / "calculator.py").write_text(broken)
        contract.snapshot_final(ctl)
        regr = score(ctl, baseline, "regression")
        checks.append(("regression caught", len(regr["verdict"]["regressions"]) > 0))

    checks.insert(0, ("golden is full success", golden["reward"]["target_fix_fraction"] == 1.0))
    checks.insert(1, ("replay equals live", replay_equal))

    print("\nacceptance:")
    for name, ok in checks:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
    ok_all = all(ok for _, ok in checks)
    print("\nPhase 1A:", "PASS" if ok_all else "FAIL")
    print("run_dir:", run_dir)
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())