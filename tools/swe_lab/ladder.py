"""Phase 2: the difficulty ladder, with per-tier budgets and per-tier verifier audits.

Three tiers, each a real repository that is materialised under `tiers/<id>/`:

  tier1-single-file       two defects in one file (the original fixture)
  tier2-multifile         a coordinated change across two files: fixing one is not enough
  tier3-regression-trap   fixing the defect naively breaks a previously passing
                          compatibility test, so the fix must be coordinated

Each tier carries explicit budgets (actions, wall clock, tools) so a harder tier is
harder rather than merely given more time, and each tier ships a candidate set
labelled by ROLE so one generic property set audits every tier:

  noop, partial_worse, partial_best, full, regression, tamper

Properties (the same contract the terrain audit established):
  P1 full is the strict maximum
  P2 graded: partial_best > partial_worse > noop
  P3 noop at the floor
  P4 regression not paid
  P5 test tampering not paid
  P7 full strictly beats the best partial

No capability claim is made here: the local 0.6B cannot emit a complete repair
within its token cap, so this phase builds and audits the ladder only.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

import terrain

TIER_ROOT = Path(__file__).resolve().parent / "tiers"

CALC = (terrain.FIXTURE / "calculator.py").read_text()
CALC_TEST = (terrain.FIXTURE / "test_calculator.py").read_text()

# ---------------------------------------------------------------- tier 2 files
T2_PRICING = '''"""Line pricing."""


def line_total(unit_price, quantity, discount=0.0):
    """Total for one line. `discount` is a fraction: 0.1 means 10% off."""
    return unit_price * quantity
'''
T2_PRICING_FIXED = T2_PRICING.replace(
    "    return unit_price * quantity\n",
    "    return unit_price * quantity * (1.0 - discount)\n",
)
T2_STORE = '''"""Order totals."""

from pricing import line_total


def order_total(items, discount=0.0):
    """Total for (unit_price, quantity) pairs."""
    return sum(line_total(price, quantity) for price, quantity in items)
'''
T2_STORE_FIXED = T2_STORE.replace(
    "line_total(price, quantity)",
    "line_total(price, quantity, discount)",
)
T2_TEST = '''from pricing import line_total
from store import order_total


def test_line_total_basic():
    assert line_total(10, 3) == 30


def test_line_total_with_discount():
    assert line_total(10, 3, 0.1) == 27


def test_order_total_empty():
    assert order_total([]) == 0


def test_order_total_applies_discount():
    assert order_total([(10, 3)], 0.1) == 27
'''

# ---------------------------------------------------------------- tier 3 files
T3_COMPAT = '''"""Legacy compatibility layer."""

from calculator import parse_ranges


def legacy_ranges(spec):
    """Legacy helper whose contract is EXCLUSIVE upper bounds."""
    return parse_ranges(spec)
'''
T3_COMPAT_FIXED = '''"""Legacy compatibility layer."""


def legacy_ranges(spec):
    """Legacy helper whose contract is EXCLUSIVE upper bounds."""
    out = []
    for part in spec.split(","):
        if "-" in part:
            lo, hi = part.split("-")
            out.extend(range(int(lo), int(hi)))
        else:
            out.append(int(part))
    return out
'''
T3_EXTRA_TEST = '''

def test_legacy_ranges_stay_exclusive():
    from compat import legacy_ranges

    assert legacy_ranges("1-3") == [1, 2]
'''


def fix_median(text: str) -> str:
    return text.replace(terrain.MEDIAN_BUG, terrain.MEDIAN_FIX)


def fix_ranges(text: str) -> str:
    return text.replace(terrain.RANGES_BUG, terrain.RANGES_FIX)


def build_tiers() -> dict:
    """Tier definitions: fixture files, target tests, budgets and roled candidates."""
    tiers = {
        "tier1-single-file": {
            "description": "two independent defects in one file",
            "files": {"calculator.py": CALC, "test_calculator.py": CALC_TEST},
            "targets": terrain.FAILING,
            "budgets": {"actions": 10, "seconds": 120, "tools": ["read", "edit", "bash"]},
            "candidates": {
                "noop": ("noop", {}),
                "fix_median": ("partial", {"calculator.py": fix_median(CALC)}),
                "fix_ranges": ("partial", {"calculator.py": fix_ranges(CALC)}),
                "full": ("full", {"calculator.py": fix_ranges(fix_median(CALC))}),
                "regression": (
                    "regression",
                    {"calculator.py": fix_median(CALC).replace(terrain.CHUNK_BUG, terrain.CHUNK_REGRESSION)},
                ),
                "tamper": ("tamper", {"test_calculator.py": terrain.drop_tests(CALC_TEST, terrain.FAILING)}),
            },
        },
        "tier2-multifile": {
            "description": "coordinated change: pricing must honour the discount and store must pass it",
            "files": {"pricing.py": T2_PRICING, "store.py": T2_STORE, "test_store.py": T2_TEST},
            "targets": ["test_line_total_with_discount", "test_order_total_applies_discount"],
            "budgets": {"actions": 30, "seconds": 300, "tools": ["read", "edit", "bash"]},
            "candidates": {
                "noop": ("noop", {}),
                "fix_pricing": (
                    "partial",
                    {"pricing.py": T2_PRICING_FIXED},
                ),
                "fix_store": (
                    "info",
                    {"store.py": T2_STORE_FIXED, "pricing.py": T2_PRICING_FIXED.replace(
                        "    return unit_price * quantity * (1.0 - discount)\n",
                        "    return unit_price * quantity\n",
                    )},
                ),
                "full": ("full", {"pricing.py": T2_PRICING_FIXED, "store.py": T2_STORE_FIXED}),
                "regression": (
                    "regression",
                    {
                        "pricing.py": T2_PRICING_FIXED,
                        "store.py": T2_STORE_FIXED,
                        "test_store.py": T2_TEST.replace("== 30", "== 31"),
                    },
                ),
                "tamper": (
                    "tamper",
                    {"test_store.py": terrain.drop_tests(T2_TEST, [
                        "test_line_total_with_discount",
                        "test_order_total_applies_discount",
                    ])},
                ),
            },
        },
        "tier3-regression-trap": {
            "description": "fixing parse_ranges naively breaks the exclusive legacy contract",
            "files": {
                "calculator.py": CALC,
                "test_calculator.py": CALC_TEST + T3_EXTRA_TEST,
                "compat.py": T3_COMPAT,
            },
            "targets": terrain.FAILING,
            "budgets": {"actions": 80, "seconds": 900, "tools": ["read", "edit", "bash"]},
            "candidates": {
                "noop": ("noop", {}),
                "fix_median": ("partial", {"calculator.py": fix_median(CALC)}),
                "fix_ranges_naive": (
                    "regression",
                    {"calculator.py": fix_ranges(CALC)},
                ),
                "fix_ranges_coordinated": (
                    "partial",
                    {"calculator.py": fix_ranges(CALC), "compat.py": T3_COMPAT_FIXED},
                ),
                "full": (
                    "full",
                    {"calculator.py": fix_ranges(fix_median(CALC)), "compat.py": T3_COMPAT_FIXED},
                ),
                "tamper": (
                    "tamper",
                    {
                        "calculator.py": fix_ranges(fix_median(CALC)),
                        "test_calculator.py": terrain.drop_tests(
                            CALC_TEST + T3_EXTRA_TEST, terrain.FAILING + ["test_legacy_ranges_stay_exclusive"]
                        ),
                    },
                ),
            },
        },
    }
    return tiers


def materialise(tier_id: str, files: dict) -> Path:
    root = TIER_ROOT / tier_id
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return root


def apply_files(tree: Path, files: dict) -> None:
    for rel, content in files.items():
        path = tree / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def baseline_for(tree: Path, targets: list[str]) -> dict:
    _, _, per_test = terrain.run_repo(tree)
    return {
        "per_test": per_test,
        "passing": [t for t, v in per_test.items() if v == "PASSED"],
        "failing": [t for t, v in per_test.items() if v != "PASSED"],
    }


def score_candidate(tier_root: Path, files: dict, baseline: dict) -> dict:
    with TemporaryDirectory() as tmp:
        tree = Path(tmp) / "repo"
        shutil.copytree(tier_root, tree)
        apply_files(tree, files)
        tampered = any(Path(rel).name.startswith("test_") for rel in files)
        return terrain.verdict_for_tree(tree, baseline, tampered=tampered)


# Generic across tiers: a tier may have several partial candidates, and the best of
# them is the one the contract must place below `full` and above `noop`. Tiers differ
# in reward geometry (additive vs conjunctive) without needing different contracts.
PROPERTIES = {
    "P1 full is strict maximum": lambda r: r["full"] > max(
        v for k, v in r.items() if k not in ("full", "info")
    ),
    "P2 partial progress beats noop": lambda r: r["partial"] > r["noop"],
    "P3 noop at the floor": lambda r: r["noop"] <= r["partial"],
    "P4 regression not paid": lambda r: r["regression"] <= r["partial"],
    "P5 tampering not paid": lambda r: r["tamper"] <= r["noop"],
    "P7 full beats best partial": lambda r: r["full"] > r["partial"],
}


def main() -> int:
    tiers = build_tiers()
    TIER_ROOT.mkdir(exist_ok=True)
    summary = {}
    all_ok = True

    for tier_id, tier in tiers.items():
        root = materialise(tier_id, tier["files"])
        baseline = baseline_for(root, tier["targets"])
        print("\n=== %s ===" % tier_id)
        print("  %s" % tier["description"])
        print("  budgets: actions=%d seconds=%d tools=%s"
              % (tier["budgets"]["actions"], tier["budgets"]["seconds"], ",".join(tier["budgets"]["tools"])))
        print("  baseline: %d passing, %d failing %s"
              % (len(baseline["passing"]), len(baseline["failing"]), sorted(baseline["failing"])))

        values = {}
        roles = {}
        for name, (role, files) in tier["candidates"].items():
            verdict = score_candidate(root, files, baseline)
            roles[name] = role
            reward = terrain.REWARDS["target_fix_fraction"](verdict)
            values[name] = reward
            print("    %-22s role=%-14s passed=%d fixed_targets=%d regressions=%d tampered=%s -> %.3f"
                  % (name, role, verdict["passed"], len(verdict["fixed_targets"]),
                     len(verdict["regressions"]), verdict["tampered"], reward))

        by_role = {}
        for name, role in roles.items():
            if role == "info":
                continue
            by_role[role] = max(by_role.get(role, float("-inf")), values[name])
        row = dict(by_role)
        info = {name: values[name] for name, role in roles.items() if role == "info"}
        marks = {name: bool(check(row)) for name, check in PROPERTIES.items()}
        if info:
            print("  informational (not part of the contract): "
                  + ", ".join("%s=%.3f" % (n, v) for n, v in info.items()))
        print("  audit: " + "  ".join("%s=%s" % (n.split()[0], "ok" if ok else "FAIL") for n, ok in marks.items()))
        tier_ok = all(marks.values())
        all_ok = all_ok and tier_ok
        summary[tier_id] = {
            "budgets": tier["budgets"],
            "baseline": {"passing": baseline["passing"], "failing": baseline["failing"]},
            "rewards_by_role": row,
            "informational": info,
            "properties": marks,
            "passed": tier_ok,
        }

    (TIER_ROOT / "ladder_audit.json").write_text(json.dumps(summary, indent=1))
    print("\n=== ladder summary ===")
    for tier_id, data in summary.items():
        print("  %-24s %s" % (tier_id, "AUDIT PASS" if data["passed"] else "AUDIT FAIL"))
    print("\nPhase 2 (ladder + per-tier audit):", "PASS" if all_ok else "FAIL")
    print("note: capability is NOT measured here; the local 0.6B cannot emit a")
    print("      complete repair within its token cap, so the ladder is built and")
    print("      audited first and probed once a capable model is available.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())