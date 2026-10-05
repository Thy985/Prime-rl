"""H_ADAPT state attribution: rebuild the scheduler's state sequence from a trace.

The adaptive harness advertises its affordances through the per-request tool list
(the only channel it owns): a request carrying only bash is RECON (the first one)
or VERIFY (a later one -- the rules allocate it only on the final turn), and a
request carrying bash+edit is EXECUTE. Assistant and tool nodes inherit the most
recent request's tools, so each call can be attributed to a state.

usage: uv run python tools/swe_lab/adapt_profile.py RUN [RUN ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "swe_lab"))

from behavior import call_kind  # noqa: E402
from frontier import read_traces  # noqa: E402


def states_and_calls(trace: dict):
    """Walk nodes; return (state_seq, calls) where calls carry their state."""
    request_tools = None
    state_seq = []
    calls = []
    for node in trace.get("nodes") or []:
        tools = node.get("tools")
        if tools:
            names = [t.get("name") for t in tools]
            has_edit = "edit" in names
            state = "EXECUTE" if has_edit else ("RECON" if not state_seq else "VERIFY")
            if not state_seq:
                state = "RECON"
            elif has_edit:
                state = "EXECUTE"
            else:
                state = "VERIFY"
            state_seq.append(state)
            request_tools = state
            continue
        if not node.get("sampled"):
            continue
        msg = node.get("message") or {}
        for call in msg.get("tool_calls") or []:
            name = call.get("name") or (call.get("function") or {}).get("name")
            calls.append((request_tools, {"name": name, "arguments": call.get("arguments")}))
    return state_seq, calls


def main() -> int:
    runs = sys.argv[1:] or ["rl-adapt"]
    for run in runs:
        run_dir = Path(f"outputs/{run}")
        if not run_dir.exists():
            print(f"{run}: no such run")
            continue
        print(f"=== {run} ===")
        for tr in read_traces(run_dir):
            seq, calls = states_and_calls(tr)
            inst = tr["task"]["data"].get("name", "?")
            score = (tr.get("rewards") or {}).get("resolve", {}).get("score", 0)
            kinds = [call_kind(c) for _, c in calls]
            print(f"  {inst:<28} solve={score} states={seq}")
            print(f"      kinds={kinds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())