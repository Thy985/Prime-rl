"""Phase 1B (partial, Route G): a deterministic episode on the real runtime.

No LLM is involved: verifiers ships no scripted model, and both the `null` and
`bash` harnesses need a ModelContext, so a harness-driven episode cannot be made
deterministic without an endpoint. What this script does instead is exercise the
abstraction that a real episode depends on -- the runtime -- with a scripted
repair:

    runtime.start -> materialise initial world -> observe failure
                  -> apply the scripted repair (action)
                  -> observe success (state transition happened in the runtime)
                  -> snapshot final state -> verifier -> verdict -> reward

It validates: real runtime execution, real state transition, real observation
capture, and that my record/verdict/replay layer sits correctly on top. It does
NOT produce a verifiers Episode/Trace: that needs Env.run(task, agents) with a
live model endpoint and is Phase 1B proper.

Honest scope note: the "agent" here is scripted, so this proves the plumbing, not
that any policy can do the task.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import contract
import terrain
from verifiers.v1.runtimes.subprocess import SubprocessConfig, SubprocessRuntime

OUT_ROOT = Path(__file__).resolve().parents[2] / "outputs" / "swe_runs"
RUN_ID = "run_0002_scripted_runtime"
PYTEST = ["-m", "pytest", "-v", "--tb=no", "-p", "no:cacheprovider"]


def tail(text: str, limit: int = 600) -> str:
    return text[-limit:]


async def main() -> int:
    baseline = terrain.baseline_outcome()
    run_dir = contract.init_run_dir(OUT_ROOT, RUN_ID)
    initial = run_dir / "initial"
    final = run_dir / "final"

    contract.write_json(run_dir / "task.json", contract.task_json())
    contract.write_json(
        run_dir / "env_fingerprint.json",
        contract.env_fingerprint(
            agent="scripted",
            harness="none (runtime-level episode)",
            runtime="subprocess",
            workdir=str(run_dir / "work"),
        ),
    )
    initial_hash = contract.tree_hash(initial)

    runtime = SubprocessRuntime(SubprocessConfig(), name=RUN_ID)
    steps: list[dict] = []
    try:
        await runtime.start()
        runtime_info = {
            "type": runtime.type,
            "id": runtime.info.id,
            "network_restricted": runtime.network_restricted,
            "workdir": str(runtime.workdir),
        }
        print("runtime:", runtime_info["type"], "->", runtime_info["workdir"])

        for path in sorted(initial.rglob("*")):
            if path.is_file():
                await runtime.write(path.relative_to(initial).as_posix(), path.read_bytes())

        first = await runtime.run([sys.executable, *PYTEST], {})
        steps.append(
            {
                "index": 0,
                "kind": "tool_result",
                "tool": "bash",
                "args": {"cmd": "python -m pytest"},
                "exit_code": first.exit_code,
                "observation": tail(first.stdout),
            }
        )
        print("observation 1: exit=%d (baseline failing)" % first.exit_code)

        await runtime.write("calculator.py", terrain.with_ranges(terrain.with_median()).encode())
        steps.append(
            {
                "index": 1,
                "kind": "tool_call",
                "tool": "edit",
                "args": {"path": "calculator.py"},
                "observation": "",
            }
        )

        second = await runtime.run([sys.executable, *PYTEST], {})
        steps.append(
            {
                "index": 2,
                "kind": "tool_result",
                "tool": "bash",
                "args": {"cmd": "python -m pytest"},
                "exit_code": second.exit_code,
                "observation": tail(second.stdout),
            }
        )
        print("observation 2: exit=%d (after repair)" % second.exit_code)

        listing = await runtime.run(
            ["bash", "-lc", "find . -type f -not -path '*/__pycache__/*' | sed 's|^\\./||' | sort"], {}
        )
        rels = [line for line in listing.stdout.split("\n") if line.strip()]
        for rel in rels:
            (final / rel).parent.mkdir(parents=True, exist_ok=True)
            (final / rel).write_bytes(await runtime.read(rel))
        print("final state files:", rels)
    finally:
        await runtime.teardown()

    final_hash = contract.tree_hash(final)
    (run_dir / "diff.patch").write_text(contract.unified_diff(initial, final))
    tampered = contract.tests_modified(initial, final)
    verdict = terrain.verdict_for_tree(final, baseline, tampered=tampered)
    reward = {name: fn(verdict) for name, fn in terrain.REWARDS.items()}

    replay = terrain.verdict_for_tree(final, baseline, tampered=contract.tests_modified(initial, final))
    replay_equal = replay == verdict

    contract.write_json(run_dir / "initial_state.json", {"tree_hash": initial_hash})
    contract.write_json(run_dir / "final_state.json", {"tree_hash": final_hash})
    contract.write_json(run_dir / "verdict.json", verdict)
    contract.write_json(run_dir / "reward.json", reward)
    (run_dir / "steps.json").write_text(json.dumps(steps, indent=1))
    contract.write_json(
        run_dir / "record.json",
        {
            "run_id": RUN_ID,
            "task_id": contract.TASK_ID,
            "task_hash": contract.task_hash(),
            "episode_ref": None,
            "raw_ref": "steps.json",
            "runtime": runtime_info,
            "initial_state_hash": initial_hash,
            "final_state_hash": final_hash,
            "verdict": verdict,
            "reward": reward,
            "replay_equal": replay_equal,
        },
    )

    print(
        "verdict: passed=%d failed=%d fixed=%d regressions=%d tampered=%s"
        % (
            verdict["passed"],
            verdict["failed"],
            len(verdict["fixed_targets"]),
            len(verdict["regressions"]),
            verdict["tampered"],
        )
    )
    checks = [
        ("baseline observation shows failure", steps[0]["exit_code"] != 0),
        ("post-repair observation shows success", steps[2]["exit_code"] == 0),
        ("all target tests fixed", len(verdict["fixed_targets"]) == 3),
        ("no regression", not verdict["regressions"]),
        ("not tampered", not verdict["tampered"]),
        ("target_fix_fraction 1.0", reward["target_fix_fraction"] == 1.0),
        ("replay equals live", replay_equal),
    ]
    print("\nacceptance:")
    for name, ok in checks:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
    ok_all = all(ok for _, ok in checks)
    print("\nPhase 1B (runtime-level):", "PASS" if ok_all else "FAIL")
    print("run_dir:", run_dir)
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))