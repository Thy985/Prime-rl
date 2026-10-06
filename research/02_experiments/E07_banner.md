# E07 — Banner Mechanism Decomposition

## Question
The banner carries the effect. Which property of the banner — repetition,
content, or message role — is load-bearing?

## Hypothesis
H12 (supported): repeating the phase context every turn is necessary.
H13 (supported, narrowed): message role is load-bearing.
H14 (supported): content and cadence are independent, non-substitutable levers.
H15 (rejected at E08): phase-boundary timing is a fourth dimension.

## Design
Hold dots3 + wide 20-instance set + T=6 + edit-always-available fixed and vary
**only the per-turn banner** (`SWE_LAB_BANNER`):

| Arm | Banner |
|-----|--------|
| H_A | no banner |
| H_ONCE | phase context once (turn 1 only) |
| H_NEUTRAL | neutral text, phase-neutral |
| H_ACTION | action-oriented text |
| H_P | full phase context every turn |
| H_PHASE | phase name per turn |
| H_SYS | same text as H_P, in the **system** role |

H_SYS was added specifically to test message role: `SWE_LAB_BANNER_ROLE=user`
vs `system`, same text, same cadence.

## Controlled variables
Model, taskset, budget T=6, edit tool always present, runtime, verifier. Only
the banner text, its cadence, and its message role vary.

## Arms
H_A | H_ONCE | H_NEUTRAL | H_ACTION | H_P | H_PHASE | H_SYS, 20 eps each (n=20 per arm).

## Results
- **Five-arm decomposition** (`3b4f0286e`): **H_A 0%, H_ONCE 5%,
  H_NEUTRAL 5%, H_ACTION 15%, H_P 25%.** Recency is necessary; neutral status is
  inert; content is secondary.
- **Injection measurement corrected** (`7ca05d71d`): H_ACTION / H_PHASE are
  *every-turn* injections, not phase-boundary. Content and cadence are both
  independently demonstrated levers: **content 5%→15%** (neutral→action),
  **cadence 15%→25%** (every-turn→phase-start).
- **H_SYS at 15%** (`610450d35`) vs H_P 25%: message role is load-bearing.
  Three single-factor arms each cost ~10pt, and repetition is the necessary
  condition.
- **Boundary of the claim** (`d0985e941`): H_SYS shows *system-role ≠ user-role*.
  It does **not** show that interruption is causal. Terminology settled as
  "user-turn runtime intervention" / "per-decision control-plane injection".
- H_ACTION vs H_PHASE tie is the cleanest separation of content from cadence.
- Two H_PHASE rollouts were 600s timeouts, so 15% is a floor and the dilution
  finding is conservative (`7e8346b05`).

## Interpretation
Three independent levers are now demonstrated, and the three-layer model is
formed:
1. **Phase 5** — Harness changes behaviour.
2. **Phase 6** — the tool gate is not what changes it.
3. **Phase 7** — runtime context injection changes it, and role, cadence and
   content all matter.

The mediator is `n_calls` staying flat while inspect / edit / state-changing
action distribution shifts — the banner changes **action allocation**, not
total cognitive effort.

## What this rules out
- A single-injection announcement as sufficient.
- Neutral status text as a control-plane anchor.
- System-role injection as equivalent to user-role injection.
- "Harness improves reasoning" as a description of the effect.

## Limitations
- **All 7 arms are single-seed at n=20.** This is exactly what E08 had to fix.
- Role contrast is a contrast of injection position, not a causal interruption
  test.
- No cross-model replication within E07; the banner-semantic bunny/DeepSeek arms
  are E08A and were blocked by provider failure.

## Evidence
- Commits: `f3a91ba36`, `3b4f0286e`, `d66e04021`, `7e8346b05`, `7ca05d71d`,
  `610450d35`, `d0985e941`
- Code: `SWE_LAB_BANNER` modes in `swe_lab_planner_program.py`;
  `analyze_banner.py` counts banner injections and trajectory metrics
  (state-changing ratio, inspect-run length, inspect-to-edit lag,
  edit-after-failed-test)
- Configs: `eval_real_7_*.toml` (hNeutral, hOnce, hAction, hPhase, hSys,
  hNeutral_smoke, …)
- Runs: `outputs/rl-7-hAction`, `outputs/rl-7-hNeutral`, `outputs/rl-7-hOnce`,
  `outputs/rl-7-hPhase`, `outputs/rl-7-hSys`, `outputs/smoke7-*`
- Writeup: `tools/swe_lab/runs/swe_7_banner.md`