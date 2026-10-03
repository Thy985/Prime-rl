# Phase 4A / 4B audit — three training views, contamination-free

## Data construction

Three canonical-branch views, each filtered to reward == 1.0:

| View | Episodes | Kept | Tiers (1/2/3/4/5) | PHASE msgs stripped |
| --- | --- | --- | --- | --- |
| D_A   | 120 (3 H_A runs)  | 66  | 24/24/5/12/1  | 0 |
| D_D   | 120 (3 H_D runs)  | 81  | 24/24/14/15/4 | 243 |
| D_AD  | 240 (union)       | 147 | 48/48/19/27/5 | 243 |

Per-run provenance (D_A): swe-lab-budget-hA=24, hA2=20, hA3=22.
Per-run provenance (D_D): swe-lab-budget-hD1=26, hD3=26, hD4=29.

## Contamination check

H_D episodes carry three PHASE user messages per episode
(PLAN, EXECUTE, FEEDBACK), which the staged harness appends between calls.
243 PHASE messages were stripped from D_D (3 x 81 = 243, exact match);
zero remain in D_AD. D_A carries none.

The strip is a documented transformation step in training_view.py and is
recorded per source in the manifest (phase_messages_stripped).

## Tier distribution

The views are the natural solve-rate distribution, not stratified. tier1/tier2
are dominated (24/24 each in every view); tier5 is the tail (1/4/5 examples).
tier3 is the interesting stratum: D_A=5, D_D=14, D_AD=19.

## Branch integrity

All three views pass the 5 acceptance gates: assistant-only mask,
tool-as-context, provenance, manifest record, canonical branch integrity.
The 8-gate acceptance (trajectory complete, conversation order, tool pairs,
final leaf, reward replayable, provenance, no duplicate-root, mask) is
documented in phase4_data.md; the 5 checks training_view.py prints today are
a subset. Gates 1 (trajectory complete), 3 (tool pairs), 5 (reward
replayable) need to be wired in before pointing a real SFT run at this view.

## Next

Phase 4C: SFT three policies pi_A, pi_D, pi_AD on these three views.
Phase 4D: protocol-invariant H_A eval sweep (Base / pi_A / pi_D / pi_AD).