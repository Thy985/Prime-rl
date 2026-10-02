"""Phase 3: how a Harness D rollout spends its turn allowance.

H_D prescribes an allocation (plan 1 turn, execute 2, feedback the rest) instead of
letting the model's own text reply end the episode, so its runs need a report the
solve rate cannot give: which phases were reached, how many model calls each one took,
and where the edits actually happened.

Only `sampled` nodes are model calls. User/phase markers and tool results are
conversation content: they are read for attribution and are never counted as turns.
A trace whose recorder re-rooted the conversation repeats the first model call as a
non-sampled node, which is why the count is on `sampled` and not on "assistant nodes".

usage: uv run python tools/swe_lab/hd_phases.py [--pattern 'outputs/swe-lab-budget-hD*']
"""

from __future__ import annotations

import argparse
import glob
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

import zstandard

REFUSAL = "this is the planning turn"
PHASE_LABELS = ("PLAN", "EXECUTE", "FEEDBACK")
DEFAULT_PATTERN = "outputs/swe-lab-budget-hD*"


def load(pattern: str) -> list[tuple[str, dict]]:
    episodes = []
    for run_dir in sorted(glob.glob(pattern)):
        for path in sorted(Path(run_dir).glob("monitors/file/traces/stream/*.jsonl.zst")):
            with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(path.read_bytes())) as reader:
                for line in reader.read().decode().splitlines():
                    if line.strip():
                        for trace in json.loads(line).get("traces") or []:
                            episodes.append((Path(run_dir).name, trace))
    return episodes


def read_episode(trace: dict) -> dict:
    """One episode's phase trail: calls, tool mix, refusals and the closing reply."""
    phase = "prompt"
    reached: list[str] = []
    calls: Counter = Counter()
    tools: Counter = Counter()
    refusals = 0
    plan: int | None = None
    for node in trace.get("nodes") or []:
        message = node.get("message") or {}
        role = message.get("role")
        content = message.get("content") or ""
        if role == "user" and content.startswith("PHASE"):
            label = content.split(".")[0].replace("PHASE ", "").strip().split(" -- ")[-1]
            if not reached or reached[-1] != label:
                reached.append(label)
            phase = label
            continue
        if role == "assistant":
            if not node.get("sampled"):
                continue
            calls[phase] += 1
            for call in message.get("tool_calls") or []:
                tools[(phase, call.get("name"))] += 1
            if phase == "PLAN" and not (message.get("tool_calls") or []) and plan is None:
                plan = len(content.strip())
            continue
        if role == "tool" and content.startswith(REFUSAL):
            refusals += 1
    reward = (trace.get("rewards") or {}).get("target_fix_fraction")
    return {
        "tier": ((trace.get("task") or {}).get("data") or {}).get("tier"),
        "reached": reached,
        "calls": calls,
        "tools": tools,
        "refusals": refusals,
        "plan_chars": plan,
        "reward": reward.get("score") if isinstance(reward, dict) else reward,
        "stop": trace.get("stop_condition"),
        "turns": sum(1 for node in (trace.get("nodes") or []) if node.get("sampled")),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pattern", default=DEFAULT_PATTERN)
    args = ap.parse_args()

    rows = [(run, read_episode(trace)) for run, trace in load(args.pattern)]
    if not rows:
        print("no episodes for", args.pattern)
        return 1
    runs = sorted({run for run, _ in rows})
    print("pattern: %s" % args.pattern)
    print("episodes: %d over %d run(s): %s" % (len(rows), len(runs), ", ".join(runs)))
    for run in runs:
        group = [row for name, row in rows if name == run]
        reached = Counter(phase for row in group for phase in set(row["reached"]))
        solved = sum(1 for row in group if (row["reward"] or 0) >= 1.0)
        print("\n%s  episodes=%d solved=%d (%.0f%%)" % (run, len(group), solved, 100.0 * solved / len(group)))
        print("  reached: " + "  ".join("%s %d/%d" % (p, reached[p], len(group)) for p in PHASE_LABELS))
        print("  mean sampled calls: " + "  ".join(
            "%s %.2f" % (p, sum(row["calls"][p] for row in group) / len(group)) for p in PHASE_LABELS))
        print("  plan written in the planning turn: %d/%d   planning write refusals fired: %d"
              % (sum(1 for row in group if row["plan_chars"]), len(group), sum(row["refusals"] for row in group)))
        print("  stops: %s" % dict(Counter(row["stop"] for row in group)))
        tools = Counter()
        for row in group:
            tools.update(row["tools"])
        print("  tool mix: " + ("  ".join("%s/%s:%d" % (p, t, n) for (p, t), n in sorted(tools.items())) or "-"))

    print("\npooled per tier:")
    by_tier: dict[str, list[dict]] = defaultdict(list)
    for _, row in rows:
        by_tier[row["tier"]].append(row)
    for tier in sorted(by_tier):
        group = by_tier[tier]
        solved = sum(1 for row in group if (row["reward"] or 0) >= 1.0)
        edited_late = [row for row in group if row["tools"].get(("FEEDBACK", "edit"), 0) > 0]
        late_solved = sum(1 for row in edited_late if (row["reward"] or 0) >= 1.0)
        print("  %-24s solve %2d/%2d (%3.0f%%) | plan bash %.1f | execute edit %.1f | feedback edit %.1f"
              % (tier, solved, len(group), 100.0 * solved / len(group),
                 sum(row["tools"].get(("PLAN", "bash"), 0) for row in group) / len(group),
                 sum(row["tools"].get(("EXECUTE", "edit"), 0) for row in group) / len(group),
                 sum(row["tools"].get(("FEEDBACK", "edit"), 0) for row in group) / len(group)))
        print("  %-24s   edited during feedback: %d/%d, of those solved %d"
              % ("", len(edited_late), len(group), late_solved))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())