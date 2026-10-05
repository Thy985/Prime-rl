"""Real-SWE behaviour profile: the same instrument as behavior.py, on swe-bench.

Swe-bench episodes are grouped by instance rather than tier, and solved means the
`resolve` reward (all FAIL_TO_PASS and PASS_TO_PASS green under the oracle test
patch) rather than the swe-lab target fraction. The action-kind classification is
behavior.py's, plus the django runner (`tests/runtests.py ...` counts as a test
run, which frontier.TEST_RE does not cover).

A --pattern may be a bare glob (the harness is then guessed from the run name, as
before) or LABEL=GLOB, which labels the cell explicitly. The H_A' run is named
rl-hAp*, so the bare rl-hA* glob would swallow it; labelling keeps the triangle
(H_A / H_A' / H_D) separable without renaming past runs.

usage: uv run python tools/swe_lab/behavior_real.py [--pattern [LABEL=]GLOB ...] [--top N]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "swe_lab"))

from behavior import call_kind, rate  # noqa: E402
from frontier import all_runs, read_traces, recorded_reward, tier_of, tool_calls  # noqa: E402

DEFAULT_PATTERNS = ("outputs/rl-hA*", "outputs/rl-hD*")


def real_call_kind(call: dict) -> str:
    """call_kind plus the django runner: `runtests.py` is a test run."""
    args = call.get("arguments") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            args = {}
    command = (args or {}).get("command", "") if isinstance(args, dict) else ""
    if "runtests" in command:
        return "test"
    return call_kind(call)


def profile(trace: dict) -> dict:
    """The behaviour profile of one episode, with the runtests-aware kind."""
    sequence = [real_call_kind(c) for c in tool_calls(trace)]
    first_write = next((i for i, k in enumerate(sequence) if k == "write"), None)
    first_test = next((i for i, k in enumerate(sequence) if k == "test"), None)
    inspect_before = bool(first_write is not None and any(k == "inspect" for k in sequence[:first_write]))
    test_after = bool(first_write is not None and any(k == "test" for k in sequence[first_write:]))
    repair = False
    seen_test = False
    for kind in sequence:
        if kind == "test":
            seen_test = True
        elif kind == "write" and seen_test:
            repair = True
    return {
        "sequence": sequence,
        "first_edit_step": first_write,
        "first_test_step": first_test,
        "inspect_before_edit": inspect_before,
        "test_after_edit": test_after,
        "repair_after_failed_test": repair,
        "no_write": first_write is None,
        "tool_call_count": len(sequence),
        "kind_mix": dict(Counter(sequence)),
    }


def solved(trace: dict) -> bool:
    return recorded_reward(trace, "resolve") == 1.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pattern", nargs="*", default=list(DEFAULT_PATTERNS), help="[LABEL=]GLOB")
    ap.add_argument("--top", type=int, default=4, help="example sequences per cell")
    args = ap.parse_args()

    rows = []
    for spec in args.pattern:
        label, _, pattern = spec.rpartition("=")
        for run_dir in all_runs(pattern):
            run = run_dir.name
            harness = label or ("H_D" if "hd" in run.lower() else "H_A")
            for trace in read_traces(run_dir):
                rows.append(
                    {
                        "run": run,
                        "harness": harness,
                        "instance": tier_of(trace),
                        "solved": solved(trace),
                        "profile": profile(trace),
                    }
                )
    if not rows:
        print("no traces matched", args.pattern)
        return 0
    print(f"patterns: {args.pattern}")

    print("== per (harness, instance, solved) ==")
    by = defaultdict(list)
    for r in rows:
        by[(r["harness"], r["instance"], r["solved"])].append(r)
    for (h, inst, sol) in sorted(by):
        cell = by[(h, inst, sol)]
        print(
            f"{h} {inst:<26} {'solved' if sol else 'unsolved':<8} n={len(cell):<2} "
            f"inspect_before={rate(cell, 'inspect_before_edit')} "
            f"test_after={rate(cell, 'test_after_edit')} "
            f"repair={rate(cell, 'repair_after_failed_test')} "
            f"no_write={rate(cell, 'no_write')} "
            f"calls={sum(r['profile']['tool_call_count'] for r in cell) // len(cell)}"
        )
    print()
    print("== per (harness, solved) pooled ==")
    pooled = defaultdict(list)
    for r in rows:
        pooled[(r["harness"], r["solved"])].append(r)
    for (h, sol) in sorted(pooled):
        cell = pooled[(h, sol)]
        print(
            f"{h} {'solved' if sol else 'unsolved':<8} n={len(cell):<3} "
            f"inspect_before={rate(cell, 'inspect_before_edit')} "
            f"test_after={rate(cell, 'test_after_edit')} "
            f"repair={rate(cell, 'repair_after_failed_test')} "
            f"no_write={rate(cell, 'no_write')} "
            f"calls={sum(r['profile']['tool_call_count'] for r in cell) // len(cell)}"
        )
    print()
    print("== solve rates ==")
    byh = defaultdict(list)
    for r in rows:
        byh[r["harness"]].append(r)
    for h in sorted(byh):
        cell = byh[h]
        ns = sum(1 for r in cell if r["solved"])
        print(f"  {h}: {ns}/{len(cell)} = {round(100 * ns / len(cell))}%")
    print()
    print("== top sequences per (harness, solved) ==")
    for (h, sol) in sorted(pooled):
        seqs = Counter(" ".join(r["profile"]["sequence"]) for r in pooled[(h, sol)])
        print(f"{h} {'solved' if sol else 'unsolved'}:")
        for seq, n in seqs.most_common(args.top):
            print(f"    {n}x  {seq[:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
