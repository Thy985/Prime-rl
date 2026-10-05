# Budget sweep: the harness gap lives in the low-budget regime

The H_A / H_A' / H_D triangle shows the +32 points are runtime-enforced structure,
not instruction text. That still leaves the question the user framed: is H_D a
unit-budget efficiency (it schedules the same few turns better) or a structural
improvement that pays at every budget? This run sweeps max_turns over
{2, 4, 6, 8} x {H_A, H_D}, same 5 gated django instances, same episode grid
(16 per cell), same model (dots3-note-prev), -c 1.

## Solve rates

| max_turns | H_A      | H_D      | gap (D - A) |
|-----------|----------|----------|-------------|
| 2         | 0/16 = 0% | 1/16 = 6% | +6 |
| 4         | 2/16 = 12% | 7/16 = 44% | +32 |
| 6         | 5/16 = 31% | 8/16 = 50% | +19 |
| 8         | 8/16 = 50% | 7/16 = 44% | -6 |

## Reading the curve

**Both arms are monotonically increasing in budget.** H_A: 0 -> 12 -> 31 -> 50.
H_D: 6 -> 44 -> 50 -> 44. Neither arm saturates at T=8, so the measurement floor
is not the problem.

**The gap is not flat; it peaks at T=4 and vanishes by T=8.** The user's predicted
shape -- "4-turn huge gap, 8-turn gap vanishes" -- holds, and it actually
crosses over at T=8 (H_A 50% vs H_D 44%, within noise at n=16 per cell but no
longer a positive D effect). H_D's value is unit-budget efficiency: at a scarce
budget its allocation forces an early edit instead of letting the free loop burn
the whole budget on `find .` and `cat -n`. At a generous budget the free loop
reaches the same behavior on its own (below), and the fixed 1-recon + 2-execute
allocation starts to cost turns: the extra budget goes to feedback turns, where
the model spends them re-reading files and pip-installing instead of editing.

**Why H_A catches up: the verify behavior finally emerges on its own.** The
behaviour profile's test_after_edit is 0% in every arm at T=4 (the "told to
verify, never verifies" finding). At T=8 it is 50% for H_A's solved episodes and
71% for H_D's solved episodes; the gating probe counts 10 test runs in H_D's
feedback phase at T=8 vs 0 at T=4. Given enough turns, this model does adopt
inspect -> edit -> test -> repair on its own -- the exact script H_D's prompts
state but that the model ignores when turns are too scarce to both act and check.

**No test run and no edit-tool absence changed at any budget; only their timing
did.** The recon phase never offers edit at any T (affordance removal holds), and
the bash write refusal string appears 0 times at every T (the model never tries
sed/patch/> in recon). What scales with budget is the execute/feedback phases:
more turns there -> more edits and, from T=6 up, actual test runs.

## What this does to the program claim

The harness gain is real but budget-shaped: H_D buys roughly +30 points at the
4-turn operating point, +20 at 6, and nothing (or slightly negative) at 8. For
the Phase 4 transfer question this sharpens the conclusion rather than changing
it: the mechanism being transferred would have to be "edit before you run out of
turns", a scheduling property that only matters when turns ARE scarce -- exactly
the property a 0.6B student that never calls a tool cannot be distilled into.
The gain is not a better agent; it is a better use of a small budget.

## Reproduce

    for T in 2 6 8; do
      for ARM in hA hD; do
        sed "s/^env.agent.max_turns = 4/env.agent.max_turns = ${T}/" \
          tools/swe_lab/eval_real_${ARM}.toml > /tmp/sweep/eval_${ARM}_T${T}.toml
        bash /tmp/run_swe_eval.sh /tmp/sweep/eval_${ARM}_T${T}.toml \
          --run.name rl-${ARM}-T${T} -c 1 --clean
        bash /tmp/run_swe_eval.sh /tmp/sweep/eval_${ARM}_T${T}.toml \
          --run.name rl-${ARM}-T${T}-topup -c 1 --clean -n 2 -r 3
      done
    done

    uv run python tools/swe_lab/behavior_real.py \
      --pattern "H_A_T2=outputs/rl-hA-T2" ... "H_D_T8=outputs/rl-hD-T8-topup"
    uv run python tools/swe_lab/gating.py outputs/rl-hD-T8 outputs/rl-hD-T8-topup