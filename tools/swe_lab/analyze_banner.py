"""Phase 7 banner decomposition: the banner arms on trajectory, not just on solves.

The control holds dots3, the wide 20-instance set, T=6 and edit-always-available
(SWE_LAB_GATE=0) fixed, and varies only the per-turn control-plane text the runtime
injects before each model completion:

  H_A        no banner                                  (stock free loop, harness bash)
  H_P        full phase instruction at each phase start (recorded reference arm)
  H_ONCE     full phase instruction on turn 1 only      (is repetition necessary?)
  H_NEUTRAL  "Turn k of T." every turn                  (is a status anchor enough?)
  H_ACTION   "Phase: X. Goal: ..." every turn           (action-oriented content)
  H_PHASE    full phase instruction every turn          (every-turn reference)

Banner injections are counted straight out of the traces (the injected text is a
user-role message), so the table validates the arms before it reads the behaviour.

Trajectory metrics, per episode:
  first_edit_turn      call index + 1 of the first write
  first_test_turn      call index + 1 of the first test run
  state_changing       calls that are not inspection (write or test)
  state_changing_ratio (write + test) / calls
  inspect_run_max      longest block of consecutive inspection calls
  inspect_runs         number of maximal inspection blocks
  inspect_to_edit_lag  calls from the last inspection before the first edit to that edit
  edit_after_failed_test  an edit within one call of a test run that failed
  no_write             the episode never wrote

usage: uv run python tools/swe_lab/analyze_banner.py
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path
from statistics import median

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "swe_lab"))

from behavior_real import real_call_kind, solved  # noqa: E402
from frontier import read_traces  # noqa: E402

ARMS = {
    "H_A": ["outputs/rl-6c-hA-T6"],
    "H_P": ["outputs/rl-6c-hP-T6"],
    "H_ONCE": ["outputs/rl-7-hOnce"],
    "H_NEUTRAL": ["outputs/rl-7-hNeutral"],
    "H_ACTION": ["outputs/rl-7-hAction"],
    "H_PHASE": ["outputs/rl-7-hPhase"],
    "H_SYS": ["outputs/rl-7-hSys"],
    "H_REPLAY": ["outputs/rl-8-hReplay"],
}

PHASE_RE = "PHASE "
NEUTRAL_RE = "Turn "
ACTION_RE = "Phase: "


def banner_injections(trace: dict) -> dict:
    """How many control-plane user messages the episode actually received.

    Verifiers re-roots a branch when the advertised tool set changes, duplicating
    the prefix (frontier.tool_calls documents this). A duplicated banner lands
    immediately after the one it duplicates, with only assistant nodes in between,
    and turn_no is monotonic in the program, so every repeated banner text is a
    re-rooting artefact. Consecutive repeats are collapsed before counting; a
    legitimately repeated goal line (H_ACTION re-injects the same goal each turn
    of a phase) is kept because it is the signal.
    """
    counts = {"phase": 0, "neutral": 0, "action": 0, "total": 0, "raw": 0, "system": 0}
    prev = None
    for node in trace.get("nodes") or []:
        message = node.get("message") or {}
        role = message.get("role")
        if role not in ("user", "system"):
            continue
        text = (message.get("content") or "")
        if text.startswith(NEUTRAL_RE) and "of" in text:
            kind = "neutral"
        elif PHASE_RE in text:
            kind = "phase"
        elif text.startswith(ACTION_RE):
            kind = "action"
        else:
            continue  # task prompt, the base system prompt, other
        counts["raw"] += 1
        if role == "system":
            counts["system"] += 1
        if text == prev:
            continue
        prev = text
        counts[kind] += 1
        counts["total"] += 1
    return counts


def calls_with_results(trace: dict) -> list[dict]:
    """Tool calls paired with their result text.

    Tool-result nodes are recorded as not sampled (the recorder keeps only the
    assistant nodes in the sampled path), so they must be collected independently
    of the sampled filter that tool_calls() applies.
    """
    results = {}
    for node in trace.get("nodes") or []:
        message = node.get("message") or {}
        if message.get("role") == "tool":
            results[message.get("tool_call_id")] = message.get("content") or ""
    calls = []
    for node in trace.get("nodes") or []:
        if not node.get("sampled"):
            continue
        for call in (node.get("message") or {}).get("tool_calls") or []:
            cid = call.get("id") or (call.get("function") or {}).get("id")
            calls.append({"name": call.get("name") or (call.get("function") or {}).get("name"),
                          "arguments": call.get("arguments"),
                          "result": results.get(cid, "")})
    return calls


FAIL_MARKERS = ("FAILED", "AssertionError", "Traceback", "error:", "FAIL:")


def test_failed(result: str) -> bool:
    return any(marker in (result or "") for marker in FAIL_MARKERS)


def trajectory(trace: dict) -> dict:
    calls = calls_with_results(trace)
    kinds = [real_call_kind(c) for c in calls]
    results = [c.get("result") or "" for c in calls]
    n = len(kinds)
    state_changing = sum(1 for k in kinds if k != "inspect" and k != "other")

    blocks, cur = 0, 0
    inspect_run_max = 0
    for k in kinds:
        if k == "inspect":
            cur += 1
            inspect_run_max = max(inspect_run_max, cur)
        else:
            if cur:
                blocks += 1
            cur = 0
    if cur:
        blocks += 1

    first_write = next((i for i, k in enumerate(kinds) if k == "write"), None)
    first_test = next((i for i, k in enumerate(kinds) if k == "test"), None)
    inspect_to_edit = None
    if first_write is not None:
        before = [i for i in range(first_write) if kinds[i] == "inspect"]
        if before:
            inspect_to_edit = first_write - max(before)

    edit_after_failed = False
    for i, k in enumerate(kinds):
        if k == "test" and test_failed(results[i]):
            for j in (i + 1, i + 2):
                if j < n and kinds[j] == "write":
                    edit_after_failed = True
    return {
        "n_calls": n,
        "solved": solved(trace),
        "no_write": first_write is None,
        "first_edit_turn": None if first_write is None else first_write + 1,
        "first_test_turn": None if first_test is None else first_test + 1,
        "state_changing": state_changing,
        "state_changing_ratio": state_changing / n if n else 0.0,
        "inspect_run_max": inspect_run_max,
        "inspect_runs": blocks,
        "inspect_to_edit_lag": inspect_to_edit,
        "edit_after_failed_test": edit_after_failed,
        "test_ep": first_test is not None,
    }


def summarize(arm: str, dirs: list[str]) -> dict:
    rows = []
    for d in dirs:
        p = REPO / d
        if p.exists():
            rows.extend(read_traces(p))
    if not rows:
        return {"n": 0}
    trajs = [trajectory(t) for t in rows]
    inj = [banner_injections(t) for t in rows]
    edit_eps = [t for t in trajs if t["first_edit_turn"] is not None]
    test_eps = [t for t in trajs if t["test_ep"]]
    def med(values):
        return median([v for v in values if v is not None]) if any(v is not None for v in values) else None
    out = {
        "n": len(rows),
        "solve": sum(t["solved"] for t in trajs) / len(trajs),
        "edit_eps": len(edit_eps) / len(trajs),
        "test_eps": len(test_eps) / len(trajs),
        "first_edit_turn": med([t["first_edit_turn"] for t in trajs]),
        "first_test_turn": med([t["first_test_turn"] for t in trajs]),
        "state_changing_ratio": statistics.mean(t["state_changing_ratio"] for t in trajs),
        "inspect_run_max": med([t["inspect_run_max"] for t in trajs]),
        "inspect_runs": statistics.mean(t["inspect_runs"] for t in trajs),
        "inspect_to_edit_lag": med([t["inspect_to_edit_lag"] for t in trajs]),
        "edit_after_failed_test": sum(t["edit_after_failed_test"] for t in trajs) / len(trajs),
        "n_calls": statistics.mean(t["n_calls"] for t in trajs),
        "inj_phase": statistics.mean(i["phase"] for i in inj),
        "inj_neutral": statistics.mean(i["neutral"] for i in inj),
        "inj_action": statistics.mean(i["action"] for i in inj),
        "inj_total": statistics.mean(i["phase"] + i["neutral"] + i["action"] for i in inj),
        "inj_raw": statistics.mean(i["raw"] for i in inj),
        "inj_system": statistics.mean(i["system"] for i in inj),
    }
    return out


def fmt(v, nd=2):
    if v is None:
        return "   -"
    if isinstance(v, float):
        return ("%." + str(nd) + "f") % v
    return str(v)


def main() -> int:
    print("== Phase 7 banner decomposition (dots3, wide 20, T=6, edit always available) ==")
    header = (f"{'arm':<11} {'n':>3} {'solve':>6} {'edit%':>6} {'first_edit':>10} {'first_test':>10} "
              f"{'inj_raw':>7} {'inj_arm':>7} {'state_chg':>9} {'n_calls':>8} "
              f"{'inspect_run_max':>15} {'inspect_runs':>12} {'lag_inspect->edit':>17} {'edit_after_fail':>15}")
    print(header)
    for arm, dirs in ARMS.items():
        r = summarize(arm, dirs)
        if not r.get("n"):
            print(f"{arm:<11} {0:>3}  (not run)")
            continue
        print(f"{arm:<11} {r['n']:>3} {r['solve']:>6.2f} {r['edit_eps']*100:>6.0f} "
              f"{fmt(r['first_edit_turn'], 1):>10} {fmt(r['first_test_turn'], 1):>10} "
              f"{r['inj_raw']:>7.2f} {r['inj_total']:>7.2f} {r['state_changing_ratio']:>9.2f} {r['n_calls']:>8.1f} "
              f"{fmt(r['inspect_run_max'], 1):>15} {r['inspect_runs']:>12.2f} "
              f"{fmt(r['inspect_to_edit_lag'], 1):>17} {r['edit_after_failed_test']:>15.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
