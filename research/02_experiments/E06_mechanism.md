# E06 — Harness Mechanism: Affordance Gating Falsified

## Question
Is the *gate* the mechanism — i.e. does removing `edit` from the recon phase do
the work — or is it the *banner* that announces the phase change?

## Hypothesis
H11: affordance gating is the mechanism behind H_D.

## Design
A 2×2 factorial over the two ingredients of H_D, holding everything else fixed:

|           | gate OFF | gate ON  |
|-----------|----------|----------|
| banner ON | H_P      | H_D      |
| banner OFF| H_A      | H_G      |

- **H_P** = per-turn phase banner, edit tool present every turn.
- **H_G** = edit tool gated out of recon, **no** banner.
- Plus **H_ADAPT**, a deterministic affordance scheduler: recon → execute →
  verify, driven by observed calls (state machine on `SWE_LAB_BUDGET`), to test
  whether a smarter gate helps where a fixed gate fails.
- Decomposition arms added at T=6 (the budget where signal exists).

## Controlled variables
dots3, wide 20-instance set, `SWE_LAB_PROMPTS` / `SWE_LAB_GATE` as the only
switches, budgets T ∈ {2,4,6,8}, T=6 as the primary budget.

## Arms
H_A | H_P | H_G | H_D | H_ADAPT, across T = 2 / 4 / 6 / 8.

## Results
- **Phase 6A 2×2 at wide × T=4 is a floor regime** (`3117af867`): solve
  0–7.5%, edit 0–0.12/ep. The factorial is **underpowered at n=40** — this is
  recorded, not hidden.
- **Phase 6C budget matrix** (`8f7a62b84`): H_D is an inverted U —
  **T6 = 25% peak, T8 = 10%**; H_A and H_ADAPT converge to **15% at T8**.
  **H_ADAPT never beats H_D** (a recon-2 tax), and the **VERIFY rule never
  fires**. Budget-dependent harness value; the v1 adaptive rules are
  miscalibrated.
- **T=6 decomposition** (`6aea58419`) — the decisive run:
  **H_P (banner only) 5/20 = H_D 25%; H_G (gate only) 1/20 (floor).**
  Banner is the mechanism; silent gating is not. **Affordance scheduling is
  falsified at a signal-bearing budget.**
- **Pilot confirmation** (`ce618eed3`): **H_P reproduces H_D exactly —
  7/16 = 44%, same instances, edit tool present every turn.** Enforcement
  adds nothing.
- `first_edit_turn` decomposition (`b2207c3d4`): H_G does not push first edit
  earlier; **H_P does**.
- Triangle conclusion and stage conclusion rewritten accordingly.

## Interpretation
The effect is **not** tool availability. It is the per-turn announcement of the
current phase. This kills H04's residual "tool set is the lever" reading for the
harness case and redirects the whole programme to E07: if the banner is the
mechanism, then *which part of the banner* matters — repetition, content, or
role?

## What this rules out
- Silent affordance gating as the mechanism.
- Adaptive scheduling (v1 rules) as an improvement.
- Any harness claim at T=4 on the wide set, which is a floor regime.

## Limitations
- The 2×2 at T=4 was underpowered; the conclusion rests on T=6 plus the pilot
  replication, not on the factorial itself.
- `first_edit_turn` moved for H_P but that is a behaviour change, not proof of
  causal direction.
- H_ADAPT was a deterministic scheduler with three rules; a richer controller
  is untested.

## Evidence
- Commits: `2bae38d38`, `4b6854707`, `3117af867`, `1908e3c5b`, `8f7a62b84`,
  `6aea58419`, `ce618eed3`, `b2207c3d4`, `62f70d41a`
- Code: `tools/swe_lab_env/swe_lab_adaptive.py`,
  `swe_lab_adaptive_executor.py`, `swe_lab_planner_program.py`, `gating.py`
- Configs: `eval_real_hP.toml`, `eval_real_hG.toml`, `eval_real_6c_*`
- Analysis: `analyze_2x2.py`, `analyze_matrix.py`, `analyze_cross_model.py`
- Runs: `outputs/rl-2x2-hA`, `outputs/rl-2x2-hD`, `outputs/rl-2x2-hP`,
  `outputs/rl-2x2-hG`, `outputs/rl-adapt`, `outputs/rl-6c-*`, `outputs/smoke-*`
- Writeup: `tools/swe_lab/runs/swe_2x2.md`, `swe_6c_matrix.md`
- Metric fix: `4b6854707` — `WRITE_RE` no longer flags `2>/dev/null` and `2>&1`
  as tree writes (H_A real edits 0/20 wide T=4, not 0.5/ep). **Every conditional
  write rate in this archive must be read after this fix.**