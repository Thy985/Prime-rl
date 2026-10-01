"""Phase 3: the capability frontier across the swe-lab tiers.

Reads finished eval runs, decompresses their stream traces, and re-derives every
score from the saved reply through the taskset's own scorer. Re-deriving rather
than trusting the recorded number is deliberate: the recorded reward reflects the
parser as it was at run time, and a parser fix must be able to correct the
measurement without re-rolling the model. Both numbers are reported.

Per tier it reports the solve rate and a failure mixture, so the frontier is
located instead of averaged away:

  no_proposal     the reply yielded no file contents at all
  invalid_syntax  a proposed file does not compile
  regression      a previously passing test broke
  partial         some target tests fixed, not all
  no_progress     parsed and valid, but no target test fixed

Episodes whose request errored are NOT model failures: they are excluded from the
denominator and reported separately, because counting them as failures understates
the solve rate.

The frontier is the first tier not solved on every valid attempt. With few
attempts a 50% cut-off hides a real cliff, and 8/8 versus 4/8 is the difference
between dependable and unusable.

Raw trajectories stay in the run directory; no training view is written here.

usage: uv run python tools/swe_lab/frontier.py [--run <glob or dir>]
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

import zstandard

REPO = Path(__file__).resolve().parents[2]
RUN_GLOB = "outputs/swe-lab--*"
sys.path.insert(0, str(REPO / "tools" / "swe_lab"))
sys.path.insert(0, str(REPO / "tools" / "swe_lab_env"))

import terrain
from swe_lab.taskset import SweLabConfig, SweLabTaskset, parse_proposals

INVALID_STOPS = ("error",)


def all_runs(pattern: str) -> list[Path]:
    """Every run matching a glob, newest last."""
    candidates = Path(pattern)
    if candidates.is_absolute():
        found = [candidates] if candidates.is_dir() else sorted(candidates.parent.glob(candidates.name))
    else:
        found = sorted(REPO.glob(pattern))
    return sorted(found, key=lambda path: path.stat().st_mtime)


def read_traces(run_dir: Path) -> list[dict]:
    traces = []
    for path in sorted(run_dir.glob("monitors/file/traces/stream/*.jsonl.zst")):
        with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(path.read_bytes())) as reader:
            for line in reader.read().decode().splitlines():
                if line.strip():
                    traces.extend(json.loads(line).get("traces") or [])
    return traces


def recorded_reward(trace: dict, name: str = "target_fix_fraction") -> float | None:
    rewards = trace.get("rewards")
    if isinstance(rewards, dict) and name in rewards:
        value = rewards[name]
        return float(value.get("score", 0.0) if isinstance(value, dict) else value)
    return None


def last_reply(trace: dict) -> str:
    for node in reversed(trace.get("nodes") or []):
        message = node.get("message") or {}
        if message.get("role") == "assistant" and message.get("content"):
            return message["content"]
    return ""


def tier_of(trace: dict) -> str:
    data = (trace.get("task") or {}).get("data") or {}
    return data.get("name") or "unknown"


def classify(reply: str, files: dict, verdict, reward: float) -> str:
    proposals = parse_proposals(reply, files)
    if not proposals:
        return "no_proposal"
    for body in proposals.values():
        try:
            ast.parse(body)
        except SyntaxError:
            return "invalid_syntax"
    if verdict and verdict["regressions"]:
        return "regression"
    if 0.0 < reward < 1.0:
        return "partial"
    return "no_progress"


def load_tasks() -> dict:
    return {task.data.name: task for task in SweLabTaskset(SweLabConfig(id="swe-lab")).load()}


def score_run(run_dir: Path, tasks: dict) -> dict:
    """Per-tier scoring for one run. Shared by the single-run and repeat reports."""
    per_tier: dict[str, list[dict]] = defaultdict(list)
    for trace in read_traces(run_dir):
        per_tier[tier_of(trace)].append(trace)

    summary = {}
    for tier in sorted(per_tier):
        rows = []
        invalid = 0
        for trace in per_tier[tier]:
            files = ((trace.get("task") or {}).get("data") or {}).get("files") or {}
            reply = last_reply(trace)
            recorded = recorded_reward(trace)
            if trace.get("stop_condition") in INVALID_STOPS or recorded is None or not reply.strip():
                invalid += 1
                continue
            task = tasks.get(tier)
            verdict = task._score(reply) if task else None
            reward = terrain.REWARDS["target_fix_fraction"](verdict) if verdict else 0.0
            rows.append(
                {
                    "reward": reward,
                    "recorded": recorded,
                    "failure": None if reward >= 1.0 else classify(reply, files, verdict, reward),
                }
            )
        solved = sum(1 for row in rows if row["reward"] >= 1.0)
        mixture = defaultdict(int)
        for row in rows:
            if row["failure"]:
                mixture[row["failure"]] += 1
        summary[tier] = {
            "n": len(rows) + invalid,
            "n_valid": len(rows),
            "n_invalid": invalid,
            "solved": solved,
            "solve_rate": solved / len(rows) if rows else None,
            "mean_rescored": sum(row["reward"] for row in rows) / len(rows) if rows else None,
            "mean_recorded": sum((row["recorded"] or 0.0) for row in rows) / len(rows) if rows else None,
            "failures": dict(mixture),
        }
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=None)
    ap.add_argument("--out", default=str(REPO / "outputs" / "swe_runs" / "frontier.json"))
    args = ap.parse_args()

    run_dirs = all_runs(args.run or RUN_GLOB)
    if not run_dirs:
        print("no swe-lab runs found for", args.run or RUN_GLOB)
        return 1
    run_dir = run_dirs[-1]

    tasks = load_tasks()
    summary = score_run(run_dir, tasks)
    if not summary:
        print("no traces in", run_dir)
        return 1

    print("run:", run_dir.name)
    print("%-24s %3s %6s %6s %7s %8s  %s"
          % ("tier", "n", "valid", "error", "solve", "rescored", "failure mixture (valid only)"))
    for tier in sorted(summary):
        row = summary[tier]
        print(
            "%-24s %3d %6d %6d %7s %8.3f  %s"
            % (
                tier,
                row["n"],
                row["n_valid"],
                row["n_invalid"],
                "%d/%d" % (row["solved"], row["n_valid"]) if row["n_valid"] else "n/a",
                row["mean_rescored"] or 0.0,
                ", ".join("%s=%d" % item for item in sorted(row["failures"].items())) or "-",
            )
        )

    unreliable = [tier for tier in sorted(summary) if summary[tier]["solve_rate"] not in (None, 1.0)]
    print("\nfrontier (first tier not solved on every valid attempt):",
          unreliable[0] if unreliable else "none")
    for tier in sorted(summary):
        rate = summary[tier]["solve_rate"]
        if rate == 1.0:
            print("  %-24s reliable (all %d valid attempts solved)" % (tier, summary[tier]["n_valid"]))
        elif rate is not None:
            print("  %-24s unreliable: %.0f%% of %d valid attempts" % (tier, rate * 100, summary[tier]["n_valid"]))
    print("\ncaveat: a single run at this n is noisy; for a stable rate see repeats.py")

    Path(args.out).write_text(
        json.dumps({"run": run_dir.name, "tiers": summary, "frontier": unreliable[:1]}, indent=1)
    )
    print("wrote", args.out)
    print("raw trajectories untouched in", run_dir.relative_to(REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())