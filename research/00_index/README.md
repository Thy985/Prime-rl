# Research Archive — Agent Runtime Intervention on SWE Agent Behaviour

Freeze point: `research-p8c-final` = `a5975ac74eb8cba6aefc1965f1422b4cef2b4ddc`
(Phase 8C final, 2026-10-06, branch `exp/swe-verifier-terrain`).

This is an index over evidence, not a restatement of it. Raw material is never
edited here; every conclusion resolves to a path, a commit, or a hash.

## Three layers

| Layer | Contents | Mutation rule |
| --- | --- | --- |
| Raw evidence | `01_raw/` — git export, run dirs, traces, logs, AI sessions | **immutable**; verified by hash, not by hand |
| Normalized index | `00_index/`, `02_experiments/`, `05_process/`, `06_artifacts/` | canonical records, one per experiment/claim/decision |
| Narrative | `04_synthesis/` | argues from the index; cites IDs, never re-derives |

`03_analysis/` holds derived analysis (regenerable); `07_archive/` holds
superseded drafts. Neither is load-bearing for a claim.

## How to audit a claim

1. Read the claim row in `00_index/claim_evidence_matrix.md` -> note its ID.
2. Follow its evidence IDs to the experiment record in `02_experiments/E0X_*.md`.
3. The record points at config path, analysis script, run directory, commit.
4. Raw values live under `01_raw/runs/<run>/monitors/file/metrics.jsonl`
   (field `eval/swe-bench/effective/agent/pass@1`).
5. `01_raw/manifest.tsv` hashes every run directory at freeze time, so a run
   can be proven unchanged.

The one-line result and its ceiling:

> **repeated user-role runtime intervention -> action-allocation change ->
> outcome difference.** Not reasoning, not effort, not earlier action, and not
> general SWE competence.

Anything stronger is not supported. See "What we must not claim" in the matrix.

## Read order

`git_milestones.md` -> `experiment_registry.md` -> `hypothesis_ledger.md`
-> `claim_evidence_matrix.md` -> `04_synthesis/final_report.md`
-> `05_process/decision_log.md` and `failure_ledger.md`.