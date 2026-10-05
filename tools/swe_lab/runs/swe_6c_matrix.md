# Phase 6C: the budget matrix -- harness value across remaining budget

Phase 6A isolated the prompt and the gate at T=4 (a floor regime) and found the
decomposition unmeasurable there. Phase 6B built a deterministic adaptive
scheduler (H_ADAPT). Phase 6C runs both against the free agent (H_A) and the
fixed harness (H_D) across four budgets to answer the Phase-6 question: how
should a runtime allocate action capability against remaining budget? The
schedules:

- H_A: free bash+edit every turn, no phase structure.
- H_D: fixed recon(1) -> execute(2) -> feedback(rest), edit gated out of recon.
- H_ADAPT: recon [bash] until the inspection pattern repeats twice or the
  budget is exhausted; then execute [bash, edit]; a bash-only verify turn only
  on the last turn when an edit exists but no test ever ran. No phase prompt.

All on the 20-instance wide set (8 django + 12 sympy), 1 episode/instance,
dots3-note-prev, `-c 1`. T=4 reuses the Phase-6A runs (H_A 20, H_D 40, H_ADAPT
20); T=2/6/8 are fresh `-n 20 -r 1` runs. Solve = resolve reward 1.0; edit =
real `edit` tool calls; test = real suite invocation.

## The matrix

| harness   | T=2 sol/ed/t  | T=4 sol/ed/t  | T=6 sol/ed/t  | T=8 sol/ed/t  |
|-----------|---------------|---------------|---------------|---------------|
| H_A       | 0/0/0         | 0/0/0 (n=20)  | 0/2/0         | 3/4/2         |
| H_P       | -             | 3/5/3 (n=40)  | 5/7/1         | -             |
| H_G       | -             | 2/2/0 (n=40)  | 1/3/0         | -             |
| H_D       | 0/0/0         | 2/4/1 (n=40)  | 5/6/4         | 2/6/2         |
| H_ADAPT   | 0/0/0         | 0/1/0 (n=20)  | 1/2/0         | 3/4/2         |

(sol/edit/test out of 20 unless the n is noted; T=4 H_D/H_G/H_P are pooled to 40
from the 6A repeats. H_P/H_G were run at T=6 only, as the banner-vs-gate
decomposition at the budget where the effect lives.)

H_D's per-budget solves: T=4 5%, T=6 25%, T=8 10%. H_A's: T=4-6 0%, T=8 15%.
H_ADAPT's: T=4-6 0-5%, T=8 15%. T=2 is a clean 0% for all three.

## The T=6 decomposition: the banner is the mechanism, the gate is not

The extension arms isolate the two signals where the effect lives (T=6, the
budget at which H_D peaks):

| arm    | solve | edits | tests | mechanism present          |
|--------|-------|-------|-------|---------------------------|
| H_A    | 0/20  | 2/20  | 0/20  | none                      |
| H_P    | 5/20  | 7/20  | 1/20  | per-turn banner only      |
| H_D    | 5/20  | 6/20  | 4/20  | banner + silent gate      |
| H_G    | 1/20  | 3/20  | 0/20  | silent gate only          |
| H_ADAPT| 1/20  | 2/20  | 0/20  | adaptive scheduler only   |

