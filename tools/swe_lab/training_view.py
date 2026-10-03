"""Phase 4 (data layer): trajectory -> training view, kept separate from the raw run.

The plan keeps these apart on purpose. A raw trajectory is the record of what
happened; a training example is a choice about what to train on, and the choice must
be explicit, reproducible and auditable rather than implied by reading the traces.

This tool applies a documented transformation and nothing else:

  filter      which episodes qualify (solved only, by default)
  select      which messages become the example (the canonical branch)
  mask        which messages carry loss (assistant turns only: content and tool
              calls; system, user and tool-result turns are context)
  strip       harness-injected control text, in two places:
              (a) user messages whose content begins with "PHASE " (the
                  recon/execute/verify instructions the staged harness appended
                  between calls) are dropped;
              (b) the system message is normalized to the eval-time H_A system
                  prompt via --system-from. The staged harness injects a 7-line
                  phase protocol into the system prompt; at eval time the model
                  will not see it, so training with it would bake the runtime
                  control protocol into the policy.
              Neither is part of the task, and either one silently turns a
              behavior-distillation dataset into a protocol-memorization one.
              The manifest records both counts per source.
  view        the emitted JSONL plus a manifest recording the filters, the counts
              kept and dropped per tier, and the source runs

Raw trajectories are never modified: the run directory is read-only input, and every
example carries its provenance so a view can be rebuilt from the runs alone.

The canonical branch is the root-to-leaf path of the trace's final turn, following
physical parent links backwards and skipping nothing. This matters for harnesses that
change the advertised tool set mid-episode: when a read-only recon phase ends, the
graph recorder re-roots the duplicate prefix as a parallel branch because the
system node's tools_hash no longer matches, and the episode's node list carries the
recon prefix twice. A node-level read of the trace would silently double-train that
prefix; the branch walk does not. Episodes whose tool set is constant carry a
single-branch trace, and the walk is the identity there.

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
from collections import Counter
from pathlib import Path

import zstandard

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from frontier import action_kind, all_runs, recorded_reward, tier_of, tool_calls

DEFAULT_RUNS = ("outputs/swe-lab-abc-A*",)
DEFAULT_SYSTEM_SOURCE = "outputs/swe-lab-budget-hA"
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


def canonical_nodes(trace: dict) -> list[dict]:
    """The trace's canonical branch: the last node's physical parent chain, root first.

    The leaf is the most recent node (the final assistant reply or a turn stopped by
    the budget). Parallel branches created by the graph recorder's re-rooting are
    siblings, not ancestors, so the walk never crosses into them.
    """
    nodes = trace.get("nodes") or []
    if not nodes:
        return []
    chain = []
    current = len(nodes) - 1
    while current is not None:
        chain.append(nodes[current])
        current = nodes[current].get("parent")
    chain.reverse()
    return chain


def trim_unanswered_tool_calls(messages: list[dict]) -> int:
    """Drop a trailing assistant turn whose tool calls never ran.

    When the turn budget binds, the framework stops the episode right after the model
    issued its tool calls, so the branch ends on an assistant message with no tool
    result following it. Training that turn is actively harmful: the trainer appends a
    stop token after every assistant message, so the target would teach the model to
    end its turn, and its episode, right after emitting a tool call. Trimming the tail
    keeps the valid prefix and removes the malformed end.
    """
    pending = 0
    start = None
    for index, message in enumerate(messages):
        if message["role"] == "assistant" and message.get("tool_calls"):
            pending = len(message["tool_calls"])
            start = index
        elif message["role"] == "tool" and pending:
            pending -= 1
    if not pending or start is None:
        return 0
    return len(messages) - start


def to_messages(trace: dict, canonical_system: str | None = None) -> tuple[list[dict], int, bool, int]:
    """The canonical conversation branch, with an explicit per-message training mask.

    Returns (messages, phase_stripped, system_normalized). When `canonical_system` is
    given, the episode's system message is replaced by it, so every view renders the
    same system prompt the protocol-invariant eval will show.
    """
    messages = []
    stripped = 0
    normalized_system = False
    for node in canonical_nodes(trace):
        source = node.get("message") or {}
        role = source.get("role")
        content = source.get("content") or ""
        if role == "user" and content.startswith("PHASE "):
            stripped += 1
            continue
        if role == "system" and canonical_system is not None:
            content = canonical_system
            normalized_system = True
        message = {"role": role, "content": content, "train": role == TRAINED_ROLE}
        for key in ("name", "tool_call_id"):
            if source.get(key):
                message[key] = source[key]
        if source.get("tool_calls"):
            message["tool_calls"] = source["tool_calls"]
        messages.append(message)
    trimmed = trim_unanswered_tool_calls(messages)
    return messages, stripped, normalized_system, trimmed


def canonical_system_prompt(system_from: str | None) -> str | None:
    """The eval-time system prompt, read from the harness that will run the eval.

    The staged harness injects a phase protocol into its system prompt, so a view
    built from it would teach the policy to expect text the eval never sends.
    Reading the prompt from the eval's own harness keeps the two in step by
    construction rather than by pattern-matching the protocol text.
    """
    if not system_from:
        return None
    episodes = load_episodes(system_from)
    for episode in episodes:
        for node in canonical_nodes(episode["trace"]):
            message = node.get("message") or {}
            if message.get("role") == "system":
                return message.get("content") or ""
    raise SystemExit("no system message found in --system-from %s" % system_from)


def build(
    run_patterns: list[str],
    require_solved: bool = True,
    canonical_system: str | None = None,
) -> tuple[list[dict], dict]:
    kept, dropped = [], Counter()
    per_tier_kept = Counter()
    per_tier_dropped = Counter()
    sources = []

    for pattern in run_patterns:
        episodes = load_episodes(pattern)
        if not episodes:
            continue
        src_entry = {
            "pattern": pattern,
            "runs": sorted({e["run"] for e in episodes}),
            "episodes": len(episodes),
            "phase_messages_stripped": 0,
            "system_prompts_normalized": 0,
            "unanswered_tool_turns_trimmed": 0,
        }
        sources.append(src_entry)
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
            messages, stripped, sys_norm, trimmed = to_messages(trace, canonical_system)
            if trimmed:
                messages = messages[:-trimmed]
            if not any(m["train"] for m in messages):
                dropped["no_assistant_turn"] += 1
                per_tier_dropped[tier] += 1
                continue
            calls = tool_calls(trace)
            canon = canonical_nodes(trace)
            example = {
                "example_id": "%s:%s" % (episode["run"], episode["episode_id"]),
                "stripped_phase_messages": stripped,
                "system_prompt_normalized": sys_norm,
                "trimmed_unanswered_turns": trimmed,
                # The trace's flat tool list is the union over the episode, so a staged
                # run contributes the same bash+edit surface a free run does, even though
                # its recon turn advertised bash alone. Rendering the union is the point:
                # the eval-time prompt must match, and the eval advertises both tools
                # from turn 1.
                "tool_defs": trace.get("tools") or [],
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
                "_canon": canon,
                "_trace": trace,
            }
            kept.append(example)
            per_tier_kept[tier] += 1
            src_entry["phase_messages_stripped"] += stripped
            src_entry["system_prompts_normalized"] += int(sys_norm)
            src_entry["unanswered_tool_turns_trimmed"] += trimmed

    manifest = {
        "transformation": {
            "filter": "reward == 1.0 (solved only)" if require_solved else "none",
            "select": "canonical branch only (the final turn's parent chain; re-rooted duplicate prefixes are siblings, not ancestors)",
            "mask": "loss on assistant turns only (content and tool_calls)",
            "excluded": ["reasoning_content (model scratchpad, not a tool-use target)"],
            "system_prompt": (
                "normalized to the eval-time harness prompt" if canonical_system is not None else "as recorded"
            ),
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
    ap.add_argument(
        "--system-from",
        default=DEFAULT_SYSTEM_SOURCE,
        help="run glob whose system prompt is the eval-time prompt; every view is normalized to it",
    )
    ap.add_argument("--keep-system", action="store_true", help="do not normalize the system prompt")
    args = ap.parse_args()

    canonical_system = None if args.keep_system else canonical_system_prompt(args.system_from)
    examples, manifest = build(args.run, require_solved=not args.include_unsolved, canonical_system=canonical_system)
    if not examples:
        print("no examples built from", args.run)
        return 1

    out = Path(args.out)
    with out.open("w") as handle:
        for example in examples:
            record = {k: v for k, v in example.items() if k not in ("_canon", "_trace")}
            handle.write(json.dumps(record) + "\n")
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
    branch_ok = True
    for example in examples:
        trace = example.get("_trace")
        branch = example.get("_canon") or []
        if not trace or not branch:
            branch_ok = False
            break
        nodes = trace.get("nodes") or []
        seen_pairs = set()
        for n in branch:
            key = (n.get("parent"), json.dumps((n.get("message") or {}).get("content"), sort_keys=True))
            if key in seen_pairs:
                branch_ok = False
                break
            seen_pairs.add(key)
        if not branch_ok:
            break
        leaf_id = None
        for i, n in enumerate(nodes):
            if n is branch[-1]:
                leaf_id = i
                break
        if leaf_id is None or any(n.get("parent") == leaf_id for n in nodes):
            branch_ok = False
            break
        num_turns = trace.get("num_turns")
        model_calls = sum(1 for n in branch if (n.get("message") or {}).get("role") == "assistant")
        if num_turns is not None and model_calls != num_turns:
            branch_ok = False
            break
    phase_leak = sum(1 for e in examples for m in e["messages"] if m["role"] == "user" and m["content"].startswith("PHASE "))
    system_prompts = {m["content"] for e in examples for m in e["messages"] if m["role"] == "system"}
    tool_pair_ok = True
    for e in examples:
        pending = []
        for m in e["messages"]:
            if m["role"] == "assistant" and m.get("tool_calls"):
                pending = [c["id"] for c in m["tool_calls"]]
            elif m["role"] == "tool" and pending:
                if m.get("tool_call_id") == pending[0]:
                    pending.pop(0)
        if pending:
            tool_pair_ok = False
            break
    checks = [
        ("mask is exactly the assistant turns", masked_ok),
        ("tool results are context, never trained", tool_context_untrained),
        ("every example carries provenance", all(e["source"]["run"] for e in examples)),
        ("manifest records the transformation", bool(manifest["transformation"]["filter"])),
        ("the canonical branch is the sampled path (no duplicate prefixes)", branch_ok),
        ("no harness phase prompt in the view", phase_leak == 0),
        ("one system prompt across the view", len(system_prompts) <= 1),
        ("every tool call is answered by its tool result", tool_pair_ok),
        ("every example declares its tools", all(e.get("tool_defs") for e in examples)),
    ]
    for name, ok in checks:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
    print("\nwrote %s and %s" % (out, args.manifest))
    print("raw trajectories untouched")
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())