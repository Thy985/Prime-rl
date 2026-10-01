"""SWE feedback-terrain lab: define and AUDIT the reward an agent would receive.

Bounded, offline fixture repo (tools/swe_lab/fixture) with two seeded defects. A
candidate repair is applied to a throwaway copy, the suite runs under a timeout,
and the outcome becomes a structured verdict. Candidate rewards are then audited
against properties a SWE verifier must hold -- before anything is trained. This
is the same order used for reverse-text: verify the verifier first.

Verdict fields:
  exit_code  timed_out  collected  passed  failed  errors  skipped
  per_test       {test name: PASSED|FAILED|ERROR|SKIPPED}
  fixed_targets  baseline-failing tests that now pass
  still_failing  baseline-failing tests that still fail
  regressions    baseline-passing tests that no longer pass
  tampered       a test file was modified
"""

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixture"
PYTHON = sys.executable
TIMEOUT = 30.0

BASE_CALC = (FIXTURE / "calculator.py").read_text()
BASE_TEST = (FIXTURE / "test_calculator.py").read_text()

MEDIAN_BUG = "    ordered = sorted(values)\n    return ordered[len(ordered) // 2]\n"
MEDIAN_FIX = (
    "    ordered = sorted(values)\n"
    "    middle = len(ordered) // 2\n"
    "    if len(ordered) % 2:\n"
    "        return ordered[middle]\n"
    "    return (ordered[middle - 1] + ordered[middle]) / 2\n"
)
RANGES_BUG = "            out.extend(range(int(lo), int(hi)))"
RANGES_FIX = "            out.extend(range(int(lo), int(hi) + 1))"
CHUNK_BUG = "return [items[i:i + size] for i in range(0, len(items), size)]"
CHUNK_REGRESSION = "return [items[i:i + size] for i in range(0, len(items) - size + 1, size)]"

for name, text in (("MEDIAN_BUG", MEDIAN_BUG), ("RANGES_BUG", RANGES_BUG), ("CHUNK_BUG", CHUNK_BUG)):
    if text not in BASE_CALC:
        raise SystemExit(f"fixture drifted: {name} not found in calculator.py")

FAILING = ["test_median_even", "test_parse_ranges_one_range", "test_parse_ranges_two_ranges"]


def with_median(text=BASE_CALC):
    return text.replace(MEDIAN_BUG, MEDIAN_FIX)


def with_ranges(text=BASE_CALC):
    return text.replace(RANGES_BUG, RANGES_FIX)


def drop_tests(text, names):
    blocks = text.split("\n\n\n")
    kept = [b for b in blocks if not any(f"def {n}(" in b for n in names)]
    return "\n\n\n".join(kept)


def skip_tests(text, names):
    out = "import pytest\n\n\n" + text
    for name in names:
        out = out.replace(f"def {name}():", f"@pytest.mark.skip\ndef {name}():")
    return out


CANDIDATES = {
    "noop": {},
    "wrong_file": {"NOTES.md": "# analysis\n\nThe defect is in parse_ranges.\n"},
    "syntax_error": {"calculator.py": BASE_CALC + "\ndef broken(:\n    pass\n"},
    "fix_median_only": {"calculator.py": with_median()},
    "fix_ranges_only": {"calculator.py": with_ranges()},
    "full_fix": {"calculator.py": with_ranges(with_median())},
    "regression": {"calculator.py": with_median().replace(CHUNK_BUG, CHUNK_REGRESSION)},
    "tamper_delete": {"test_calculator.py": drop_tests(BASE_TEST, FAILING)},
    "tamper_skip": {"test_calculator.py": skip_tests(BASE_TEST, FAILING)},
    "timeout": {"calculator.py": BASE_CALC.replace(
        "    return ordered[len(ordered) // 2]\n",
        "    while True:\n        pass\n",
    )},
}

OUTCOMES = ("PASSED", "FAILED", "ERROR", "SKIPPED", "XFAIL", "XPASS")


def parse_verbose(stdout):
    per_test = {}
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and "::" in parts[0] and parts[1] in OUTCOMES:
            per_test[parts[0].split("::", 1)[1]] = parts[1]
    return per_test


def materialise(repo, files):
    for rel, content in files.items():
        path = repo / rel
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)


