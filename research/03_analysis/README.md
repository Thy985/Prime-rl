# 03_analysis — Derived Analysis

Everything here is **regenerable**. None of it is evidence; it is a convenience
layer over `01_raw/`. If a derived file disagrees with the raw data, the raw
data wins and the derived file is wrong.

## Artifacts

| File | Contents | Source |
| --- | --- | --- |
| `runs_inventory.tsv` | 176 run directories: pass@1, reward, resolve, is_completed, has_error, stop_condition, n, model, max_turns, harness env, banner/gate flags, file count | `outputs/*/monitors/file/metrics.jsonl` and `configs/attempt_1/eval.toml` |
| `session_index.tsv` | 3 session exports: path, sha256 prefix, record count, prompt count, model, tool-use top-8, start/end | `dsh-session/` and `subagents/*/session.v4.jsonl` |
| `code_inventory.tsv` | File inventory for `tools/swe_lab/` and `tools/swe_lab_env/` | filesystem |
| `git_experiment_range.tsv` | The 82 experiment commits (`86e9e8366^..83c990b00`) with full dates | `git log` |
| `../01_raw/ai-sessions/user_prompts_extract.txt` | 88 substantive user prompts with message IDs | main session export |

## How to regenerate

All of these were produced by small Python scripts that read the repository and
write TSV. The commands that produced the freeze-point figures:

```
# run inventory (pass@1 per run dir)
python3 .archive-work/runkv.py

# session metadata
python3 .archive-work/sessions.py

# file inventory
python3 .archive-work/cm.py

# commit range
git log --format='%H%x09%ci%x09%s' 86e9e8366^..83c990b00
```

The transient tooling has been removed from the archive; the commands above are
the contract. Re-run them against the repository at any commit to reproduce
these tables, or to check whether they have drifted.

## One derived figure worth knowing

`runs_inventory.tsv` lets a reader recompute the E08 headline without opening
any writeup. Four arms, three seeds, pass@1:

| Arm | seed 0 | seed 1 | seed 2 | mean |
| --- | --- | --- | --- | --- |
| H_A | 0.000 | 0.105 | 0.105 | 7% |
| H_ONCE | 0.050 | 0.000 | 0.059 | 3% |
| H_P | 0.250 | 0.000 | 0.150 | 13% |
| H_REPLAY | 0.158 | 0.211 | 0.150 | 17% |

Seed 0 for the H_A/H_ONCE/H_P arms is the E07 single-seed run
(`rl-6c-hA-T6`, `rl-7-hOnce`, `rl-6c-hP-T6`); the two 8C seeds are
`rl-8c-*`. H_REPLAY's "seed 0" is `rl-8-hReplay`, the Phase 8B run.

## What derived analysis cannot do

It cannot supply the paired analysis. The p-values (0.031, 0.008, 0.77) come
from per-instance McNemar on the 20 shared tasks, which requires the trace
annotations under `traces/annotations/`, not the aggregate metrics. Those are
not tabulated here because they are the load-bearing numbers of the freeze point
and belong in the writeup, not in a convenience table.