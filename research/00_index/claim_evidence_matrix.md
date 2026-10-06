# Claim — Evidence Matrix

Each row: what we may say, on what, with what strength, and what we must **not**
say. Evidence IDs resolve through `02_experiments/`; raw numbers resolve through
`01_raw/runs/` + `01_raw/manifest.tsv`.

| Claim | Statement | Evidence | Strength | Limit |
| --- | --- | --- | --- | --- |
| C01 | A budget-binding agent harness changes solve rate on a graded lab set. | E03, E04 (`d43b15861`, `d732e5ffd`) | strong | Lab tiers only; not generalisation evidence. |
| C02 | Tool-availability change is a real and large lever. | E04: A vs B −44pt | strong | Established on H_B only; the H_C variant reversed at n=32. |
| C03 | Removing a phase's tool (affordance gating) explains H_D. | E06 (`6aea58419`, `ce618eed3`) | **refuted** | H_P = H_D 25% with no gate; H_G = 1/20 with no banner. |
| C04 | H_D improved the agent's reasoning. | — | **no evidence** | No arm measured reasoning; H05 was retracted on 0/120 planner turns. |
| C05 | The runtime effect is reproducible on real SWE-bench Verified. | E05 (`14c2b34e6`, `22f40cd41`) | moderate | Containerless in-filesystem verifier, not the official harness. |
| C06 | H_D +32pt over H_A on real SWE. | E05 pilot (`22f40cd41`), calibrated in `6bc971c6b` | moderate, **pilot only** | 5 instances, 1 repo, 1 model. Wide 20-instance set: **+10pt** — 4× shrink. |
| C07 | The effect is budget-shaped, not structural. | E05 (`a867f112d`) | moderate | Peak T=4 (+32pt), crosses to −6pt at T=8; T=8 cross within noise at n=16/cell. |
| C08 | Static behaviour prose reproduces the gain. | E05 (`625653bb4`) | strong negative | H_A-prime 1/16 vs H_A 2/16 vs H_D 7/16. |
| C09 | The harness effect replicates on a second model. | E05 (`e559251f3`): bunny H_A 19% vs H_D 31% | moderate | Same 5-instance grid, n=16/cell; not the 20-instance set. |
| C10 | Harness trajectories distil into a small student policy. | E05 (`1df2989df`) | **refuted for this route** | dots3→Qwen3-0.6B LoRA, H_A eval: 0/10 tool calls both, 0/10 resolve. Route-specific, not general. |
| C11 | Repeated user-role injection of phase context is load-bearing. | E07 (`3b4f0286e`): H_ONCE 5% vs H_NEUTRAL 5% vs H_ACTION 15% vs H_P 25% | moderate | **Single seed.** H_ONCE survives replication (C14). |
| C12 | Injection *position* at phase boundaries is a fourth dimension. | E07/E08 (`323655757` n=20, `a5975ac74` n=60) | **refuted** | n=60: H_REPLAY 17% > H_P 13%, p=0.77. Timing is not load-bearing. |
| C13 | H_P = 25% on the wide set. | E07 (`3b4f0286e`), revised in `a5975ac74` | **overclaimed** | Single seed. At n=60, H_P = 13% (s1 = 2/20, s2 = 3/20; seed-2 rerun 0/20). |
| C14 | Banner vs no-banner improves solve rate. | E08 (`a5975ac74`) | strong | **p = 0.031, McNemar, one-sided, paired on 20 instances, n=60.** Same-instance pairing only. |
| C15 | Multiple injections beat a single injection. | E08 (`a5975ac74`) | strong | **p = 0.008.** Same pairing caveat. |
| C16 | The banner changes action allocation, not interaction effort. | E08 mediation (`0807caa0c`, `a5975ac74`) | moderate | state_chg 0.04→0.07 (0.17→0.30 solved-only); n_calls flat; first_edit not earlier. Mediation chain, **not a formal causal estimate.** |
| C17 | Runtime intervention changes action allocation, not reasoning. | E07 (`d0985e941`), E08 (`a5975ac74`) | moderate | Role claim deliberately narrowed: H_SYS shows system-role ≠ user-role. **Not** "interruption is causal." |
| C18 | The effect is cross-model. | E08A (`51f7ae526`) | **no evidence** | Bunny provider failed (F08); DeepSeek-v4-flash never run. Claim must not be made. |

## What we must not claim

1. **Not reasoning.** No measurement supports it; the closest arm (H05) was
   retracted on its own trace data.
2. **Not general SWE competence.** The strongest quantitative claim is +10pt on
   a 20-instance, 2-repo set at one budget.
3. **Not cross-model.** Two models were *attempted* for the banner study;
   neither completed. Only the earlier pilot-tier comparison has a second model.
4. **Not causation of interruption.** H_SYS is a role contrast, not an
   interruption test.
5. **Not a distillation result.** "Route rejected" is the finding; "distillation
   cannot work" is not.
6. **Not provider-neutral conclusions.** Any bunny/DeepSeek gap is an
   infrastructure fact, not a model fact.