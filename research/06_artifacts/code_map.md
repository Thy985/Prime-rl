# Code Map

This is a map, not documentation. No code is explained here; every entry points
at a file so a reader can open it.

## Agent runtime (`tools/swe_lab_env/`)

| File | Role | Load-bearing |
| --- | --- | --- |
| `swe_lab_planner_program.py` | Banner injection: `SWE_LAB_BANNER` modes, `SWE_LAB_BANNER_ROLE`, `SWE_LAB_PROMPTS`, `SWE_LAB_GATE` | **the intervention itself** (E06, E07) |
| `swe_lab_planner_executor.py` | Phase protocol text under `SWE_LAB_PROMPTS` | H_D |
| `swe_lab_adaptive.py` | Deterministic affordance scheduler on `SWE_LAB_BUDGET` | H_ADAPT (E06, falsified) |
| `swe_lab_adaptive_executor.py` | Scheduler executor | H_ADAPT |
| `swe_lab_patch_first.py` | Patch-first harness variant | E04 |

## Environment (`tools/swe_lab_env/swe_bench/`)

| File | Role |
| --- | --- |
| `prepare.py` | Clones the repo at the base commit, in-filesystem (no container runtime on this box) |
| `verify.py` | 5-check gate: applies the oracle test patch to a host-side copy and runs F2P / P2P under a per-repo interpreter |
| `taskset.py` | `swe_bench` taskset; appends the H_A-prime prose under `SWE_REAL_H_A_PRIME=1` |
| `manifest.json`, `manifest_candidates.json` | Per-instance manifests |

## Verification and lab (`tools/swe_lab/`)

| File | Role | Experiments |
| --- | --- | --- |
| `contract.py` | Environment contract | E02 |
| `golden.py` | Golden Episode | E02 |
| `replay_executing.py` | Executing-reward replay acceptance | E02 |
| `terrain.py` | Seed terrain + structured verdict | E02 |
| `ladder.py` | Difficulty ladder + per-tier audits | E03 |
| `frontier.py` | Capability frontier, budget frontier | E03 |
| `behavior.py` | Tier behaviour metrics | E03, E04 |
| `behavior_real.py` | Real-SWE behaviour metrics | E05 |
| `gating.py` | Turn-by-turn gating probe | E05, E06 |
| `episode_scripted.py`, `index_episode.py` | Episode scripting and indexing | E02 |

## Analysis (`tools/swe_lab/`)

| Script | Reads | Experiments |
| --- | --- | --- |
| `analyze_banner.py` | Banner injections plus trajectory metrics: state-changing ratio, inspect-run length, inspect-to-edit lag, edit-after-failed-test | **E07, E08** |
| `analyze_2x2.py` | 2x2 factorial | E06 |
| `analyze_matrix.py` | Budget matrix | E03, E06 |
| `analyze_cross_model.py` | Cross-model replication | E05, E08 |
| `training_view.py` | Trajectory to training view | E05 (distillation) |
| `adapt_profile.py`, `mine_trajectories.py`, `export_pi.py`, `merge_adapter.py` | Distillation pipeline | E05 |

## Launch

| File | Role |
| --- | --- |
| `run_swe_eval.sh` | Wrapper: sources `.env`, sets `DUMMY_API_KEY`, `PYTHONPATH`, `SWE_REAL_PY`, adds `--no-sync` (`6315a6e06`) |
| `eval_real_*.toml` | Per-arm configs: `eval_real_7_*` (banner), `eval_real_6c_*` (budget matrix), `eval_real_8_*` (8B/8A), `eval_real_wide_*`, `eval_real_hA_prime.toml` |
| `eval_patch*.toml` | Tier patch-mode harness configs |

## Writeups (`tools/swe_lab/runs/`)

`PLAN.md` is the project spec and holds the E01 retraction table. The 14 writeups map to the registry as follows:

| Writeup | Experiments |
| --- | --- |
| `swe_bench_pilot.md` | E05 |
| `swe_budget_sweep.md` | E05 |
| `swe_second_model.md` | E05 |
| `swe_distill_verify.md` | E05 |
| `swe_stage_conclusion.md` | E05 (contains a pre-fix metric; see F12) |
| `swe_harness_triangle.md` | E06 (contains the corrected conditional write rates; authoritative for F08) |
| `swe_2x2.md`, `swe_6c_matrix.md` | E06 |
| `swe_7_banner.md` | E07 (headline numbers are single-seed; see F11) |
| `swe_8c_expanded.md` | **E08 — the frozen text** |
| `behavior_profile.md`, `cross_model.md` | E03, E04, E05 |
| `phase4_audit.md`, `phase4_data.md` | E05 distillation views |

## Verifier and lab fixture

- `deps/verifiers` (0.3.2.dev137) — `verifiers/v1` owns Task, Taskset, Harness,
  Runtime, Trace, Episode. Not re-implemented.
- `tools/swe_lab/fixture/` — two-file lab fixture with two seeded defects
  (`median` even-length, `parse_ranges` upper bound). Baseline: 4 passing,
  3 failing.
- `tools/swe_lab/tiers/` — tier1 single-file, tier2 multifile,
  tier3 regression-trap, tier4 hidden-config-layer, tier5 multi-constraint.

## Environment switches, one place

`SWE_LAB_PROMPTS`, `SWE_LAB_GATE`, `SWE_LAB_PHASES`, `SWE_LAB_BUDGET`,
`SWE_LAB_BANNER`, `SWE_LAB_BANNER_ROLE`, `SWE_REAL_H_A_PRIME`, `SWE_REAL_PY`.