def run_repo(repo, timeout=TIMEOUT):
    """Run the suite; return (exit_code, timed_out, per_test) for one repo state."""
    try:
        proc = subprocess.run(
            [PYTHON, "-m", "pytest", "-v", "--tb=no", "-p", "no:cacheprovider"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, True, {}
    return proc.returncode, False, parse_verbose(proc.stdout)


def evaluate(files, baseline, timeout=TIMEOUT):
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(FIXTURE, repo)
        materialise(repo, files)
        exit_code, timed_out, per_test = run_repo(repo, timeout)
    tampered = any(Path(rel).name.startswith("test_") for rel in files)
    if timed_out:
        return {
            "exit_code": None,
            "timed_out": True,
            "per_test": {},
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "collected": 0,
            "fixed_targets": [],
            "still_failing": list(baseline["failing"]),
            "regressions": list(baseline["passing"]),
            "tampered": tampered,
        }
    passed = sum(1 for v in per_test.values() if v == "PASSED")
    failed = sum(1 for v in per_test.values() if v == "FAILED")
    errors = sum(1 for v in per_test.values() if v == "ERROR")
    skipped = sum(1 for v in per_test.values() if v == "SKIPPED")
    fixed = [t for t in baseline["failing"] if per_test.get(t) == "PASSED"]
    still = [t for t in baseline["failing"] if per_test.get(t) != "PASSED"]
    regressions = [t for t in baseline["passing"] if per_test.get(t) not in ("PASSED", "SKIPPED")]
    return {
        "exit_code": exit_code,
        "timed_out": False,
        "per_test": per_test,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "fixed_targets": fixed,
        "still_failing": still,
        "regressions": regressions,
        "tampered": tampered,
        "collected": passed + failed + errors,
    }


def baseline_outcome():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(FIXTURE, repo)
        _, _, per_test = run_repo(repo)
    return {
        "per_test": per_test,
        "passing": [t for t, v in per_test.items() if v == "PASSED"],
        "failing": [t for t, v in per_test.items() if v != "PASSED"],
    }


def r_exit_zero(v):
    return 1.0 if v["exit_code"] == 0 and not v["timed_out"] else 0.0


def r_pass_fraction(v):
    return v["passed"] / v["collected"] if v.get("collected") else 0.0


def r_pass_fraction_guarded(v):
    if v["timed_out"] or v["regressions"]:
        return 0.0
    return r_pass_fraction(v)


def r_shaped(v):
    if v["timed_out"] or v["tampered"] or v["regressions"]:
        return 0.0
    return r_pass_fraction(v) + (0.15 if v["failed"] == 0 and v["errors"] == 0 else 0.0)


def r_target_fix_fraction(v):
    if v["timed_out"] or v["tampered"] or v["regressions"]:
        return 0.0
    targets = len(v["fixed_targets"]) + len(v["still_failing"])
    return len(v["fixed_targets"]) / targets if targets else 0.0


REWARDS = {
    "exit_zero": r_exit_zero,
    "pass_fraction": r_pass_fraction,
    "pass_fraction_guarded": r_pass_fraction_guarded,
    "shaped": r_shaped,
    "target_fix_fraction": r_target_fix_fraction,
}

# Properties a SWE verifier must hold. Each takes {candidate: reward value}.
PROPERTIES = {
    "P1 full_fix is the strict maximum": lambda r: r["full_fix"] > max(
        v for k, v in r.items() if k != "full_fix"
    ),
    "P2 graded: ranges > median > noop": lambda r: r["fix_ranges_only"] > r["fix_median_only"] > r["noop"],
    "P3 noop/wrong_file at the floor": lambda r: r["noop"] <= r["fix_median_only"] and r["wrong_file"] <= r["fix_median_only"],
    "P4 regression penalised": lambda r: r["regression"] <= r["fix_median_only"],
    "P5 test tampering not rewarded": lambda r: r["tamper_delete"] <= r["noop"] and r["tamper_skip"] <= r["noop"],
    "P6 crash/timeout not rewarded": lambda r: r["syntax_error"] <= r["noop"] and r["timeout"] <= r["noop"],
    "P7 success beats best partial": lambda r: r["full_fix"] > r["fix_ranges_only"],
}


def main():
    baseline = baseline_outcome()
    print("baseline: %d passing, %d failing -> %s"
          % (len(baseline["passing"]), len(baseline["failing"]), sorted(baseline["failing"])))

    verdicts = {name: evaluate(files, baseline) for name, files in CANDIDATES.items()}

    print("\n%-18s %5s %5s %5s %6s %5s %6s %5s  %s"
          % ("candidate", "pass", "fail", "err", "regr", "tamp", "timeout", "exit", "fixed_targets"))
    for name, v in verdicts.items():
        print("%-18s %5d %5d %5d %6d %5s %6s %5s  %s"
              % (name, v["passed"], v["failed"], v["errors"], len(v["regressions"]),
                 "yes" if v["tampered"] else "-", "yes" if v["timed_out"] else "-",
                 "-" if v["exit_code"] is None else v["exit_code"], v["fixed_targets"]))

    print("\n%-24s %s" % ("reward", "  ".join("%-9s" % c[:9] for c in CANDIDATES)))
    values = {}
    for rname, fn in REWARDS.items():
        row = {c: fn(v) for c, v in verdicts.items()}
        values[rname] = row
        print("%-24s %s" % (rname, "  ".join("%-9.3f" % row[c] for c in CANDIDATES)))

    print("\n%-24s %s" % ("property", "  ".join("%-4s" % ("P%d" % i) for i in range(1, len(PROPERTIES) + 1))))
    for rname, row in values.items():
        marks = ["ok" if check(row) else "FAIL" for check in PROPERTIES.values()]
        print("%-24s %s" % (rname, "  ".join("%-4s" % m for m in marks)))
    print("\nproperties:")
    for name in PROPERTIES:
        print("  %s" % name)


if __name__ == "__main__":
    main()