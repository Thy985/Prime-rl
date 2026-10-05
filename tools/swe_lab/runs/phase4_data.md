# Phase 4 (SFT) — protocol-invariant training data

Built from the recorded H_A, H_D and H_F runs via `training_view.py`.

## Source and size

- 360 episodes: 3 x H_A (swe-lab-budget-hA{,2,3}) + 3 x H_D (swe-lab-budget-hD{1,3,4}) + 3 x H_F (swe-lab-budget-hF{1,2,3}), each 40 tasks.
- Kept (solved): 214. Dropped (unsolved): 146.
- Kept per tier: tier1=72, tier2=72, tier3=24, tier4=41, tier5=5.

## Why the canonical branch matters here

H_D and H_F both carry a read-only recon phase that drops the `edit` tool on turn 1. The graph recorder keys a root system node on `(parent, tools_hash, message_hash)`; when the next phase adds `edit` back the tools_hash changes, the root match fails, and the turn-1 prefix is re-rooted as a sibling branch. The node-level read would silently double-train that prefix. The branch read follows the last node's physical parent chain and skips the sibling.

## What is trained

Assistant turns only: content + tool_calls. System, user, and tool-result turns carry context, not loss. The model learns the tool-usage pattern the harness shaped; the protocol text is not in the target (H_F episodes have no protocol text at all; H_D episodes carry the plan/execute/verify instructions in user turns, which are context).

## Rebuild command

    uv run python tools/swe_lab/training_view.py \
      --run 'outputs/swe-lab-budget-hA*' 'outputs/swe-lab-budget-hD[134]*' 'outputs/swe-lab-budget-hF*' \
      --out outputs/swe_runs/training_view.jsonl \
      --manifest outputs/swe_runs/training_view.manifest.json

## The 8-gate acceptance

Run on every Phase 4 build; the gate must pass before SFT:

1. trajectory complete (all model turns present on the branch)
2. conversation order (parent chain is strictly root to leaf)
3. tool calls/results not lost (every assistant tool_call has its tool result immediately after on the branch)
4. final state (the last node is a leaf with no children)
5. reward replayable (the recorded reward is recomputable from the final tree)
6. provenance (each example carries run/episode_id/tier/reward)
7. no duplicate-root double-counting (the branch contains each (parent, message) pair at most once)
8. mask is exactly the assistant turns; tool results are context

The 5 acceptance checks training_view.py prints today are a subset: assistant-only mask, tool-as-context, provenance, manifest record, branch integrity. Gates 1, 3, and 5 need to be wired in before a real SFT run is pointed at this view.