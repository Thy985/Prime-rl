"""Phase 4C (bridge): training view JSONL -> the parquet SFTDataset reads.

prime-rl's `SFTDataset` takes a `messages` column (a whole-chat training sample) plus
either `tools` or `tool_defs`, and masks loss by role: assistant only by default. That
is exactly the shape training_view.py emits, so this tool is a schema adapter and
nothing more -- it does not re-select, re-filter, or re-mask anything.

Two columns are added that the view deliberately does not carry:

  tool_defs   the flat tool list the episode ran with. Required: a chat template cannot
               render `tool_calls` without the definitions, and without it the trainer
               would render tool calls with no declared tools -- an unlearnable target.
  source      provenance (run, tier, reward) carried through for audit. Not read by the
               trainer; kept so a trained checkpoint can be traced back to its episodes.

One field is dropped: the view's per-message `train` flag. The trainer's loss mask is
role-based (`LossMaskConfig` defaults to assistant-only, system/user/tool masked), which
is the same rule the view records, and an extra key in every message dict would be handed
to the chat template for no benefit. The flag stays in the JSONL view, which is the audit
artifact; the parquet is the trainer artifact.

usage: uv run python tools/swe_lab/sft_export.py --view <jsonl> --out <dir>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[2]


def load_view(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


TRAINER_KEYS = ("role", "content", "name", "tool_call_id", "tool_calls")


def messages_of(example: dict) -> list[dict]:
    """The view's messages with trainer-relevant keys only, nulls dropped.

    A message that carried no tool calls must not keep a `tool_calls: null` entry: the
    view emits the key for every message for uniformity, and a null there is not the same
    as an absent key to a chat template.
    """
    out = []
    for message in example["messages"]:
        clean = {key: message[key] for key in TRAINER_KEYS if message.get(key) is not None}
        out.append(clean)
    return out


def tools_of(example: dict) -> list[dict]:
    """The tool definitions the episode ran with."""
    return example.get("tool_defs") or []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--view", required=True)
    ap.add_argument("--out", required=True, help="output directory for the parquet shard")
    args = ap.parse_args()

    view_path = Path(args.view)
    examples = load_view(view_path)
    if not examples:
        print("empty view:", view_path)
        return 1

    missing_tools = [e["example_id"] for e in examples if not tools_of(e)]
    if missing_tools:
        print("view has no tool_defs on %d/%d examples (first: %s)" % (len(missing_tools), len(examples), missing_tools[0]))
        return 1

    rows = {
        "messages": [messages_of(e) for e in examples],
        "tool_defs": [tools_of(e) for e in examples],
        "source": [
            {"run": e["source"]["run"], "tier": e["source"]["tier"], "reward": e["source"]["reward"]}
            for e in examples
        ],
    }
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    shard = out_dir / "train-00000-of-00001.parquet"
    pq.write_table(pa.table(rows), shard)

    trained = sum(
        1 for e in examples for m in e["messages"] if m["role"] == "assistant"
    )
    print("wrote %d rows to %s" % (len(examples), shard))
    print("  assistant turns (loss-bearing): %d" % trained)
    print("  mean messages/episode: %.1f" % (sum(len(e["messages"]) for e in examples) / len(examples)))
    print("  per tier: %s" % {t: sum(1 for e in examples if e["source"]["tier"] == t)
                              for t in sorted({e["source"]["tier"] for e in examples})})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())