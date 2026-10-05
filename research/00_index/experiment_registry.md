# Experiment Registry

Eight canonical experiments. Each row answers one question; the canonical record
lives in `02_experiments/`. Raw runs are untracked (`outputs/` is gitignored) and
are hashed in `01_raw/manifest.tsv`.

| ID | Question | Key control | Freeze evidence | Status |
| --- | --- | --- | --- | --- |
| E01_reverse_text | Can a learned capability be shaped by reward and survive a non-destructive update? | LoRA SFT + RL plumbing on reverse-text, reward ablation V1/V2/V3 | branch `exp/reverse-text-pipeline` (8 commits); `tools/swe_lab/PLAN.md` §0 | closed; two conclusions retracted |
| E02_verifier_audit | Is the reward itself trustworthy before any capability claim? | Environment contract + Golden Episode + replay acceptance | `498fca529`, `b2698922c`, `56a6c91d1` | accepted |
| E03_swe_micro | Does a graded task set separate the agent's behaviour? | Tiered ladder + per-tier audit + budget frontier | `57e81c8af`, `5ef3bf8ee`, `2755ba56f`, `a56e6ae13`, `6004a7559` | accepted |
| E04_harness_ab | Does changing the tool set change the outcome? | Harness A (bash+edit) vs B (no edit) vs C (completion bound) | `d43b15861`, `af3bddf12`, `6a1177c45`, `d732e5ffd` | accepted with a retraction |
| E05_real_swe | Does the harness effect survive real SWE-bench Verified? | Containerless verifier pipeline; H_D vs H_A; budget sweep; wide set; second model; distillation | `14c2b34e6`, `22f40cd41`, `625653bb4`, `9136aac03`, `a867f112d`, `e559251f3`, `1df2989df`, `247fc2fc7`, `6bc971c6b` | accepted; pilot claim downgraded |
| E06_harness_mechanism | Is the affordance gate the mechanism? | 2×2 prompt × gate + adaptive scheduler; H_P vs H_G | `2bae38d38`, `3117af867`, `8f7a62b84`, `6aea58419`, `ce618eed3`, `b2207c3d4` | **gating falsified** |
| E07_banner | Which property of the injected text carries the effect? | 7 arms varying text, cadence, role; dots3 + wide-20 + T=6 fixed | `f3a91ba36`, `3b4f0286e`, `7ca05d71d`, `610450d35`, `d0985e941` | accepted |
| E08_expanded_n | Which single-seed claims survive replication? | 4 arms × 3 seeds × 20 tasks = n=60; paired analysis; mediation | `0807caa0c`, `323655757`, `a5975ac74` (**freeze**) | frozen |

## Phase map

| Phase | Experiments | Range |
| --- | --- | --- |
| P0 | E01, E02 | 2026-09-27 → 10-01 |
| P1–P3 | E02, E03, E04 | 10-01 → 10-02 |
| P3.5 / P4.5 | E05 | 10-02 → 10-03 |
| P5 | E05 | 10-04 → 10-05 |
| P6 | E06 | 10-05 |
| P7 | E07 | 10-05 |
| P8A / 8B / 8C | E08 | 10-05 → 10-06 |

## What is deliberately not an experiment

- `outputs/sft-*`, `short-ovf*`, `reverse_text_local`, `m2-*`, `base-eval*`
  are E01 infrastructure and sanity runs, not evidence.
- `smoke-*` runs are protocol checks, not result evidence. They are listed in
  `01_raw/manifest.tsv` so their absence from a claim is auditable.
- Provider-failed arms (bunny Phase 6C, DeepSeek-v4-flash, bunny Phase 8A) are
  not negative results; see `05_process/failure_ledger.md` F08.