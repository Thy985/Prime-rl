# E05 — Real SWE-bench Verified: Calibration, Budget, Second Model, Distillation

## Question
Does the harness effect survive contact with real SWE-bench Verified — and if it
does, how big is it, at what budget, on what models, and can it be learned?

## Hypothesis
H08: the effect generalises beyond the 5-instance pilot.
H09 (rejected): static behaviour prose is the active ingredient.
H10 (rejected): the gain is budget-independent.
H07 (route rejected): harness trajectories distil into a small student policy.

## Design
Built from scratch because there is **no container runtime on this box**:
1. `prepare.py` clones the repo at the base commit.
2. `verify.py` is a **5-check gate** that applies the oracle test patch to a
   host-side copy and runs each F2P / P2P under a per-repo interpreter.
3. `manifest.json` → `taskset.py` (the `swe_bench` taskset) exposes instances.
4. `resolve` = 1.0 iff all F2P + P2P pass; tampering voids the score;
   `f2p_fraction` is 0-weight.
5. `setup()` strips gold-fix references (origin, post-base tags, reflog).

Then five controlled experiments over the same pipeline:
pilot → budget sweep → wide multi-repo set → second model → distillation.

## Controlled variables
Model (`9router/dots3-note-prev` unless stated), `max_turns`, temperature 0.0,
`-c 1`, `timeout.rollout=600` (1200 for the slower model), bare H_A as the
distillation evaluation protocol so the harness itself is not confounded.

