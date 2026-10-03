# Phase 3.6 -- the behaviour H_D actually changes

`tools/swe_lab/behavior.py` reduces each recorded episode to a behaviour profile:
the sequence of action kinds (inspect / test / write / other) over the canonical
branch, plus where the first write and the first test land.

Source: 96 episodes, tier3 + tier5, H_A (3 runs) and H_D (3 runs), same model.

    tier                   harn solv     n  edit@  test@ insp1st tstAft repair   noWr calls
    tier3-regression-trap  H_A  yes      5    1.8      -   100%     0%     0%     0%   4.8
    tier3-regression-trap  H_A  no      19    2.4    1.5    95%     0%    74%     5%   4.3
    tier3-regression-trap  H_D  yes     14    2.6    6.1   100%    64%     0%     0%   6.5
    tier3-regression-trap  H_D  no      10    1.5    2.0   100%    10%    10%     0%   4.6
    tier5-multi-constraint H_A  yes      1    2.0    1.0   100%     0%   100%     0%   5.0
    tier5-multi-constraint H_A  no      23    2.9    1.7    48%     0%    48%    52%   4.7
    tier5-multi-constraint H_D  yes      4    1.8    4.2   100%   100%    50%     0%   5.8
    tier5-multi-constraint H_D  no      20    2.6    3.3    55%     5%     5%    45%   4.2

## The finding

**On tier3, H_D's gain is the verify turn and nothing else.** Solved H_D episodes run a
test after the edit 64% of the time; solved H_A episodes never do (0%, n=5). Mean first
test sits at action 6.1 under H_D versus never under H_A. The harness is not making the
model a better code reader -- `inspect_before_edit` is ~100% under both. It is making
the model close the loop, and closing the loop is what tier3 punishes: tier3's defect is
a change that looks correct and breaks a previously passing test, so an unverified edit
scores the same as a wrong one.

That also explains the negative result that was harder to read: H_A's *unsolved* tier3
episodes show `repair_after_failed_test` at 74%, higher than its solved episodes (0%).
Those are not episodes that failed to verify -- they ran the suite early, saw failures,
patched again, and spent the 4-turn budget oscillating. Repair behaviour is not the
missing ingredient; sequencing is. A model that tests first and repairs has burned its
budget before it has located the defect; a model that edits and then tests has one
verification left inside the cap.

## tier5 is the opposite failure

tier5's unsolved episodes are dominated by `no_write` -- 52% under H_A, 45% under H_D --
and by half of them never running an inspect before their first write. The model spends
the budget orienting in a fixture with more constraints than it can hold, and leaves
without having changed anything. Here the harness's read-only recon turn is the right
idea, and it is why H_D's tier5 tool-mix shows fewer writes than H_A, but the gain is
small (4% -> 17%) because the binding constraint is exploration budget, not sequencing.

## What this closes

H_D is not "a better planner" and not "a better coder". On the tier where it wins, it
converts an *unverified* edit into a *verified* one, and the win tracks that single
behavioural difference (0% -> 64% test-after-edit) far more tightly than it tracks
inspect-before-edit (unchanged at ~100%) or repair-after-test (unchanged at 0%).

This is also why H_F did not reproduce the effect. H_F gated turn 1 to be read-only but
supplied no verify instruction, and its profile has no reason to add a trailing test --
consistent with its measured tier3 rate of 21%, identical to H_A.

## Caveat

Each tier is ONE task (`ladder.build_tiers()` returns a single fixture per tier), so
these 24 episodes per cell are samples of one task, not 24 tasks. The behavioural
contrast is within-task and within-model; it does not establish that the same sequence
shapes success on other regression-trap repositories.