"""Phase 3: repeat a configuration and report the spread, not a single number.

A single run at n=8 turned out to be noisy (tier2 measured 100% in one run and 50%
in another), so a per-tier rate from one run is provisional. This runs the same
scoring over every matching run and reports, per tier, each run's rate plus the
pooled rate and the observed range. The pooled rate is the one to quote; the range
is what tells you whether quoting it is justified yet.

usage: uv run python tools/swe_lab/repeats.py [--pattern 'outputs/swe-lab-rep*']
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from frontier import all_runs, load_tasks, score_run

DEFAULT_PATTERN = "outputs/swe-lab-rep*"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pattern", default=DEFAULT_PATTERN)
    ap.add_argument("--out", default=str(REPO / "outputs" / "swe_runs" / "repeats.json"))
    args = ap.parse_args()

    run_dirs = all_runs(args.pattern)
    if not run_dirs:
        print("no runs matching", args.pattern)
        return 1

    tasks = load_tasks()
    per_run = {}
    for run_dir in run_dirs:
        summary = score_run(run_dir, tasks)
        if summary:
            per_run[run_dir.name] = summary

    tiers = sorted({tier for summary in per_run.values() for tier in summary})
    print("runs:", len(per_run))
    print()
    header = "%-24s" % "tier" + "".join("%9s" % name.replace("swe-lab-", "") for name in per_run)
    print(header + "%10s %10s %8s %8s" % ("pooled", "range", "tools", "errors"))
    pooled_rows = {}
    for tier in tiers:
        cells = []
        solved = valid = invalid = 0
        tool_total = tool_n = 0
        for name, summary in per_run.items():
            row = summary.get(tier)
            if not row:
                cells.append("%9s" % "-")
                continue
            cells.append("%9s" % ("%d/%d" % (row["solved"], row["n_valid"])))
            solved += row["solved"]
            valid += row["n_valid"]
            invalid += row["n_invalid"]
            tool_total += row.get("mean_tool_calls", 0.0) * row["n_valid"]
            tool_n += row["n_valid"]
        rates = [
            summary[tier]["solve_rate"]
            for summary in per_run.values()
            if summary.get(tier) and summary[tier]["solve_rate"] is not None
        ]
        pooled = solved / valid if valid else None
        print(
            "%-24s%s%10s %10s %8s %8d"
            % (
                tier,
                "".join(cells),
                "%.0f%%" % (pooled * 100) if pooled is not None else "n/a",
                "%.0f-%.0f%%" % (min(rates) * 100, max(rates) * 100) if rates else "n/a",
                "%.1f" % (tool_total / tool_n) if tool_n else "-",
                invalid,
            )
        )
        pooled_rows[tier] = {
            "mean_tool_calls": (tool_total / tool_n) if tool_n else None,
            "pooled_solve_rate": pooled,
            "valid": valid,
            "solved": solved,
            "per_run": {name: summary[tier]["solve_rate"] for name, summary in per_run.items() if summary.get(tier)},
            "range": [min(rates), max(rates)] if rates else None,
            "invalid": invalid,
        }

    print("\nper-tier pooled rate with the observed run-to-run range:")
    for tier, row in pooled_rows.items():
        print(
            "  %-24s pooled %.0f%% over %d valid attempts | runs spanned %.0f-%.0f%%"
            % (
                tier,
                (row["pooled_solve_rate"] or 0) * 100,
                row["valid"],
                (row["range"][0] if row["range"] else 0) * 100,
                (row["range"][1] if row["range"] else 0) * 100,
            )
        )
    print("\nquote the pooled rate; the range says whether that is justified yet.")
    Path(args.out).write_text(json.dumps({"runs": list(per_run), "tiers": pooled_rows}, indent=1))
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())