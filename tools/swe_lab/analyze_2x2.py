"""Phase 6A: 2x2 factorial analysis on the wide set.

Reads the four arms (H_A, H_P, H_G, H_D) and reports the metrics the factorial
is decided on, per arm:

  solve rate        episodes whose resolve reward is 1.0
  no_write          share of episodes that never edited
  first_edit_turn   median turn of the first edit, among episodes that edited
  edit count        mean edit (write-kind) calls per episode
  test count        mean test-run calls per episode (runtests/pytest/manage.py)
  first_test_turn   median turn of the first test run, among episodes that ran one

usage: uv run python tools/swe_lab/analyze_2x2.py [--pattern [LABEL=]GLOB ...]
"""

from __future__ import annotations

import argparse
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "swe_lab"))

from behavior_real import profile, solved  # noqa: E402
from frontier import all_runs, read_traces, tier_of  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pattern", nargs="*", default=["H_A=outputs/rl-2x2-hA*", "H_P=outputs/rl-2x2-hP*", "H_G=outputs/rl-2x2-hG*", "H_D=outputs/rl-2x2-hD*"])
    args = ap.parse_args()

    rows = []
    for spec in args.pattern:
        label, _, pattern = spec.rpartition("=")
        for run_dir in all_runs(pattern):
            label = label or run_dir.name
            for trace in read_traces(run_dir):
                p = profile(trace)
                rows.append(
                    {
                        "harness": label,
                        "instance": tier_of(trace),
                        "solved": solved(trace),
                        "no_write": p["no_write"],
                        "first_edit_turn": None if p["first_edit_step"] is None else p["first_edit_step"] + 1,
                        "edit_count": p["kind_mix"].get("write", 0),
                        "test_count": p["kind_mix"].get("test", 0),
                        "first_test_turn": None if p["first_test_step"] is None else p["first_test_step"] + 1,
                    }
                )
    if not rows:
        print("no traces matched", args.pattern)
        return 0

    by = defaultdict(list)
    for r in rows:
        by[r["harness"]].append(r)

    print("== 2x2 factorial, wide set, T=4, 1 ep/instance ==")
    print(f"{'arm':<4} {'n':>3} {'solve':>7} {'no_write':>8} {'edit/ep':>7} {'test/ep':>7} {'first_edit (med, edt-ep)':>22} {'first_test (med, test-ep)':>24}")
    for h in sorted(by):
        cell = by[h]
        n = len(cell)
        ns = sum(1 for r in cell if r["solved"])
        nw = sum(1 for r in cell if r["no_write"])
        ec = sum(r["edit_count"] for r in cell) / n
        tc = sum(r["test_count"] for r in cell) / n
        fe = [r["first_edit_turn"] for r in cell if r["first_edit_turn"] is not None]
        ft = [r["first_test_turn"] for r in cell if r["first_test_turn"] is not None]
        fem = statistics.median(fe) if fe else None
        ftm = statistics.median(ft) if ft else None
        print(
            f"{h:<4} {n:>3} {f'{ns}/{n}':>7} {f'{round(100*nw/n)}%':>8} {ec:>7.2f} {tc:>7.2f} "
            f"{f'{fem} ({len(fe)})':>22} {f'{ftm} ({len(ft)})':>24}"
        )

    print()
    print("== per-instance solve ==")
    insts = sorted({r["instance"] for r in rows})
    head = "  " + "".join(f"{h:>6}" for h in sorted(by))
    print(f"  instance{'':<16}" + head)
    for inst in insts:
        line = f"  {inst:<22}"
        for h in sorted(by):
            cell = [r for r in by[h] if r["instance"] == inst]
            solved_fraction = f"{sum(1 for r in cell if r['solved'])}/{len(cell)}"
            line += f"{solved_fraction:>6}"
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())