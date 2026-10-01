"""Phase 3: the capability frontier across the swe-lab tiers.

Reads a finished eval run, decompresses its stream traces, and re-derives every
score from the saved reply through the taskset's own scorer. Re-deriving rather
than trusting the recorded number is deliberate: the recorded reward reflects the
parser as it was at run time, and a parser fix must be able to correct the
measurement without re-rolling the model. Both numbers are reported.

Per tier it reports solve rate and a failure mixture, so the frontier is located
instead of averaged away:

  no_proposal     the reply yielded no file contents at all
  invalid_syntax  a proposed file does not compile
  regression      a previously passing test broke
  partial         some target tests fixed, not all
  no_progress     parsed and valid, but no target test fixed

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

FAILURES = ("no_proposal", "invalid_syntax", "regression", "partial", "no_progress")


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=None)
    ap.add_argument("--out", default=str(REPO / "outputs" / "swe_runs" / "frontier.json"))
    args = ap.parse_args()

    candidates = Path(args.run) if args.run else None
    if candidates is not None and candidates.is_absolute():
        run_dirs = [candidates] if candidates.is_dir() else sorted(candidates.parent.glob(candidates.name))
    else:
        run_dirs = sorted(REPO.glob(args.run or RUN_GLOB))
    if not run_dirs:
        print("no swe-lab runs found for", args.run or RUN_GLOB)
        return 1
    run_dir = max(run_dirs, key=lambda path: path.stat().st_mtime)

    tasks = {task.data.name: task for task in SweLabTaskset(SweLabConfig(id="swe-lab")).load()}
    traces = read_traces(run_dir)
    if not traces:
        print("no traces in", run_dir)
        return 1

    per_tier: dict[str, list[dict]] = defaultdict(list)
    for trace in traces:
        per_tier[tier_of(trace)].append(trace)

    summary = {}
    print("run:", run_dir.name)
    print("%-24s %3s %7s %8s %8s  %s" % ("tier", "n", "solve", "rescored", "recorded", "failure mixture"))
    for tier in sorted(per_tier):
        rows = []
        for trace in per_tier[tier]:
            files = ((trace.get("task") or {}).get("data") or {}).get("files") or {}
            reply = last_reply(trace)
            task = tasks.get(tier)
            verdict = task._score(reply) if task else None
            reward = terrain.REWARDS["target_fix_fraction"](verdict) if verdict else 0.0
            rows.append(
                {
                    "reward": reward,
                    "recorded": recorded_reward(trace),
                    "failure": None if reward >= 1.0 else classify(reply, files, verdict, reward),
                }
            )
        solved = sum(1 for row in rows if row["reward"] >= 1.0)
        mixture = defaultdict(int)
        for row in rows:
            if row["failure"]:
                mixture[row["failure"]] += 1
        print(
            "%-24s %3d %7s %8.3f %8.3f  %s"
            % (
                tier,
                len(rows),
                "%d/%d" % (solved, len(rows)),
                sum(row["reward"] for row in rows) / len(rows),
                sum((row["recorded"] or 0.0) for row in rows) / len(rows),
                ", ".join("%s=%d" % item for item in sorted(mixture.items())) or "-",
            )
        )
        summary[tier] = {
            "n": len(rows),
            "solve_rate": solved / len(rows),
            "mean_rescored": sum(row["reward"] for row in rows) / len(rows),
            "mean_recorded": sum((row["recorded"] or 0.0) for row in rows) / len(rows),
            "failures": dict(mixture),
        }

    unsolved = [tier for tier in sorted(summary) if summary[tier]["solve_rate"] < 1.0]
    print("\nfrontier (first unsolved tier):", unsolved[0] if unsolved else "none, all tiers solved")
    Path(args.out).write_text(
        json.dumps({"run": run_dir.name, "tiers": summary, "frontier": unsolved[:1]}, indent=1)
    )
    print("wrote", args.out)
    print("raw trajectories untouched in", run_dir.relative_to(REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())