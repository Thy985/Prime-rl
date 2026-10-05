# Phase 6A: the prompt / gating / interaction factorial

Phase 5 answered "why does the fixed harness work" by isolating the instruction
text (H_A') from the runtime gating (H_D): the gating is the mechanism, the
prose is not. Phase 6A pulls the two levers apart orthogonally and asks whether
the *scheduling of the edit affordance* is doing the work, independent of the
phase prompt that announces it. The 2x2:

| arm    | phase prompts | edit affordance          | edit available in |
|--------|---------------|--------------------------|-------------------|
| H_A    | no            | always present            | every turn         |
| H_P    | yes (H_D's)   | always present            | every turn         |
| H_G    | no            | gated like H_D            | turns 2-4 only     |
| H_D    | yes (H_D's)   | gated like H_D            | turns 2-4 only     |

H_P and H_G each carry exactly one of the two signals: H_P has the phase prose
but no gating (the prompt *claims* edit is unavailable in recon while the edit
tool is in fact listed throughout -- isolating the prompt-claim effect); H_G has
the gating but a neutralised system prompt (no phase protocol) and no per-turn
phase banner -- isolating the affordance-scheduling effect. H_ADAPT, run on the
same grid, is Phase 6B's deterministic adaptive scheduler.

The switches live in `tools/swe_lab_env/swe_lab_planner_program.py`
(`SWE_LAB_PROMPTS`, `SWE_LAB_GATE`) and `swe_lab_planner_executor.py`
(`_phase_protocol` returns "" under `SWE_LAB_PROMPTS=0`). All four arms share
one program; the env vars pick the branch.

## Setup

- task set: the 20-instance wide set (8 django + 12 sympy,
  `tools/swe_lab_env/swe_bench/manifest.json`), 1 episode per instance
- model: dots3-note-prev, endpoint `http://172.20.208.1:20128/v1`, `-c 1`
- budget: T=4 (`max_turns = 4`, `SWE_LAB_BUDGET = 4` for H_ADAPT)
- grid: H_P / H_G / H_D each run twice (rl-2x2-{hP,hG,hD} and rl-2x2-{hP,hG,hD}2)
  and pooled to 40 episodes; H_A and H_ADAPT at 20 (the floor regime made
  further repeats low-value). Same 20 instances x 1 ep throughout.
- metrics: solve rate, no_write (no `write`-kind call at all), real edit-tool
  calls per episode, real test-suite runs per episode, median first-edit turn
  (only over episodes that edited), median first-test turn.

All behavioural metrics use `tools/swe_lab/frontier.py`'s `kind_of`, which this
phase corrected: the old `WRITE_RE` matched `>\s*\S`, so every
`find ... 2>/dev/null` and `grep ... 2>&1` was counted as a tree write. The
fixed `>(?!&)\s*(?!/dev/null\b)\S` matches only real file redirection. This is
an analysis-time classifier; the recorded traces are unchanged. The previously
published `no_write` / `edits/ep` figures (computed by `behavior_real.py`) were
inflated by it -- see the correction appended to `swe_harness_triangle.md`.
Solve rates are unaffected (they come from rewards).

## Results

| arm    | n   | solve   | no_write | edit/ep | test/ep | first_edit (med, eps) | first_test (med, eps) |
|--------|-----|---------|----------|---------|---------|----------------------|----------------------|
| H_A    | 20  | 0/20    | 100%     | 0.00    | 0.00    | - (0)                | - (0)                |
| H_ADAPT| 20  | 0/20    | 95%      | 0.05    | 0.00    | 4 (1)                | - (0)                |
| H_D    | 40  | 2/40    | 90%      | 0.10    | 0.03    | 3.0 (4)              | 3 (1)                |
| H_G    | 40  | 2/40    | 95%      | 0.05    | 0.00    | 3.0 (2)              | - (0)                |
| H_P    | 40  | 3/40    | 88%      | 0.12    | 0.07    | 4 (5)                | 4 (3)                |

Per-instance solves (out of 2 unless noted):

| instance                  | H_A | H_ADAPT | H_D | H_G | H_P |
|---------------------------|-----|---------|-----|-----|-----|
| django__django-11066      | 0/1 | 0/1     | 2/2 | 1/2 | 2/2 |
| django__django-11206      | 0/1 | 0/1     | 0/2 | 1/2 | 0/2 |
| sympy__sympy-16766        | 0/1 | 0/1     | 0/2 | 0/2 | 1/2 |
| (other 17 instances)      | 0   | 0       | 0   | 0   | 0   |

## The wide-T=4 floor swallows the factorial

Every arm is at the floor: solve 0-7.5%, edit 0.00-0.12/ep. The wide set is
harder than the pilot (sympy dominates), and T=4 is the scarcest budget. Dots3
on real SWE at this operating point almost never reaches an edit in *any*
harness: H_A literally never edits (0 real edit-tool calls in 20 episodes; 2 in
the older 40-episode wide run). The differences between arms are 1-3 episodes
across 20-40 samples -- within the noise band (+-10pt at n=40). The factorial
cannot resolve prompt-vs-gate at this operating point.

The direction the floor data leans, for what it is worth, is the opposite of the
pilot intuition: the phase prose alone (H_P) produced the most real edits (5 in
40), the most test-suite runs (3 in 40), and the most solves (3); silent gating
(H_G) produced the fewest (2 edits, 0 tests, 2 solves). The pure instruction
text that was *inert as a static paragraph* in H_A' (the triangle) is *not*
inert as a per-turn phase banner that names the turn and the remaining budget.
The likely reason: the banner announces that the tool list has changed ("PHASE
2 of 3 -- EXECUTE"), which the model reads as a signal; the silent tool-list
swap of H_G is something dots3 does not notice on the wide set. If this
survives higher n, the Phase-5 "gating is the mechanism" claim narrows to
"gating is the mechanism on the pilot, where the model is one edit away; on the
wider set the binding constraint is finding the defect and editing within budget,
and the banner that announces the affordance matters at least as much as the
affordance itself." It does not survive n=40 here -- this is a direction, not a
result.

## Mechanism traces (the episodes that did edit)

H_P django-11066 (solved): `cat -n <file>` -> `edit <file>` -> `cat -n <file>`
-> `runtests.py contenttypes_tests...`. Inspect, edit, re-inspect, run the
suite -- the verify loop the phase prompts describe, driven by the prompt
banner alone with no gating.

H_P sympy-16766 (solved): `find` -> `grep` -> `sed -n` -> `edit pycode.py`.
Three inspects then the edit; no suite run, solved anyway.

H_G django-11206 (solved): `find` -> `find` -> `cat` -> `edit numberformat.py`
-> `python -c <repro>`. Gated recon, then the edit, then a manual repro (not
the suite). The one episode where silent gating alone produced an edit.

H_ADAPT django-11066, T=8 smoke (solved): RECON x2 (`find`, `cat -n`) -> EXECUTE
x6 (`find tests`, `cat tests`, `edit`, `cat -n | head`, `runtests x2`). The
deterministic scheduler: recon until the inspection pattern repeats, then
execute with edit, then the model runs the suite on its own. Rule C (force
VERIFY, bash-only, when edit-seen + not-tested + budget<=1) did not fire --
whenever the model edited it also tested within EXECUTE. Rule C remains an
unexercised safety net at T=8.

## H_ADAPT at T=4 is structurally late to edit

The scheduler's rules, as specified, give RECON a minimum of two turns (rule A:
same-inspect-pattern-repeats-twice; rule B: budget-remaining <= 2). At T=4 that
means RECON turns 1-2 and edit first available at turn 3, against H_D's fixed
1-recon / 2-execute / 1-feedback schedule where edit is available from turn 2.
So H_ADAPT trades one execute turn for one recon turn at the scarcest budget --
by design. 18 of 20 wide episodes were the same shape: `[RECON x2, EXECUTE x2]`
with four inspects and no edit. The scheduler behaved correctly; dots3 on the
wide set does not reach an edit in two execute turns at T=4. This is the
operating point where a *fixed* short recon is simply better, and where H_ADAPT
should lose to H_D. The adaptive design is meant for budgets long enough that
its dynamic recon-shrink and verify-allocate pay off -- Phase 6C's T=6/8.

## What this tells Phase 6C

The 6A grid says the decomposition is unmeasurable at wide x T=4: the floor is
too low for n=40 to separate arms that differ by 1-3 episodes. Two consequences:

1. The budget matrix (6C) should run H_A / H_D / H_ADAPT at T=6 and T=8 on the
   wide set -- budgets at which dots3 actually edits (the pilot budget sweep had
   H_A at 50% solve at T=8). There the harness differences and H_ADAPT's
   design intent can express themselves; the Phase-6 research question -- how a
   runtime should allocate affordance against remaining budget -- is answerable
   only where the model gets far enough to edit.
2. The H_P banner effect, if real, is a Phase-7 question (cross-model) worth a
   dedicated check at T=6: does announcing the affordance change outperform
   silently applying it? It is not separable at T=4.

## Reproduce

    # one program, four arms
    bash /tmp/run_swe_eval.sh tools/swe_lab/eval_real_wide_hD.toml  --run.name rl-2x2-hD  -c 1 --clean -n 20 -r 1
    bash /tmp/run_swe_eval.sh tools/swe_lab/eval_real_hP.toml     --run.name rl-2x2-hP  -c 1 --clean -n 20 -r 1
    bash /tmp/run_swe_eval.sh tools/swe_lab/eval_real_hG.toml     --run.name rl-2x2-hG  -c 1 --clean -n 20 -r 1
    # adaptive arm (Phase 6B)
    bash /tmp/run_swe_eval.sh tools/swe_lab/eval_real_hAdapt.toml --run.name rl-adapt -c 1 --clean -n 20 -r 1
    # pooled metrics + per-instance
    uv run python tools/swe_lab/analyze_2x2.py \
      --pattern "H_A=outputs/rl-2x2-hA*" "H_P=outputs/rl-2x2-hP*" \
                 "H_G=outputs/rl-2x2-hG*" "H_D=outputs/rl-2x2-hD*" \
                 "H_ADAPT=outputs/rl-adapt*"
    # H_ADAPT state attribution
    uv run python tools/swe_lab/adapt_profile.py rl-adapt smoke-adapt-t8