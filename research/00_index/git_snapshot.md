# Git Snapshot at Freeze

## Repository

- url: https://github.com/PrimeIntellect-ai/prime-rl (vendored; this is a fork working copy)
- branch: `exp/swe-verifier-terrain`
- experiment commit range: `86e9e8366..83c990b00` — **82 commits**, 2026-10-01 11:29 → 2026-10-06 06:37
- parent of range (upstream base): `c28afbbae` — repository has 2574 commits total
- parallel branch: `exp/reverse-text-pipeline` (7 experiment commits, E01)
- freeze tag: `research-p8c-final` -> `a5975ac74eb8cba6aefc1965f1422b4cef2b4ddc`

## Freeze commit

- hash: `a5975ac74eb8cba6aefc1965f1422b4cef2b4ddc`
- parent: `b257519feb4432d7f0a34179597aac2ec63cc702`
- diff vs parent: `tools/swe_lab/runs/swe_8c_expanded.md` only (+65 / -55)
- date: 2026-10-06T06:16:43+08:00 — author Thy985
- meaning: this is an **experiment freeze point, not a "latest code" marker**.
  Everything below it is Phase 8C's final state; later commits may modify code
  without disturbing Phase 8C reproducibility.

## Head at archive time (working tree)

- head: `83c990b000c22dbeb719d6330b6bb9809f27c664`
  (`chore: commit tier4/tier5 materialized fixture dirs and .python-version`)
- tracked modifications: none
- `research/` is the archive itself and is committed as the archive commit,
  not left untracked
- untracked at archive time: `=75` (a shell redirect accident, inert),
  `dsh-session/`, `scan_sp.py`, `subagents/` — tooling, not evidence
- raw data is **not tracked**: `outputs/` is in `.gitignore` (line 10);
  `git ls-files outputs` = 0 files. Run evidence survives only in the working
  tree, which is why `01_raw/manifest.tsv` hashes every run directory.

## Environment

- kernel: `Linux 6.18.33.2-microsoft-standard-WSL2 x86_64 GNU/Linux`
- python: 3.14.4 — uv 0.12.19 (x86_64-unknown-linux-gnu)
- hardware: single workstation, RTX 4060-class GPU, 11 GB RAM (~10 GB free),
  ~916 GB free disk — this constraint is load-bearing, not incidental:
  it is why E01 went LoRA and why RL / large distillation were never attempted.
- no Docker anywhere (WSL + Windows host). Real SWE verification therefore runs
  in-filesystem: `prepare.py` clones the repo at base commit, `verify.py`
  applies the oracle test patch to a host-side copy and runs F2P/P2P under
  `SWE_REAL_PY=/tmp/swe_deps/django_env/bin/python`.

## Reproduction entry points

- `uv run eval @ tools/swe_lab/eval_real_<arm>.toml --run.name <tag> -c 1 --clean`
  (wrapper `tools/swe_lab/run_swe_eval.sh`; sources `.env`, sets `DUMMY_API_KEY`,
  `PYTHONPATH`, `SWE_REAL_PY`; **`--no-sync` is required** — commit `6315a6e06`)
- model endpoint: `http://172.20.208.1:20128/v1` (dots3 = `9router/dots3-note-prev`)
- environment switches: `SWE_LAB_PHASES`, `SWE_LAB_GATE`, `SWE_LAB_BANNER`,
  `SWE_LAB_BANNER_ROLE`, `SWE_LAB_BUDGET` — see `06_artifacts/code_map.md`
- one config comment in `eval_real_8_hReplay.toml` names the file
  `eval_real_8_hReplay.toml.toml`; the run used the correct single extension
  and the numbers are unaffected (F15).