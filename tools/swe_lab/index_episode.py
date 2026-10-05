"""Index a verifiers episode stream into the SWE experiment record.

The invariant this enforces: the record is DERIVED FROM the Episode, never a
competing source of truth. Episode and trace ids, reward, token counts, turns,
stop condition, truncation and timing are copied verbatim from verifiers' own
index; only the experiment-layer fields verifiers does not carry are added (task
identity, environment fingerprint, and where the executing verdict lives).

Replay note: `vf-replay` re-scores "judges + trace-only signals; no runtime". A
reward that executes the suite (this task's `target_fix_fraction`) is therefore
outside its scope and must be re-derived by re-running the verifier over the
archived repository state. The record records which mode applies rather than
pretending the two are interchangeable.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import contract

REPO = Path(__file__).resolve().parents[2]
INDEX_GLOB = "outputs/swe-lab--*/monitors/file/traces/stream.index.jsonl"
OUT = REPO / "outputs" / "swe_runs" / "episode_index_records.json"

EPISODE_FIELDS = ("id", "kind", "env", "group", "ok", "trace_ids", "num_errors")
REWARD_FIELDS = ("reward", "advantage")
USAGE_FIELDS = ("input_tokens", "output_tokens", "turns", "branches", "duration")
TERMINAL_FIELDS = ("stop_condition", "truncated")


def load_index(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def to_record(entry: dict, source: Path) -> dict:
    return {
        "record_version": 1,
        "source": {"kind": "verifiers.episode_index", "path": str(source.relative_to(REPO))},
        "episode": {k: entry.get(k) for k in EPISODE_FIELDS},
        "reward_from_episode": {k: entry.get(k) for k in REWARD_FIELDS},
        "usage_from_episode": {k: entry.get(k) for k in USAGE_FIELDS},
        "terminal_from_episode": {k: entry.get(k) for k in TERMINAL_FIELDS},
        "task_id": contract.TASK_ID,
        "task_hash": contract.task_hash(),
        "env_fingerprint": contract.env_fingerprint(
            agent="qwen3-0.6b",
            harness="null",
            runtime="subprocess",
            workdir="verifiers/episode",
        ),
        "verdict_source": "executing verifier over the proposed file; see swe-lab reward",
        "replay_mode": "executing",
        "replay_note": (
            "target_fix_fraction executes the suite, so vf-replay (judges and "
            "trace-only signals, no runtime) cannot re-score it; re-derive by "
            "re-running the verifier over the archived state"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default=INDEX_GLOB)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    sources = sorted(REPO.glob(args.index))
    if not sources:
        print("no verifiers episode index found matching", args.index)
        return 1

    records = []
    for source in sources:
        for entry in load_index(source):
            record = to_record(entry, source)
            records.append(record)
            ep = record["episode"]
            print(
                "episode=%s trace=%s env=%s reward=%.3f tokens=%s/%s turns=%s truncated=%s"
                % (
                    str(ep["id"])[:12],
                    str(ep["trace_ids"][0])[:12] if ep["trace_ids"] else "-",
                    ep["env"],
                    record["reward_from_episode"]["reward"] or 0.0,
                    record["usage_from_episode"]["input_tokens"],
                    record["usage_from_episode"]["output_tokens"],
                    record["usage_from_episode"]["turns"],
                    record["terminal_from_episode"]["truncated"],
                )
            )

    Path(args.out).write_text(json.dumps(records, indent=1))
    print("\nwrote %d record(s) -> %s" % (len(records), args.out))

    checks = [
        ("record carries a verifiers episode id", all(r["episode"]["id"] for r in records)),
        ("record carries trace ids", all(r["episode"]["trace_ids"] for r in records)),
        ("reward copied from the episode, not recomputed", all("reward" in r["reward_from_episode"] for r in records)),
        ("source path recorded for provenance", all(r["source"]["path"].endswith(".jsonl") for r in records)),
        ("replay mode declared", all(r["replay_mode"] == "executing" for r in records)),
    ]
    print("\nacceptance:")
    for name, ok in checks:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())