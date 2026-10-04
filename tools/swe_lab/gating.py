"""What does H_D's runtime gate actually do to the agent, turn by turn?

The triangle (H_A / H_A' / H_D) shows the gain is not in the instruction text, so
this probe asks the mechanical question instead: per phase, which tools the
request actually carried, what the agent called, and what a refused write returned.

The tool list lives on the request nodes only, so each assistant node inherits the
tools of the most recent request node -- which is what the model was offered for
that very turn.

usage: uv run python tools/swe_lab/gating.py outputs/rl-hD outputs/rl-hAp ...
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import zstandard as zstd

PHASE = re.compile(r"PHASE \d+ of \d+ -- ([A-Z]+)")
# The exact refusal the planner emits for a tree-changing bash command; matching
# loose words like "must not" instead would flag ordinary file contents the agent
# catted back.
REFUSAL = re.compile(r"writes are not allowed in this turn")


def episodes(run: Path):
    for chunk in sorted((run / "monitors" / "file" / "traces" / "stream").glob("*.jsonl.zst")):
        reader = zstd.ZstdDecompressor().stream_reader(open(chunk, "rb"))
        for line in reader.read(40_000_000).decode("utf-8", "replace").splitlines():
            if line.strip():
                yield json.loads(line)


def call_of(msg: dict):
    """Return (tool name, the command or path it was asked to touch)."""
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or tc
        raw = fn.get("arguments", "")
        try:
            args = json.loads(raw) if isinstance(raw, str) else raw
        except ValueError:
            args = {}
        return fn.get("name", "?"), str((args or {}).get("command") or (args or {}).get("path") or "")
    return None, ""


def command_head(command: str) -> str:
    """First tokens of a bash command, enough to tell read from write from test."""
    toks = command.split()
    if not toks:
        return "(empty)"
    head = " ".join(toks[:2])
    if any(t in command for t in ("runtests", "pytest", "tox ", "manage.py test")):
        return "TEST: " + head
    if any(t in toks for t in (">", ">>", "sed -i", "tee", "patch", "cp ", "mv ", "rm ")):
        return "WRITE: " + head
    return head


def trace_turns(trace: dict) -> list[dict]:
    turns, offered = [], []
    for node in trace["nodes"]:
        if node.get("tools"):
            offered = [t["name"] for t in node["tools"]]
        msg = node.get("message", {})
        role, content = msg.get("role"), str(msg.get("content") or "")
        label = PHASE.search(content)
        if label:
            turns.append({"kind": "phase", "phase": label.group(1), "offered": list(offered)})
        elif role == "assistant":
            name, target = call_of(msg)
            turns.append({"kind": "act", "call": name, "target": target, "offered": list(offered)})
        elif role == "tool":
            turns.append({"kind": "result", "text": content[:300], "refused": bool(REFUSAL.search(content))})
    return turns


def main() -> int:
    rows = []
    for run_name in sys.argv[1:]:
        for ep in episodes(Path(run_name)):
            tr = ep["traces"][0]
            rows.append({"run": Path(run_name).name, "reward": tr["rewards"].get("resolve"), "turns": trace_turns(tr)})

    phases, offered_by_phase, calls, violations, after = Counter(), Counter(), Counter(), Counter(), Counter()
    heads = Counter()
    for r in rows:
        # Unstaged harnesses never announce a phase; their turns are the control.
        phase = "free"
        for i, t in enumerate(r["turns"]):
            if t["kind"] == "phase":
                phase, _ = t["phase"], phases.update({t["phase"]: 1})
                offered_by_phase[(phase, "edit_offered" if "edit" in t["offered"] else "bash_only")] += 1
            elif t["kind"] == "act":
                calls[(phase, t["call"])] += 1
                if t["call"] == "bash":
                    heads[(phase, command_head(t["target"]))] += 1
                if t["call"] == "edit" and "edit" not in t["offered"]:
                    violations[(phase, "edit_without_tool")] += 1
            elif t["kind"] == "result" and t["refused"]:
                violations[(phase, "refused_result")] += 1
                nxt = next((x for x in r["turns"][i + 1:] if x["kind"] == "act"), None)
                after[nxt["call"] if nxt else "end_of_episode"] += 1

    print("== phase turns and whether edit was offered in the request ==")
    for p in sorted(phases):
        print(f"  {p:<8} turns={phases[p]:<4} edit_offered={offered_by_phase[(p, 'edit_offered')]:<4} bash_only={offered_by_phase[(p, 'bash_only')]}")
    free_calls = {k[1]: v for k, v in calls.items() if k[0] == "free"}
    if free_calls:
        print(f"  {'free':<8} turns={sum(free_calls.values()):<4} (no phase injected) {free_calls}")
    print("\n== calls made, by phase ==")
    for p in sorted({k[0] for k in calls}):
        c = {k[1]: v for k, v in calls.items() if k[0] == p}
        if c:
            print(f"  {p:<8} {c}")
    print("\n== bash commands by phase (test/write/read) ==")
    for p in sorted({k[0] for k in heads}):
        c = {k[1]: v for k, v in heads.items() if k[0] == p}
        if c:
            print(f"  {p}:")
            for head, n in sorted(c.items(), key=lambda kv: -kv[1])[:6]:
                print(f"      {n:>3}x {head[:70]}")
    print(f"\n== refusals / violations: {dict(violations)}")
    print(f"== what followed a refusal: {dict(after)}")
    print(f"== episodes parsed: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())