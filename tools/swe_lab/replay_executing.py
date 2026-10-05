"""Executing-reward replay: re-derive the reward from a saved trace and compare.

`vf-replay` re-scores "judges + trace-only signals; no runtime", so it cannot
re-score a reward that executes the suite. This is the counterpart for that case:
it reads a saved `traces.jsonl`, re-extracts the model's proposed file from the
recorded reply, re-runs the audited verifier, and requires the re-derived reward
to equal the reward recorded on the trace.

That equality is the Phase 1B acceptance condition: the episode must be a
reproducible unit of experiment, not a one-off number.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import terrain as terrain_verifier

REPO = Path(__file__).resolve().parents[2]
DEFAULT_GLOB = "outputs/swe-lab--primeintellect*/traces.jsonl"


def assistant_reply(trace: dict) -> str:
    """The last assistant message on the trace, which is what the reward consumed."""
    nodes = trace.get("nodes") or []
    for node in reversed(nodes):
        message = node.get("message") or {}
        if message.get("role") == "assistant" and message.get("content"):
            return message["content"]
    return nodes[-1]["message"]["content"] if nodes else ""


def recorded_reward(trace: dict, name: str) -> float | None:
    rewards = trace.get("rewards")
    if isinstance(rewards, dict) and name in rewards:
        value = rewards[name]
        if isinstance(value, dict):
            value = value.get("score", 0.0)
        return float(value)
    if isinstance(rewards, list):
        for item in rewards:
            if isinstance(item, dict) and item.get("handler") == name:
                return float(item.get("score", 0.0))
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", default=DEFAULT_GLOB)
    args = ap.parse_args()

    candidates = Path(args.traces)
    paths = [candidates] if candidates.is_absolute() else sorted(REPO.glob(args.traces))
    if not paths:
        print("no saved traces matching", args.traces)
        return 1

    baseline = terrain_verifier.baseline_outcome()
    total, equal = 0, 0
    live_values: list[float] = []
    for path in paths:
        if path.suffix == ".zst":
            import io
            import zstandard

            with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(path.read_bytes())) as reader:
                text = reader.read().decode()
        else:
            text = path.read_text()
        for line in text.splitlines():
            if not line.strip():
                continue
            episode = json.loads(line)
            for trace in episode.get("traces") or []:
                reply = assistant_reply(trace)
                live = recorded_reward(trace, "target_fix_fraction")
                blocks = terrain_verifier.CODE_BLOCK.findall(reply) if hasattr(terrain_verifier, "CODE_BLOCK") else []
                if not blocks:
                    import re

                    blocks = re.findall(r"```(?:python)?\s*\n(.*?)```", reply, re.DOTALL)
                replayed = 0.0
                if blocks:
                    verdict = terrain_verifier.evaluate({"calculator.py": max(blocks, key=len)}, baseline)
                    replayed = terrain_verifier.REWARDS["target_fix_fraction"](verdict)
                total += 1
                if live is not None:
                    live_values.append(live)
                same = live is not None and abs(live - replayed) < 1e-9
                equal += int(same)
                print(
                    "trace=%s blocks=%d recorded=%.3f replayed=%.3f -> %s"
                    % (str(trace.get("id"))[:12], len(blocks), live if live is not None else -1.0, replayed,
                       "EQUAL" if same else "DIFFER")
                )
                print("  path=%s" % path.relative_to(REPO))

    # The live trace scores 0, and 0 == 0 is weak evidence: a replay path that was
    # broken and always returned 0 would also "match". Force a non-zero replay by
    # substituting the known-correct repair for the same trace, and require 1.0.
    golden = "```python\n" + terrain_verifier.with_ranges(terrain_verifier.with_median()) + "\n```"
    blocks = __import__("re").findall(r"```(?:python)?\s*\n(.*?)```", golden, __import__("re").DOTALL)
    pos_verdict = terrain_verifier.evaluate({"calculator.py": blocks[0]}, baseline)
    pos = terrain_verifier.REWARDS["target_fix_fraction"](pos_verdict)
    print("positive control (golden reply): replayed=%.3f -> %s" % (pos, "OK" if pos == 1.0 else "BROKEN"))

    print("\ntraces replayed=%d equal=%d" % (total, equal))
    ok = total > 0 and equal == total and pos == 1.0
    print("Phase 1B executing replay:", "PASS" if ok else "FAIL")
    if any(abs(v) > 0 for v in live_values):
        print("note: the live equality is on a NON-ZERO reward, so the executing replay path")
        print("      is exercised end to end rather than merely matching at zero.")
    else:
        print("note: the live equality is 0==0 (a truncated reply); the positive control is")
        print("      what shows the replay path can produce a non-zero score.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())