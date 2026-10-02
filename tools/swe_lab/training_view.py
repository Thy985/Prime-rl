"""Phase 4 (data layer): trajectory -> training view, kept separate from the raw run.

The plan keeps these apart on purpose. A raw trajectory is the record of what
happened; a training example is a choice about what to train on, and the choice must
be explicit, reproducible and auditable rather than implied by reading the traces.

This tool applies a documented transformation and nothing else:

  filter      which episodes qualify (solved only, by default)
  select      which messages become the example (the whole conversation)
  mask        which messages carry loss (assistant turns only: content and tool
              calls; system, user and tool-result turns are context)
  view        the emitted JSONL plus a manifest recording the filters, the counts
              kept and dropped per tier, and the source runs

Raw trajectories are never modified: the run directory is read-only input, and every
example carries its provenance so a view can be rebuilt from the runs alone.

Deliberately excluded: `reasoning_content` is not copied into the view. It is model
scratchpad, it is not what a tool-use SFT target should imitate, and copying it
would silently double the supervision. The manifest records that choice.

usage: uv run python tools/swe_lab/training_view.py [--run <glob> ...]
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import zstandard

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from frontier import action_kind, all_runs, recorded_reward, tier_of, tool_calls

DEFAULT_RUNS = ("outputs/swe-lab-abc-A*",)
TRAINED_ROLE = "assistant"


def load_episodes(pattern: str) -> list[dict]:
    episodes = []
    for run_dir in all_runs(pattern):
        for path in sorted(run_dir.glob("monitors/file/traces/stream/*.jsonl.zst")):
            with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(path.read_bytes())) as reader:
                for line in reader.read().decode().splitlines():
                    if not line.strip():
                        continue
                    payload = json.loads(line)
                    for trace in payload.get("traces") or []:
                        episodes.append({"run": run_dir.name, "episode_id": payload.get("id"), "trace": trace})
    return episodes


def to_messages(trace: dict) -> list[dict]:
    """The conversation, with an explicit per-message training mask."""
    messages = []
    for node in trace.get("nodes") or []:
        source = node.get("message") or {}
        role = source.get("role")
        message = {"role": role, "content": source.get("content") or "", "train": role == TRAINED_ROLE}
        for key in ("name", "tool_call_id"):
            if source.get(key):
                message[key] = source[key]
        if source.get("tool_calls"):
            message["tool_calls"] = source["tool_calls"]
        messages.append(message)
    return messages


def build(run_patterns: list[str], require_solved: bool = True) -> tuple[list[dict], dict]:
    kept, dropped = [], Counter()
    per_tier_kept = Counter()
    per_tier_dropped = Counter()
    sources = []

    for pattern in run_patterns:
        episodes = load_episodes(pattern)
        if not episodes:
            continue
        sources.append({"pattern": pattern, "runs": sorted({e["run"] for e in episodes}), "episodes": len(episodes)})
        for episode in episodes:
            trace = episode["trace"]
            reward = recorded_reward(trace)
            tier = tier_of(trace)
            if reward is None:
                dropped["no_reward"] += 1
                per_tier_dropped[tier] += 1
                continue
            if require_solved and reward < 1.0:
                dropped["unsolved"] += 1
                per_tier_dropped[tier] += 1
                continue
            messages = to_messages(trace)
            if not any(m["train"] for m in messages):
                dropped["no_assistant_turn"] += 1
                per_tier_dropped[tier] += 1
                continue
            calls = tool_calls(trace)
            kept.append(
                {
                    "example_id": "%s:%s" % (episode["run"], episode["episode_id"]),
                    "source": {
                        "run": episode["run"],
                        "episode_id": episode["episode_id"],
                        "tier": tier,
                        "reward": reward,
                    },
                    "stats": {
                        "messages": len(messages),
                        "trained_messages": sum(1 for m in messages if m["train"]),
                        "tool_calls": len(calls),
                        "tool_mix": dict(Counter(call["name"] for call in calls)),
                        "writes": sum(1 for call in calls if action_kind(call) == "write"),
                    },
                    "messages": messages,
                }
            )
            per_tier_kept[tier] += 1

    manifest = {
        "transformation": {
            "filter": "reward == 1.0 (solved only)" if require_solved else "none",
            "select": "all messages of the episode",
            "mask": "loss on assistant turns only (content and tool_calls)",
            "excluded": ["reasoning_content (model scratchpad, not a tool-use target)"],
        },
        "sources": sources,
        "kept": len(kept),
        "dropped": dict(dropped),
        "kept_per_tier": dict(per_tier_kept),
        "dropped_per_tier": dict(per_tier_dropped),
        "note": "raw trajectories are read-only input; this view can be rebuilt from them",
    }
    return kept, manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", nargs="*", default=list(DEFAULT_RUNS))
    ap.add_argument("--out", default=str(REPO / "outputs" / "swe_runs" / "training_view.jsonl"))
    ap.add_argument("--manifest", default=str(REPO / "outputs" / "swe_runs" / "training_view.manifest.json"))
    ap.add_argument("--include-unsolved", action="store_true")
    args = ap.parse_args()

    examples, manifest = build(args.run, require_solved=not args.include_unsolved)
    if not examples:
        print("no examples built from", args.run)
        return 1

    out = Path(args.out)
    with out.open("w") as handle:
        for example in examples:
            handle.write(json.dumps(example) + "\n")
    Path(args.manifest).write_text(json.dumps(manifest, indent=1))

    print("kept %d examples, dropped %s" % (manifest["kept"], manifest["dropped"]))
    print("%-28s %6s %6s %8s %7s" % ("tier", "kept", "drop", "msgs", "tools"))
    tiers = sorted(set(manifest["kept_per_tier"]) | set(manifest["dropped_per_tier"]))
    for tier in tiers:
        group = [e for e in examples if e["source"]["tier"] == tier]
        msgs = sum(e["stats"]["messages"] for e in group) / len(group) if group else 0
        tools = sum(e["stats"]["tool_calls"] for e in group) / len(group) if group else 0
        print("%-28s %6d %6d %8.1f %7.1f"
              % (tier, manifest["kept_per_tier"].get(tier, 0), manifest["dropped_per_tier"].get(tier, 0), msgs, tools))

    masked_ok = all(
        m["train"] == (m["role"] == "assistant")
        for example in examples for m in example["messages"]
    )
    tool_context_untrained = all(
        m["train"] is False
        for example in examples for m in example["messages"] if m["role"] == "tool"
    )
    print("\nacceptance:")
    checks = [
        ("mask is exactly the assistant turns", masked_ok),
        ("tool results are context, never trained", tool_context_untrained),
        ("every example carries provenance", all(e["source"]["run"] for e in examples)),
        ("manifest records the transformation", bool(manifest["transformation"]["filter"])),
    ]
    for name, ok in checks:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
    print("\nwrote %s and %s" % (out, args.manifest))
    print("raw trajectories untouched")
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())