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
import re
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

TEST_RE = re.compile(r"\bpytest\b|\bunittest\b")
# A `>` counts as a tree write only when it redirects to a real path: `2>&1`
# and `>/dev/null` suppress or discard output, they do not mutate the tree.
WRITE_RE = re.compile(r">(?!&)\s*(?!/dev/null\b)\S|\bsed -i\b|\btee\b|<<\s*['\"]?EOF|\bpatch\b|\bapply_patch\b")
INSPECT_RE = re.compile(r"^\s*(cat|ls|head|tail|grep|find|sed|wc|file|awk|less|diff)\b")
WRITE_TOOLS = ("edit", "write", "apply_patch", "str_replace", "create")


def kind_of(command: str) -> str:
    """Classify a bash command by what it is FOR, not by which binary it calls."""
    text = (command or "").strip()
    if TEST_RE.search(text):
        return "test"
    if WRITE_RE.search(text):
        return "write"
    if INSPECT_RE.match(text):
        return "inspect"
    return "other"


def action_kind(call: dict) -> str:
    """Classify a TOOL CALL, which is not always a bash command.

    A dedicated edit/write tool changes a file with no shell command at all, so
    classifying only bash text reports every edit-tool repair as "never wrote
    anything" -- a measurement bug that would invert a success/failure finding.
    """
    name = (call.get("name") or "").lower()
    if any(marker in name for marker in WRITE_TOOLS):
        return "write"
    if name != "bash":
        return "other"
    arguments = call.get("arguments") or ""
    if arguments.strip().startswith("{"):
        try:
            return kind_of(json.loads(arguments).get("command", "") or "")
        except json.JSONDecodeError:
            return "other"
    return kind_of(arguments)


def all_runs(pattern: str) -> list[Path]:
    """Every run matching a glob, newest last.

    WSL's native ``Path.glob`` silently drops matches when the pattern contains a
    glob class after the separator (e.g. ``swe-lab-hD[134]``); a shell-style
    glob through the shell's own ``glob`` function resolves them.
    """
    import glob as _glob

    def _candidates(base: Path, pat: str) -> list[Path]:
        if base.is_dir():
            found = sorted(base.glob(pat))
        else:
            found = [Path(c) for c in _glob.glob(str(base / pat))]
        return found

    if "/" not in pattern and pattern in ("", "."):
        found = _candidates(REPO, pattern)
    elif "*" in pattern or "[" in pattern:
        found = _candidates(REPO, pattern)
    else:
        found = _candidates(REPO, pattern) if REPO.exists() else []
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
    """The tier id, independent of task mode (patch names carry a mode suffix)."""
    data = (trace.get("task") or {}).get("data") or {}
    return data.get("tier") or data.get("name") or "unknown"


def trace_mode(trace: dict) -> str:
    """`reply` scores an answer; `patch` scored the runtime tree at rollout time."""
    data = (trace.get("task") or {}).get("data") or {}
    return data.get("mode") or "reply"


def tool_calls(trace: dict) -> list[dict]:
    """Tool calls as recorded on assistant message nodes (they are not on ModelCall).

    Only `sampled` nodes count. A non-sampled node repeats a message the graph already
    holds. The re-rooting this triggers has a precise cause, found in
    verifiers.v1.graph: a root node is keyed by (parent, tools_hash, message_hash),
    so when the advertised tool set changes between turns -- a read-only recon turn
    advertises bash only, the next turn adds edit -- the recorder cannot match the
    existing root and re-roots, duplicating the prefix as a parallel branch.
    H_A and H_E keep the tool set constant and never re-root; H_D and H_F always do.
    The duplication is harmless here (sampled=True appears once per model call) but
    would silently double-count tool calls and, on a write-refused recon turn,
    report writes that never ran.
    """
    calls = []
    for node in trace.get("nodes") or []:
        if not node.get("sampled"):
            continue
        message = node.get("message") or {}
        for call in message.get("tool_calls") or []:
            calls.append(
                {
                    "name": call.get("name") or (call.get("function") or {}).get("name"),
                    "arguments": call.get("arguments"),
                }
            )
    return calls