H_P -- the phase banner with the edit tool present every turn, no gating --
reproduces H_D's solve rate exactly (5/20 = 25%) and beats H_D on edits
(7 vs 6). H_G -- the same gating as H_D with the banner neutralised -- lands at
the free-agent floor (1/20, 3 edits). The Phase-6A question ("does silent gating
push the first edit earlier? if so, and the banner cannot, affordance scheduling
is established") is answered in the negative: **the banner does it, the silent
gate does not.** Dots3 does not notice the tool list changing; it does notice the
per-turn phase announcement ("PHASE 2 of 3 -- EXECUTE ... apply the repair
now"). The gate's only measurable extra over the banner is test runs (H_D 4 vs
H_P 1) -- the feedback phase prompt does drive suite runs -- but that does not
translate into more solves at T=6.

This refines Phase 5's "runtime-enforced structure > static instruction": the
triangle proved a *static* paragraph is inert, and the pilot attributed H_D's
gain to the enforcement. The 2x2 shows the effective ingredient is the *per-turn*
announcement, which the pilot's design never isolated: H_D's effect is the
banner's, and the enforcement (edit removal) adds nothing on the wide set. The
causal chain is announcement -> the model edits at the announced turn -> a
fraction of those edits land. The affordance itself (which tools exist) is not
the lever dots3 responds to.

The H_ADAPT comparison is then mostly the same negative: an adaptive scheduler
with no banner is a silent gate with worse timing (recon-2 tax), so it sits at
the H_G/H_A floor until T=8, where the free budget carries it to 15% alongside
H_A.

## Three findings

**1. The fixed harness is budget-dependent: a mid-budget peak.** H_D's value
over H_A is +5pt at T=4 (noise), +25pt at T=6, and -5pt at T=8 (H_A pulls ahead).
The harness only helps where the free agent cannot yet reach an edit on its own:
on the wide set that band is roughly T=4 to T=6. Below it nothing edits (floor);
above it the free budget is large enough that the model edits and solves on its
own (H_A 4/20 edits and 3/20 solves at T=8), and the harness's structure stops
being the binding constraint. This sharpens the Phase-5 story -- the harness is
not "always good", it is "good exactly where the model would otherwise stall in
inspection."

**2. The fixed harness over-edits at high budget.** H_D@T8 made 6 edits in 20
episodes but only 2 solved (33% edit->solve), against H_A@T8's 4 edits and 3
solves (75%) and H_ADAPT@T8's 4 edits and 3 solves (75%). H_D's longer feedback
phase (1 recon + 2 execute + 5 feedback at T=8) gives the model many edit-capable
turns and it re-edits, sometimes breaking a working fix. The inverted U (25% at
T=6 -> 10% at T=8) is not significant at n=20 (+-11pt) but the edit-conversion
rate points at the mechanism: more edit affordance past the point of usefulness
hurts.

**3. The adaptive v1 scheduler does not beat the fixed schedule.** H_ADAPT never
exceeds H_D at any budget (0% vs 5% at T=4, 5% vs 25% at T=6, 15% vs 10% at T=8
-- only the last is in H_ADAPT's favour and within noise). Its recon-minimum of
two turns (rule A: same-inspect-twice; rule B: budget-remaining <= 2) makes the
edit tool first available at turn 3, against H_D's turn 2. At T=4/6 that is one
fewer execute turn where dots3, which inspects by default, gets to edit -- and
dots3 rarely reaches an edit in the remaining turns. 58 of 60 H_ADAPT episodes
across T=2/6/8 had the shape `[RECON x2, EXECUTE]` and 18 of 20 at T=6 were six
inspects and no edit. The verify rule (rule C: bash-only last turn when edit-seen
+ not-tested + budget<=1) never fired -- whenever the model edited it also ran
the suite within EXECUTE on its own. Rule C is correct but the operating point
does not exercise it.

## Against the expected matrix

| budget | expected                    | actual (H_A / H_D / H_ADAPT)        | verdict |
|--------|-----------------------------|-------------------------------------|---------|
| T=2    | H_A < H_D < H_ADAPT         | 0 / 0 / 0                           | all floor; ordering unmeasurable |
| T=4    | H_A << H_D ~= H_ADAPT       | 0 / 5% / 0%                         | direction ok; floor |
| T=6    | H_A ~= H_D < H_ADAPT        | 0% / 25% / 5%                       | inverted -- H_D dominates, H_ADAPT worst |
| T=8    | H_A >= H_D < H_ADAPT        | 15% / 10% / 15%                     | H_A>=H_D holds; H_ADAPT ties H_A, not ahead |

The expectations were explicitly a guess. The data corrects two of them: the
T=6 row inverts (the fixed schedule wins, the adaptive one loses), and the T=8
"H_ADAPT pulls ahead" does not happen (H_ADAPT ties the free agent). What the
expectations got right is the shape: H_D's value is largest in the middle of the
budget range and vanishes at both ends.

## What this means for the runtime-allocation question

The Phase-6 thesis was "the runtime should adapt the affordance to the
trajectory and remaining budget." The measurement says: the v1 adaptive rules do
not do this usefully, because their one adaptive lever (delay edit until the
agent has reconned) only ever *postpones* the edit affordance -- it never makes
edit available *earlier* than the fixed schedule does, and dots3's default is to
inspect, so the delay is pure tax. A scheduler that beats H_D must do something
H_D does not: shrink recon below one turn on easy instances, *force* an edit on
a stuck inspecting agent (not merely permit one), or terminate a verifying
episode early once the suite passes. The v1 rules do none of these; the verify
rule, the only genuinely adaptive one, never fires because the model self-tests.

The negative result is itself the answer to the research question at this
operating point: *for a model whose default is inspection, the binding lever is
when edit becomes available, and a fixed early unlock beats an adaptive late
unlock.* The adaptive gain must come from the other end -- forcing action on a
stalled agent, or stopping when done -- not from gating edit later.

## Reproduce

    for T in 2 6 8; do
      for H in hA hD hAdapt; do
        bash /tmp/run_swe_eval.sh tools/swe_lab/eval_real_6c_${H}_T${T}.toml \
          --run.name rl-6c-${H}-T${T} -c 1 --clean -n 20 -r 1
      done
    done
    uv run python tools/swe_lab/analyze_matrix.py
    uv run python tools/swe_lab/adapt_profile.py rl-6c-hAdapt-T6 rl-6c-hAdapt-T8