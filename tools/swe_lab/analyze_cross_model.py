"""Phase 6C cross-model budget matrix (dots3 + bunny).

usage: uv run python tools/swe_lab/analyze_matrix.py --bunny
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "swe_lab"))

from behavior_real import profile, solved  # noqa: E402
from frontier import read_traces  # noqa: E402

DOTS3 = {
    ("H_A", 2): ["outputs/rl-6c-hA-T2"], ("H_A", 4): ["outputs/rl-2x2-hA"],
    ("H_A", 6): ["outputs/rl-6c-hA-T6"], ("H_A", 8): ["outputs/rl-6c-hA-T8"],
    ("H_P", 4): ["outputs/rl-2x2-hP", "outputs/rl-2x2-hP2"],
    ("H_P", 6): ["outputs/rl-6c-hP-T6"],
    ("H_G", 4): ["outputs/rl-2x2-hG", "outputs/rl-2x2-hG2"],
    ("H_G", 6): ["outputs/rl-6c-hG-T6"],
    ("H_D", 2): ["outputs/rl-6c-hD-T2"], ("H_D", 4): ["outputs/rl-2x2-hD", "outputs/rl-2x2-hD2"],
    ("H_D", 6): ["outputs/rl-6c-hD-T6"], ("H_D", 8): ["outputs/rl-6c-hD-T8"],
    ("H_ADAPT", 2): ["outputs/rl-6c-hAdapt-T2"], ("H_ADAPT", 4): ["outputs/rl-adapt"],
    ("H_ADAPT", 6): ["outputs/rl-6c-hAdapt-T6"], ("H_ADAPT", 8): ["outputs/rl-6c-hAdapt-T8"],
}
BUNNY = {
    ("H_A", t): [f"outputs/rl-6c-bunny-hA-T{t}"] for t in (2, 4, 6, 8)
} | {
    ("H_D", t): [f"outputs/rl-6c-bunny-hD-T{t}"] for t in (2, 4, 6, 8)
} | {
    ("H_ADAPT", t): [f"outputs/rl-6c-bunny-hAdapt-T{t}"] for t in (2, 4, 6, 8)
} | {
    ("H_P", 6): ["outputs/rl-6c-bunny-hP-T6"],
    ("H_G", 6): ["outputs/rl-6c-bunny-hG-T6"],
}


def cells(runs):
    out = {}
    for (arm, T), dirs in runs.items():
        rows = []
        for d in dirs:
            rd = Path(d)
            if rd.exists():
                rows += read_traces(rd)
        n = len(rows)
        sol = sum(1 for tr in rows if solved(tr))
        profs = [profile(tr) for tr in rows]
        edits = sum(1 for p in profs if not p["no_write"])
        tests = sum(1 for p in profs if p["first_test_step"] is not None)
        out[(arm, T)] = (n, sol, edits, tests)
    return out


def render(name, cells):
    print(f"== {name} (wide set, T=2/4/6/8, sol/edit/test) ==")
    for arm in ("H_A", "H_P", "H_G", "H_D", "H_ADAPT"):
        cols = []
        for T in (2, 4, 6, 8):
            if (arm, T) in cells:
                n, sol, ed, te = cells[(arm, T)]
                cols.append(f"T={T} {sol:>2}/{n:<3} {ed:>2}/{n:<3} {te:>2}/{n:<3}")
            else:
                cols.append(f"T={T}    --    ")
        print(f"{arm:9} " + "  ".join(cols))
    print()


def main() -> int:
    if "--bunny" in sys.argv:
        render("bunny (space-bunny-alpha)", cells(BUNNY))
    render("dots3", cells(DOTS3))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())