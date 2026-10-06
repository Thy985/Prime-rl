# E04 — Harness A/B/C: Does the Tool Set Change the Outcome?

## Question
If you remove one tool, does the agent stop succeeding — and is that effect
stable once you actually replicate?

## Hypothesis
H04: the tool set (action affordance) is the lever.

## Design
Three harnesses over the same task set, same model, same verifier:
- **H_A** — bash + edit, free-form turns.
- **H_B** — bash only (edit removed).
- **H_C** — H_A with a *completion-condition bound*: the episode cannot end while
  a change is pending.
Naming discipline: the completion-bound config was renamed to the harness it
actually configures (`b6c1ad9a8`, H_C) rather than left a generic name.

Each arm run **3 times**; results pooled at n=32 per cell.

## Controlled variables
Model, taskset, verifier, budget (the turn budget introduced in E03), runtime.
Only the tool set / completion condition varies.

## Arms
H_A | H_B | H_C, 3 runs each, pooled.

## Results
- **First harness A/B: removing one tool costs 44 points of solve rate**
  (`d43b15861`). Trajectory mining on the same runs: failures **never attempt a
  change at all** (`734496132`) — the binding failure is no-write, not a bad
  edit.
- Harness C: bounding the completion condition cut no-write and lifted solve
  (`af3bddf12`).
- **RETRACTED** (`6a1177c45`): at n=32 the Harness C effect **reverses**. The
  single-run result was noise. The retraction is committed and stands.
- At 3 runs each, the settled statement is narrower and sturdier:
  **tool support is the effect; difficulty is task × harness** (`d732e5ffd`).

## Interpretation
E04's real output is the pair: a large single-run effect, its reversal at
replication, and the settled claim that survives. That pair is the template the
rest of the archive follows — every later arm (E06's 2×2, E07's 7 arms) is
replicated before being named.

## What this rules out
- Tool-support claims from n=1 runs.
- "Harness C improves outcomes" — reversed at n=32.
- Treating difficulty as a property of the task alone.

## Limitations
H_B's effect is large enough to survive noise; H_C's was not, and that is the
point of the study rather than a nuisance. Only the swe-lab tiers here; the real
SWE version of the same comparison is E05.

## Evidence
- Commits: `d43b15861`, `734496132`, `af3bddf12`, `6a1177c45`, `d732e5ffd`,
  `b6c1ad9a8`, `6004a7559`
- Code: `tools/swe_lab_env/swe_lab_*.py` (H_A/H_B/H_C variants),
  `eval_patch*.toml` configs (`eval_patch_hd.toml`, `eval_patch_he.toml`,
  `eval_patch_hf.toml`, `eval_patch_noedit.toml`)
- Runs: `outputs/swe-lab-harnessA`, `outputs/swe-lab-harnessB-noedit`,
  `outputs/swe-lab-harnessC-patchfirst`, `outputs/swe-lab-abc-*`
- Analysis: `behavior.py`, `analyze_2x2.py`