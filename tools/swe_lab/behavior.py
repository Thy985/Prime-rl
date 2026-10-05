"""Phase 3.6: what behaviour does the harness actually change?

Solve rates say H_D beats H_A by +37 points on tier3. They do not say what the model
started doing differently. This reads the recorded trajectories and reduces each episode
to a short behaviour profile, so the effect can be named instead of only measured.

The profile is a sequence of action kinds over the canonical branch, using the same
classification frontier.py already uses for its tool mix:

  inspect  a read-only command (cat, ls, grep, sed, find, ...)
  test     a command that runs a suite (pytest, unittest)
  write    an edit tool call, or a command that mutates the tree
  other    everything else

From that sequence:

  first_edit_step     index of the first write, or None
  first_test_step     index of the first test, or None
  inspect_before_edit at least one inspect precedes the first write
  test_after_edit     a test runs after the first write
  repair_after_test   a write occurs after a test that was followed by another write
                      (the close-the-loop shape: test, see failure, fix)
  no_write            the episode never wrote anything
  tool_call_count     length of the sequence

Reported per (harness, tier) split by solved/unsolved, because the interesting
comparison is not "H_D trajectories look different" but "H_D changes the profile of
the episodes that would otherwise fail".

usage: uv run python tools/swe_lab/behavior.py [--pattern ...] [--tier ...]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "swe_lab"))

from frontier import WRITE_TOOLS, all_runs, kind_of, recorded_reward, tier_of, tool_calls

DEFAULT_PATTERNS = (
    "outputs/swe-lab-budget-hA*",
    "outputs/swe-lab-budget-hD[134]*",
)


def call_kind(call: dict) -> str:
    """One action kind per tool call: write > test > inspect > other."""
    name = (call.get("name") or "").lower()
    if any(marker in name for marker in WRITE_TOOLS):
        return "write"
    arguments = call.get("arguments") or {}
    if isinstance(arguments, str):
        try:
            import json

            arguments = json.loads(arguments)
        except ValueError:
            arguments = {}
    command = (arguments or {}).get("command", "") if isinstance(arguments, dict) else ""
    kind = kind_of(command)
    if kind == "write":
        return "write"
    if kind == "test":
        return "test"
    if kind == "inspect":
        return "inspect"
    return "other"


def profile(trace: dict) -> dict:
    """The behaviour profile of one episode."""
    sequence = [call_kind(c) for c in tool_calls(trace)]
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


def rate(rows: list[dict], key: str) -> str:
    if not rows:
        return "-"
    hits = sum(1 for r in rows if r["profile"][key])
    return "%d%%" % round(100 * hits / len(rows))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pattern", nargs="*", default=list(DEFAULT_PATTERNS))
    ap.add_argument("--tier", nargs="*", default=["tier3-regression-trap", "tier5-multi-constraint"])
    ap.add_argument("--top", type=int, default=6, help="how many example sequences to print per cell")
    args = ap.parse_args()

    rows = []
    for pattern in args.pattern:
        for run_dir in all_runs(pattern):
            from frontier import read_traces

            for trace in read_traces(run_dir):
                if tier_of(trace) not in args.tier:
                    continue
                reward = recorded_reward(trace)
                if reward is None:
                    continue
                rows.append(
                    {
                        "run": run_dir.name,
                        "tier": tier_of(trace),
                        "solved": reward >= 1.0,
                        "profile": profile(trace),
                    }
                )

    if not rows:
        print("no episodes matched", args.pattern, args.tier)
        return 1

    print("episodes: %d from %d runs\n" % (len(rows), len({r["run"] for r in rows})))
    header = "%-22s %-4s %-4s %5s %6s %6s %6s %6s %6s %6s %5s"
    print(header % ("tier", "harn", "solv", "n", "edit@", "test@", "insp1st", "tstAft", "repair", "noWr", "calls"))
    cells = defaultdict(list)
    for row in rows:
        harness = "H_D" if "hd" in row["run"].lower() else "H_A"
        cells[(row["tier"], harness)].append(row)

    for tier in args.tier:
        for harness in ("H_A", "H_D"):
            group = cells.get((tier, harness), [])
            for solved in (True, False):
                sub = [r for r in group if r["solved"] is solved]
                if not sub:
                    continue
                p = [r["profile"] for r in sub]
                edits = [x["first_edit_step"] for x in p if x["first_edit_step"] is not None]
                tests = [x["first_test_step"] for x in p if x["first_test_step"] is not None]
                print(
                    header
                    % (
                        tier,
                        harness,
                        "yes" if solved else "no",
                        len(sub),
                        ("%.1f" % (sum(edits) / len(edits))) if edits else "-",
                        ("%.1f" % (sum(tests) / len(tests))) if tests else "-",
                        rate(sub, "inspect_before_edit"),
                        rate(sub, "test_after_edit"),
                        rate(sub, "repair_after_failed_test"),
                        rate(sub, "no_write"),
                        "%.1f" % (sum(x["tool_call_count"] for x in p) / len(p)),
                    )
                )
                if not solved:
                    continue
        print()

    print("\nmode sequence per (tier, harness), solved episodes:")
    for tier in args.tier:
        for harness in ("H_A", "H_D"):
            sub = [r for r in cells.get((tier, harness), []) if r["solved"]]
            if not sub:
                continue
            shapes = Counter(
                "->".join(
                    k
                    for i, k in enumerate(r["profile"]["sequence"])
                    if i == 0 or k != r["profile"]["sequence"][i - 1]
                )
                for r in sub
            )
            print("\n  %s / %s (n=%d)" % (tier, harness, len(sub)))
            for shape, count in shapes.most_common(args.top):
                print("    %3d  %s" % (count, shape))

    print("\nmode sequence per (tier, harness), UNSOLVED episodes:")
    for tier in args.tier:
        for harness in ("H_A", "H_D"):
            sub = [r for r in cells.get((tier, harness), []) if not r["solved"]]
            if not sub:
                continue
            shapes = Counter(
                "->".join(
                    k
                    for i, k in enumerate(r["profile"]["sequence"])
                    if i == 0 or k != r["profile"]["sequence"][i - 1]
                )
                for r in sub
            )
            print("\n  %s / %s (n=%d)" % (tier, harness, len(sub)))
            for shape, count in shapes.most_common(args.top):
                print("    %3d  %s" % (count, shape))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())