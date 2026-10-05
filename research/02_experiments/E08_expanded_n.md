# E08 — Expanded n: Which Single-Seed Claims Survive Replication

## Question
Every conclusion from E06/E07 came from a single seed at n=20. Which ones survive
replication to n=60, and which are seed artefacts?

## Hypothesis
H15 (rejected): phase-boundary timing is a fourth load-bearing dimension.
H16 (partly rejected): the banner effect survives replication — in fact the *size*
did not.
H17 (supported): the banner changes action allocation, not reasoning or effort.
H18 (untested, blocked): the effect replicates across models.

## Design
- **Phase 8A** — cross-model replication: bunny arms (`rl-6c-bunny-*`),
  DeepSeek-v4-flash arms, `timeout.rollout=1200` for the slower model,
  `SWE_LAB_PROMPTS=0` for the no-banner arm.
- **Phase 8B** — one new arm, **H_REPLAY**: 3 injections at turns 1/3/5, which
  decouples injection *count* from phase *boundaries*. If phase-boundary timing
  mattered, H_REPLAY should drop below H_P at equal count.
- **Phase 8C** — replication proper: 4 arms × 3 seeds × 20 tasks = **n=60 per
  arm**, then per-instance paired analysis and a trajectory mediation chain.

## Controlled variables
dots3, wide 20-instance set, T=6, edit always present, same banner semantics as
E07. Seeds are the only new axis.

## Arms
H_A | H_ONCE | H_P | H_REPLAY, 3 seeds each.

## Results

Per-seed `pass@1` read from the run directories (see `01_raw/manifest.tsv`):

| Arm | seed 0 (E07 run) | seed 1 | seed 2 | n=60 |
| --- | --- | --- | --- | --- |
| H_A | 0.000 (`rl-6c-hA-T6`) | 0.105 (`rl-8c-hA-s1`) | 0.105 (`rl-8c-hA-s2`) | **7%** |
| H_ONCE | 0.050 (`rl-7-hOnce`) | 0.000 (`rl-8c-hOnce-s1`) | 0.059 (`rl-8c-hOnce-s2`) | **3%** |
| H_P | 0.250 (`rl-6c-hP-T6`) | 0.000 (`rl-8c-hP-s1`) | 0.150 (`rl-8c-hP-s2`) | **13%** |
| H_REPLAY | 0.158 (`rl-8-hReplay`) | 0.211 (`rl-8c-hReplay-s1`) | 0.150 (`rl-8c-hReplay-s2`) | **17%** |

- **H_P's 25% was single-seed noise.** Seed-1 rerun scored **0/20**. The E07
  headline number halves.
- **H_REPLAY 17% > H_P 13%, p = 0.77.** Phase-boundary timing is **not** a real
  dimension; it did not survive.
- **Banner vs no-banner survives: p = 0.031** (McNemar, one-sided, paired on the
  20 instances).
- **Multiple-vs-single injection survives: p = 0.008.** Repetition, not
  position, is the load-bearing property.
- **Mediation chain holds at n=60**: `state_chg` 0.04 → 0.07 (0.17 → 0.30
  on solved-only), `n_calls` flat, `first_edit` not earlier. Action allocation,
  confirmed — not more effort, not earlier action, not more calls.

## Interpretation
This is the archive's most important experiment, and it is a negative one.
Three-quarters of the narrative built in E07 shrank or died under replication;
two claims survived because they were paired on the same instances rather than
compared as aggregate rates. The surviving finding is narrower than the
headline ever was: **repeated user-role injection of phase context changes how
the agent allocates its actions, and that change improves the outcome at this
budget.**

## What this rules out
- H_P's 25% as a property of the wide set.
- Phase-boundary timing as a mechanism.
- Any unreplicated single-seed number quoted in earlier writeups
  (`swe_7_banner.md` headline, `swe_6c_matrix.md` 25% cell).

## Limitations
- n=60 is still 20 tasks × 3 seeds. Power for a 13% vs 7% gap is thin; the
  p-values come from paired McNemar, not from independent samples.
- **Cross-model is still untested.** Bunny was blocked by provider failure
  (`deep-ep` metadata on aarch64, fixed in `6315a6e06`, then abandoned), and
  DeepSeek-v4-flash never ran. See `05_process/failure_ledger.md` F08.
- Mediation is an observational chain on the same trajectories, not a formal
  causal estimate.
- Only 2 repos, 20 instances; no task-family stratification.

## Evidence
- Commits: `571774e43`, `323655757`, `0807caa0c`, `6315a6e06`, `51f7ae526`,
  `b257519fe`, **`a5975ac74` = `research-p8c-final`**
- Configs: `eval_real_8_hReplay.toml`, `eval_real_8_bunny_{hA,hOnce,hP}.toml`,
  `eval_real_8_deeps_{hA,hP,hOnce}.toml`, `eval_real_6c_bunny_*`
- Analysis: `analyze_banner.py` (ARMS updated for H_REPLAY),
  `analyze_cross_model.py`
- Runs: `outputs/rl-8c-{hA,hOnce,hP,hReplay}-{s1,s2}`, `outputs/rl-8-hReplay`,
  `outputs/rl-8-bunny-*`, `outputs/rl-8-deeps-*`, `outputs/smoke8-*`
- Writeup (frozen text): `tools/swe_lab/runs/swe_8c_expanded.md`
  — revised at `a5975ac74` (+65/−55 vs `b257519fe`)
- Tag: `research-p8c-final`