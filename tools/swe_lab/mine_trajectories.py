"""Phase 3.6: trajectory mining -- what behaviour separates success from failure?

Phase 3 answered whether tiers can be solved; this asks why. The useful sample is a
condition that contains BOTH outcomes, so the comparison is controlled: the same
model, taskset, harness family and budgets produced 9 successes and 7 failures when
the `edit` tool was removed, so that run is the primary cohort and the all-success
runs serve as a reference.

Per episode it reconstructs the action sequence from the recorded tool calls and
derives behavioural features, then contrasts the success and failure cohorts:

  first_kind          what the agent did first (inspect / test / write / other)
  inspected_first     looked at code before changing any file
  tested_first        ran the suite before changing any file
  n_calls             total tool calls
  n_tests             how often it ran the suite
  duplicates          repeated identical commands (thrashing)
  wrote               whether it changed anything at all

Reading tool counts without conditioning on outcome is a trap this data makes
concrete: the failing cohort uses FEWER calls, because giving up looks efficient.

usage: uv run python tools/swe_lab/mine_trajectories.py [--run <glob> ...]
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import zstandard

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from frontier import all_runs, recorded_reward, tier_of, tool_calls

DEFAULT_RUNS = ("outputs/swe-lab-harnessB-noedit", "outputs/swe-lab-harnessA")

TEST_RE = re.compile(r"\bpytest\b|\bunittest\b")
WRITE_RE = re.compile(r">\s*\S|\bsed -i\b|\btee\b|<<\s*['\"]?EOF|\bpatch\b|\bapply_patch\b")
INSPECT_RE = re.compile(r"^\s*(cat|ls|head|tail|grep|find|sed|wc|file|awk|less|diff)\b")


WRITE_TOOLS = ("edit", "write", "apply_patch", "str_replace", "create")


def kind_of(command: str) -> str:
    """Classify a bash command by what it is FOR, not by which binary it calls."""
    text = (command or "").strip()
    if TEST_RE.search(text):
        return "test"
    if WRITE_RE.search(text):
        return "write"
    if INSPECT_RE.match(text):
        return "inspect"
    return "other"


def action_kind(call: dict) -> str:
    """Classify a TOOL CALL, which is not always a bash command.

    A dedicated edit/write tool changes a file with no shell command at all, so
    classifying only bash text reported every edit-tool repair as "never wrote
    anything" -- a measurement bug, not a behavioural finding.
    """
    name = (call.get("name") or "").lower()
    if any(marker in name for marker in WRITE_TOOLS):
        return "write"
    if name != "bash":
        return "other"
    arguments = call.get("arguments") or ""
    command = ""
    if arguments.strip().startswith("{"):
        try:
            command = json.loads(arguments).get("command", "") or ""
        except json.JSONDecodeError:
            command = ""
    else:
        command = arguments
    return kind_of(command)


def features(trace: dict, solved: bool) -> dict:
    calls = tool_calls(trace)
    commands = []
    for call in calls:
        arguments = call.get("arguments") or ""
        if arguments.strip().startswith("{"):
            try:
                commands.append(json.loads(arguments).get("command") or json.dumps(json.loads(arguments), sort_keys=True))
            except json.JSONDecodeError:
                commands.append(arguments)
        else:
            commands.append(arguments)
    kinds = [action_kind(call) for call in calls]
    first_write = next((i for i, kind in enumerate(kinds) if kind == "write"), None)
    first_test = next((i for i, kind in enumerate(kinds) if kind == "test"), None)
    return {
        "tier": tier_of(trace),
        "solved": solved,
        "n_calls": len(commands),
        "first_kind": kinds[0] if kinds else "none",
        "inspected_first": bool(first_write is not None and "inspect" in kinds[:first_write]),
        "tested_first": bool(first_test is not None and (first_write is None or first_test < first_write)),
        "n_tests": sum(1 for kind in kinds if kind == "test"),
        "wrote": first_write is not None,
        "duplicates": len(commands) - len(set(commands)),
        "kinds": kinds,
    }


def load(pattern: str) -> list[dict]:
    rows = []
    for run_dir in all_runs(pattern):
        for path in sorted(run_dir.glob("monitors/file/traces/stream/*.jsonl.zst")):
            with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(path.read_bytes())) as reader:
                for line in reader.read().decode().splitlines():
                    if not line.strip():
                        continue
                    for trace in json.loads(line).get("traces") or []:
                        reward = recorded_reward(trace)
                        if reward is None:
                            continue
                        row = features(trace, reward >= 1.0)
                        row["run"] = run_dir.name
                        rows.append(row)
    return rows


def cohort(rows: list[dict]) -> dict:
    out = {}
    for label, group in (("solved", [r for r in rows if r["solved"]]),
                         ("failed", [r for r in rows if not r["solved"]])):
        if not group:
            continue
        n = len(group)
        out[label] = {
            "n": n,
            "mean_calls": sum(r["n_calls"] for r in group) / n,
            "mean_tests": sum(r["n_tests"] for r in group) / n,
            "mean_duplicates": sum(r["duplicates"] for r in group) / n,
            "inspected_first": sum(r["inspected_first"] for r in group) / n,
            "tested_first": sum(r["tested_first"] for r in group) / n,
            "wrote": sum(r["wrote"] for r in group) / n,
            "first_kind": dict(Counter(r["first_kind"] for r in group)),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", nargs="*", default=list(DEFAULT_RUNS))
    ap.add_argument("--out", default=str(REPO / "outputs" / "swe_runs" / "trajectory_mining.json"))
    args = ap.parse_args()

    summary = {}
    for pattern in args.run:
        rows = load(pattern)
        if not rows:
            print("no traces for", pattern)
            continue
        groups = cohort(rows)
        print("\n=== %s ===  episodes=%d" % (pattern, len(rows)))
        print("%-9s %4s %10s %9s %11s %12s %11s %7s" % (
            "cohort", "n", "calls", "tests", "duplicates", "inspect 1st", "test 1st", "wrote"))
        for label in ("solved", "failed"):
            if label not in groups:
                continue
            g = groups[label]
            print("%-9s %4d %10.1f %9.1f %11.1f %12.0f%% %10.0f%% %6.0f%%" % (
                label, g["n"], g["mean_calls"], g["mean_tests"], g["mean_duplicates"],
                g["inspected_first"] * 100, g["tested_first"] * 100, g["wrote"] * 100))
        for label in ("solved", "failed"):
            if label in groups:
                print("  %-6s first action: %s" % (label, groups[label]["first_kind"]))
        summary[pattern] = groups

    Path(args.out).write_text(json.dumps(summary, indent=1))
    print("\nreading these together matters: fewer tool calls in the failed cohort is a")
    print("symptom of giving up, not of efficiency. Always condition on outcome.")
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())