## Arms
H_A (bash + edit, free) | H_D (staged recon/execute/verify,
`SWE_LAB_PHASES="1,2,"`) | H_A-prime (H_A + one static behaviour paragraph)
| pi-base / pi-D-lora (Qwen3-0.6B, untrained vs SFT'd).

## Results
- **Pilot, 5 gated django instances** (`14c2b34e6`): H_A 10% vs H_D 30%.
  Two instances gated out: 11239 (P2P is a docstring, needs psql) and
  12155 (F2P already passes → no signal).
- **Topup to 5 eps/harness on 11066/11206** (`22f40cd41`): **H_D 7/16 = 44%
  vs H_A 2/16 = 12%, +32pt.** 11066: 5/5 (H_D) vs 2/5 (H_A); 11206: 2/5 vs 0/5.
- **Budget sweep, T ∈ {2,4,6,8}** (`a867f112d`): gap **+6 → +32 → +19 → −6pt**.
  Peak at T=4; **crosses to −6 at T=8** (within noise at n=16/cell). At T=8
  H_A self-discovers verify + repair (tstAft 50%, repair 12%).
- **Wide 20-instance, 2-repo set** (`247fc2fc7` adds sympy; `6bc971c6b`
  calibrates): **gap shrinks 4× — +32pt → +10pt** (`rl-wide-hA` 0.0,
  `rl-wide-hD` 0.1). H_D still solves instances H_A never does.
- **Second model** (`e559251f3`, space-bunny 7B, same 5-instance grid):
  **H_A 19% vs H_D 31%, +12pt** — direction reproduces, magnitude smaller.
- **H_A-prime control** (`625653bb4`): **1/16 vs 2/16 vs 7/16** — static prose
  recovers none of the gap. **No arm in 32 episodes ever runs the test suite.**
- **Turn-by-turn mechanism probe** (`9136aac03`): **0 bash refusals in 48 eps**
  (the gate is edit-tool *absence*, not refusal), **0 test runs**
  (told-to-verify is never obeyed), H_D gets **3.5× more edits per episode**.
- **Distillation** (`1df2989df`): dots3 D_D teacher → Qwen3-0.6B LoRA SFT,
  eval under bare H_A. Untrained: 0/10 tool calls, 0/10 resolve.
  After SFT: **0/10 tool calls, 0/10 resolve.** No behaviour transfer.

## Interpretation
The effect is real but small and conditional: **+32pt is a 5-instance,
4-turn pilot number; the honest wide-set number is +10pt at the peak budget,
and the gain disappears at T=8.** The mechanism is not reasoning and not
verification — it is *editing more often before the budget runs out*.

## What this rules out
- Test-driven verification as the mechanism (0 test runs in 32 episodes).
- Static instruction text as the mechanism.
- Budget-independent harness value.
- A general distillation route. What was rejected is one specific route:
  dots3 → Qwen3-0.6B, 20-step LoRA, no tool-format alignment, H_A eval.

## Limitations
- Containerless verifier, not the official SWE-bench harness.
- 5-instance pilot grid; 20-instance wide set only at T=4.
- `f2p_fraction` carries no weight, so partial credit is invisible.
- Distillation negative is route-specific, not general.
- Multi-seed was only attempted from E08; E05 is single-seed throughout.

## Evidence
- Commits: `14c2b34e6`, `22f40cd41`, `247fc2fc7`, `3786b0ae5`, `1df2989df`,
  `625653bb4`, `9136aac03`, `a867f112d`, `e559251f3`, `6bc971c6b`
- Code: `tools/swe_lab_env/swe_bench/{prepare,verify,taskset}.py`,
  `gating.py`, `behavior_real.py`, `analyze_cross_model.py`
- Configs: `eval_real_{hA,hD,hA_prime,hP}.toml` (T=4 pilot, `max_turns = 4`),
  `eval_real_wide_{hA,hD}.toml`, `eval_sft_local.toml`, `sft_real_D.toml`.
  Per-T sweep configs were generated to `/tmp/sweep/` at run time by the
  reproducer's `sed` and are **not** in the tree; only the T=4 base configs
  survive.
- Runs: `outputs/rl-hA`, `outputs/rl-hD`, `outputs/rl-hAp`, `outputs/rl-wide-hA`,
  `outputs/rl-wide-hD`, `outputs/rl-sb-hA`, `outputs/rl-sb-hD`,
  `outputs/rl-{hA,hD}-T{2,6,8}` and their `-topup` companions where they exist.

## Reconstructability of the budget-sweep table — verified, all eight cells

The writeup's `16 per cell` is a **weighted pool of two directories**, and the
pool reproduces every cell exactly (checked cell by cell during archival):

- base run: `num_examples = 5`, `group_size = 2` => **10 episodes**
- topup run: the reproducer's `-n 2 -r 3` => **6 episodes**
- pooled cell: **10 + 6 = 16 episodes**

| T | arm | base pass@1 (10 eps) | topup pass@1 (6 eps) | pooled | writeup | |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | H_A | 0/10 | 0/6 | **0/16** | 0/16 | exact |
| 2 | H_D | 0/10 | 1/6 | **1/16** | 1/16 | exact |
| 4 | H_A | 1/10 | 1/6 | **2/16** | 2/16 | exact |
| 4 | H_D | 3/10 | 4/6 | **7/16** | 7/16 | exact |
| 6 | H_A | 3/10 | 2/6 | **5/16** | 5/16 | exact |
| 6 | H_D | 3/10 | 5/6 | **8/16** | 8/16 | exact |
| 8 | H_A | 3/10 | 5/6 | **8/16** | 8/16 | exact |
| 8 | H_D | 2/10 | 5/6 | **7/16** | 7/16 | exact |

Notes for the reader:

1. **T=4 has no directory of its own** — it is the base config
   (`eval_real_hA.toml` / `eval_real_hD.toml`, `max_turns = 4`). The reproducer
   loops `for T in 2 6 8` and generates per-T configs to `/tmp/sweep/` at run
   time, so only the T=4 configs survive in the tree. The writeup's T=4 row is
   the pool of `rl-hA`+`rl-hA-topup` and `rl-hD`+`rl-hD-topup`.
2. **`runs_inventory.tsv` cannot reproduce a cell on its own** — it records one
   `pass@1` per directory (e.g. `rl-hD` 0.3, `rl-hD-topup` 0.6667), and a cell
   is the weighted pool of the pair. Single-directory numbers must not be
   quoted as cell values.
3. The numbers behind the archive's most-cited figure (+32pt at T=4) are exact,
   not approximate. What is not archived is the *curve-shape claim* in prose
   form; the numbers themselves are fully reconstructable.
- **Do not conflate the two T=6 measurements.** E06's T=6 decomposition
  (H_P 25% / H_G 5.6% / H_D 29.4%) is on the wide 20-instance set
  (`rl-6c-h{P,G,D}-T6`, n=20, `max_turns = 6` confirmed in config). The
  budget-sweep T=6 row is on the 5-instance pilot grid. Same budget, different
  task set; H_D reads 29.4% and 50% respectively while the direction agrees.
- Writeups: `tools/swe_lab/runs/swe_bench_pilot.md`,
  `swe_budget_sweep.md`, `swe_second_model.md`, `swe_distill_verify.md`,
  `swe_stage_conclusion.md`