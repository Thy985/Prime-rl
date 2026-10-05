# Failure Ledger

Failures are first-class evidence. Each entry: what broke, how it was detected,
the correction, and the general rule it produced.

| ID | Failure | Detected how | Correction | Rule |
| --- | --- | --- | --- | --- |
| F01 | **Rewards can be gamed by tampering.** Exit-code and raw-pass-fraction rewards pay a tampering repair 1.000 while a genuine partial fix scores 0.571 | Per-tier audit of the terrain (`terrain.py`) | Structured verdict: `per_test`, `fixed_targets`, `regressions`, `tampered`, `timed_out` | "The test suite is green" is not a verifier. |
| F02 | **Holdout leakage in the reward ablation** | Held-out exact eval (`58996d1fb`) | Protocol contract: one serialisation, one verifier version across train / inference / eval | Protocol invariance is a precondition for any ablation. |
| F03 | **"Every reward destroys the capability" was an optimiser artifact** (lr 1e-4) | Re-running at a non-destructive lr | Retracted (`PLAN.md` sec. 0); ablation only at a non-destructive lr | Establish a non-destructive update regime before reading an ablation. |
| F04 | **"Reward rises and transfers" was a protocol bug** | Two slightly different facts either side of a boundary | Retracted (`PLAN.md` sec. 0) | Never compare two numbers produced by two different protocols. |
| F05 | **Tier-3 cliff was partly an endpoint error-rate artifact** | Repeated runs exposed error-rate asymmetry (`5ef3bf8ee`) | Endpoint error rate fixed; errored episodes excluded from the solve curve | A cliff must survive a failure-rate check before it is a cliff. |
| F06 | **Pooled rates from runs with endpoint contention** | Repeat runs (`b43c3f1d4`) | Repeat runs before pooling; 8 attempts per tier | Pooling hides contention; repetition exposes it. |
| F07 | **Reply-mode "empty reply is invalid" leaked into patch mode**, silently deleting the failures the budget had just created; tier3 read 33% instead of 12.5%, tier1 read 5/5 instead of 5/8 | 18/40 episodes flagged `error` while stop-condition counts showed `{agent_completed: 11, max_turns: 29}` and **zero** errors | Rule split by mode: patch mode voids only a real error stop or a missing recorded reward | A classifier must not import validity rules from another mode. The only bug close enough to inverting a conclusion to matter. |
| F08 | **`WRITE_RE` counted `2>/dev/null` and `2>&1` as tree writes** | Manual trace check (`4b6854707`) | Regex narrowed to exclude `/dev/null` and `&` redirects | Every conditional write rate in this archive must be read *after* this fix. |
| F09 | **Harness C claim reversed at n=32** | Replication (`6a1177c45`) | Retraction committed; claim narrowed to "tool support is the effect" | No harness claim from n=1. |
| F10 | **Bunny provider failure mistaken for a harness / model failure** | Provider returned empty responses; smoke hung. Root cause was **not** the model: `uv sync` failed silently on `deep-ep==1.2.1` metadata for aarch64, so the eval subprocess never launched | `--no-sync` added to the wrapper (`6315a6e06`); bunny smoke then completed in 50.9s with reward=1.0 | An infrastructure failure and a model failure look identical in the harness log. Probe the endpoint directly before blaming the subject. |
| F11 | **H_P = 25% was single-seed noise** | Seed expansion to n=60 (`a5975ac74`); seed-1 rerun scored 0/20 | 25% to 13% at n=60; earlier writeups must be read against this | A single seed at n=20 is not a result; it is a hypothesis. |
| F12 | **Conditional write rate (54% vs 25%) quoted from the pre-fix metric** in `swe_stage_conclusion.md` while `swe_harness_triangle.md` records the corrected figures | Cross-document comparison | Use the triangle's corrected figures whenever citing conditional write rate | When writeups disagree, the metric-fix commit, not the writeup, is authoritative. |
| F13 | **WSL `Path.glob` silently dropped matches** | A check that passed when it should not have (`1f89fc05b`) | Glob replaced with an explicit walk | On WSL, verify a glob with `find` before trusting its count. |
| F14 | **Cross-model replication never completed** | Provider unavailability (F10 lineage); user terminated (D18) | Recorded as untested (H18), not as negative | An untested claim must be filed as untested. Never as a negative result. |
| F15 | **Config comment typo: `.toml.toml`** — the documented command in `eval_real_8_hReplay.toml` names the file `eval_real_8_hReplay.toml.toml` | Dry-run of the reproduction command while assembling the archive | Recorded here; the run used the correct single extension, so the numbers are unaffected | A comment is a contract. A typo in a reproduction command costs the next reader a failed first attempt and an hour of suspicion. |

## Three structural notes

- **F01 through F08 and F13 are instrument failures, not science failures.** The
  largest single distortion in the archive (F07) was close to inverting a
  conclusion about whether a budget creates headroom. Measurement work precedes
  mechanism work.
- **F09 and F11 are the only replication failures, and the only failures that
  changed a headline number.** Everything else changed an interpretation, or
  (F15) would have cost the next reader an hour.
- **F10 is the only failure that cost a whole study leg.** The bunny provider
  issue was diagnosed correctly twice, fixed once, and still abandoned on
  schedule grounds. The cross-model question remains open.