def advertised_tools(trace: dict) -> list[str]:
    return [tool.get("name") for tool in (trace.get("tools") or []) if tool.get("name")]


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
    """Keyed by tier so reply-mode and patch-mode runs resolve to the same task."""
    return {task.data.tier: task for task in SweLabTaskset(SweLabConfig(id="swe-lab")).load()}


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
            mode = trace_mode(trace)
            # An empty reply only invalidates a REPLY-mode episode. In patch mode the
            # reward came from the runtime tree, so a rollout the budget stopped
            # mid-tool-call is a legitimate episode that simply did not fix anything --
            # counting it as invalid silently deletes the failures a budget creates.
            if trace.get("stop_condition") in INVALID_STOPS or recorded is None:
                invalid += 1
                continue
            if mode == "reply" and not reply.strip():
                invalid += 1
                continue
            calls = tool_calls(trace)
            writes = sum(1 for call in calls if action_kind(call) == "write")
            if trace_mode(trace) == "patch":
                # A patch reward was computed from the runtime tree during the rollout
                # and cannot be re-derived offline (it needs a live runtime), so the
                # recorded value is authoritative here.
                verdict = None
                reward = recorded
                # "Ended without writing anything" is its own outcome, not a bad
                # patch: the two call for different harness interventions.
                if reward >= 1.0:
                    failure = None
                else:
                    failure = "no_write" if writes == 0 else "unsolved"
            else:
                task = tasks.get(tier)
                verdict = task._score_reply(reply) if task else None
                reward = terrain.REWARDS["target_fix_fraction"](verdict) if verdict else 0.0
                failure = None if reward >= 1.0 else classify(reply, files, verdict, reward)
            rows.append(
                {
                    "reward": reward,
                    "recorded": recorded,
                    "failure": failure,
                    "writes": writes,
                    "mode": trace_mode(trace),
                    "tool_calls": len(calls),
                    "tool_names": [call["name"] for call in calls],
                }
            )
        solved = sum(1 for row in rows if row["reward"] >= 1.0)
        mixture = defaultdict(int)
        for row in rows:
            if row["failure"]:
                mixture[row["failure"]] += 1
        tool_mix = defaultdict(int)
        for row in rows:
            for name in row["tool_names"]:
                tool_mix[name] += 1
        summary[tier] = {
            "n": len(rows) + invalid,
            "n_valid": len(rows),
            "n_invalid": invalid,
            "solved": solved,
            "mode": rows[0]["mode"] if rows else "reply",
            "mean_tool_calls": (sum(row["tool_calls"] for row in rows) / len(rows)) if rows else 0.0,
            "no_write": sum(1 for row in rows if row["writes"] == 0 and row["reward"] < 1.0),
            "mean_writes": (sum(row["writes"] for row in rows) / len(rows)) if rows else 0.0,
            "tool_mix": dict(tool_mix),
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
    print("%-24s %3s %6s %6s %7s %8s %7s %6s %6s  %s"
          % ("tier", "n", "valid", "error", "solve", "score", "tools", "writes", "no-write",
             "failure mixture / tool mix"))
    for tier in sorted(summary):
        row = summary[tier]
        detail = ", ".join("%s=%d" % item for item in sorted(row["failures"].items()))
        mix = ", ".join("%s:%d" % item for item in sorted(row["tool_mix"].items()))
        print(
            "%-24s %3d %6d %6d %7s %8.3f %7.1f %6.1f %6d  %s"
            % (
                tier,
                row["n"],
                row["n_valid"],
                row["n_invalid"],
                "%d/%d" % (row["solved"], row["n_valid"]) if row["n_valid"] else "n/a",
                row["mean_rescored"] or 0.0,
                row["mean_tool_calls"],
                row["mean_writes"],
                row["no_write"],
                (detail or "-") + (" | " + mix if mix else ""),
            )
        )
    if any(row["mode"] == "patch" for row in summary.values()):
        print("\nmode: patch -- scores are the recorded runtime verdicts, not re-derived")

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