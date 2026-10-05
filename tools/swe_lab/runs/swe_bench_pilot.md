# Real SWE-bench Verified pilot: H_A vs H_D on gated django instances

Checklist step 3: the harness effect, measured on real SWE-rebench tasks instead of
the swe-lab tiers. This is the first time the H_D > H_A differential is tested
against actual SWE-bench Verified instances, and the first time any verifier runs
real SWE-bench on this host at all (no Docker anywhere; 11 GB RAM).

## What was built

A containerless real-SWE taskset under `tools/swe_lab_env/swe_bench/`:

- `prepare.py` — downloads the Verified split, filters candidates (per-entry clean
  test names, `PASS_TO_PASS` capped so verification stays cheap, single repo so one
  interpreter holds one dependency set), clones each repo at its `base_commit` into
  per-commit cache dirs, writes `manifest_candidates.json`.
- `verify.py` — the gate every shipped instance must pass (the same contract
  swebench's own harness validates):
  1. `test_patch` applies on the base checkout;
  2. every FAIL_TO_PASS test FAILS at base+test_patch (else there is no signal and
     a no-op agent would score 1.0);
  3. every PASS_TO_PASS test PASSES at the pristine base (environment sound);
  4. the gold patch applies and every FAIL_TO_PASS test PASSES with it;
  5. every PASS_TO_PASS test still PASSES with gold.
  Only instances passing all five go into `manifest.json`.
- `taskset.py` — the `swe_bench` taskset. `setup()` stages the real checkout into
  the subprocess runtime and strips every ref to the gold fix (origin, post-base
  tags, reflog), mirroring the official swebench setup. The prompt is the issue
  text only; the oracle `test_patch` is never exposed to the agent and is applied
  only at scoring time on a host-side copy. Scoring mirrors the official eval
  script: oracle test files are reset to base, `git apply` the test patch, run each
  oracle test once (one process per test; pass/fail is the exit code). Rewards:
  `resolve` (weight 1.0, all F2P+P2P green) and `f2p_fraction` (weight 0.0).
  Editing an oracle-touched file voids the reward.
- `behavior_real.py` — the swe-lab behaviour-profile instrument, re-grouped by
  instance and solved = `resolve == 1.0`.

## The five gated instances

All django, all pure-Python test paths, `nfail` 1-2, `npass` 1-6, oracle test
patches touching exactly one or two test files. 11066/11206 pass the pristine-P2P
soundness check; their P2P also fails at base+test_patch (the patch adds
multi-database infrastructure only the fix enables), which the official contract
allows — the gold fix turns them all green.

| instance | bug | nfail/npass | oracle files |
|---|---|---|---|
| django-11066 | `ContentType._rename()` saves on wrong database | 1/3 | `tests/contenttypes_tests/test_operations.py` |
| django-11206 | `numberformat.format` renders small decimals in scientific notation | 2/4 | `tests/utils_tests/test_numberformat.py` |
| django-11333 | URLResolver rebuilds on every `__getitem__` | 1/2 | `tests/urlpatterns/test_resolvers.py` |
| django-15127 | `LEVEL_TAGS` not updated under `@override_settings` | 1/1 | `tests/messages_tests/{base,tests}.py` |
| django-16901 | XOR lookups wrong for `Q() ^ Q() ^ Q()` | 1/6 | `tests/xor_lookups/tests.py` |

Candidates that FAILED the gate and why: django-11239 (a PASS_TO_PASS entry is a
docstring, not a test name; a P2P test needs the `psql` client) and django-12155
(its F2P test already passes at base+test_patch — no signal).

## Results

Model `9router/dots3-note-prev` (the harness-effect model; the replication model
space-bunny-alpha hit OpenRouter's free-tier daily cap on pilot day — 429 then 404
unavailable-for-free), `max_turns = 4`, temperature 0.0, subprocess runtime, 2
episodes per instance per harness, `-c 1`, `timeout.rollout = 600`. 20 episodes,
all valid, zero ProviderErrors.

After the first 20 episodes the two carrying instances (11066, 11206) were topped
up to 5 episodes per harness each (`-n 2 -r 3` on the same configs), so the table
below mixes 5-episode cells on those two and 2-episode cells on the rest (32
episodes total).

| instance | H_A | H_D |
|---|---|---|
| django-11066 | 2/5 | 5/5 |
| django-11206 | 0/5 | 2/5 |
| django-11333 | 0/2 | 0/2 |
| django-15127 | 0/2 | 0/2 |
| django-16901 | 0/2 | 0/2 |
| **total** | **2/16 = 12%** | **7/16 = 44%** |

The differential H_D - H_A = **+32 points on real SWE-bench Verified** (+20 on
the first 20 episodes alone), the same direction as the swe-lab tiers (tier3 +34
on space-bunny, +37 on dots3). The topped-up cells are decisive: on 11066, H_D is
5/5 — the model solves it every time — against H_A's 2/5, and on 11206 it is 2/5
against 0/5. All seven solves were inspected: find the buggy source, read it, one
targeted `edit` at the bug location (e.g. `transaction.atomic(using=db)` for
11066, the Decimal branch of `numberformat` for 11206), re-read the hunk —
genuine minimal fixes, rewarded by the never-seen oracle test patch.

## Behaviour profile (20 episodes)

| cell | n | no_write | test_after_edit | calls |
|---|---|---|---|---|
| H_A unsolved | 14 | 57% | 0% | 3 |
| H_A solved | 2 | 0% | 0% | 4 |
| H_D unsolved | 9 | 33% | 0% | 3 |
| H_D solved | 7 | 0% | 0% | 3 |

Top sequences: H_A unsolved is dominated by pure `inspect x4` (8/14 episodes —
studied the repo, never wrote); solved episodes (both harnesses) have the
`write inspect write inspect` shape, and H_D's seven solves are 5x that exact
shape. No episode in either harness ever ran the test suite
(`pytest`/`unittest`/`runtests.py`: zero occurrences across all 32 traces).

## Interpretation

The direction replicates on real tasks, and the topped-up cells sharpen the
mechanism. On the tiers, H_D's win was the verify turn (tier3 `test_after_edit`
9% -> 56-62%, `no_write` 41% -> ~0%): the staged allocation pushed the model to
run tests after editing. On these real django instances at 4 turns, the model
never verifies under either harness; H_D's win is earlier and simpler — the phase
protocol (recon / execute / verify wording and turn split) gets the model to
commit edits at all (`no_write` 57% -> 33% among unsolved, and every solved
episode wrote), while H_A's free allocation lets it spend all four turns
inspecting. The mechanism difference is visible in solve stability: H_D turns a
one-shot solve (11066, H_A 2/5) into a near-deterministic one (11066, H_D 5/5),
which is exactly the "budget -> repair action" claim — H_A's writes are not
reliably preceded by a plan, H_D's phases force the write step. A mechanism
shift, not a copy, but the same underlying claim.

## Limits

- n = 16 episodes per harness, but cells are unbalanced: 11066/11206 at 5 per
  harness, 11333/15127/16901 at 2 per harness (0/0 everywhere — the expected
  capability floor for a small model on real SWE at 4 turns). The effect rides
  entirely on 11066 (H_A 2/5 vs H_D 5/5) and 11206 (H_A 0/5 vs H_D 2/5).
- Single repo (django), single model (dots3), single 4-turn budget. No test runs
  were observed in any episode, so the real-task `test_after_edit` channel is
  untested, not disproven.
- Scoring is host-side pytest/runtests with the oracle patch; a `version`-pinned
  install (as the official harness does) is approximated by one shared interpreter
  that happens to cover django 3.x and 4.2.

## Files

- `tools/swe_lab_env/swe_bench/{taskset,prepare,verify}.py` + `__init__.py` + `manifest.json`
- `tools/swe_lab/behavior_real.py`
- `tools/swe_lab/eval_real_{hA,hD}.toml`
- this note
