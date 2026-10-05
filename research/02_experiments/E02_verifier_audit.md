# E02 — Verifier Audit: Golden Episode and Replay Acceptance

## Question
Is the reward itself trustworthy before any capability claim is made against it?

## Hypothesis
H02: the audited verifier is a valid reward source.
Provenance: user, P1 — "verify the verifier first" is lesson 2 of the E01
retactions, applied as a gate rather than a hope.

## Design
Two artefacts, both cheap, both load-bearing:
1. **Golden Episode** — a hand-checked episode whose trace, tree hashes, verdict
   and reward are recorded before any live run is allowed to run.
2. **Replay acceptance** — the same reward recomputed from an archived trace
   must reproduce the live value.

On top of these: a **difficulty ladder with per-tier audits** (P2), i.e. each
tier's instances are audited for whether the reward discriminates at all.

## Controlled variables
One verifier version for the whole study; task set frozen per tier; tree state
recorded as hashes so a repair can be diffed, not eyeballed.

## Arms
Golden Episode (oracle repair) | replay of a saved trace | per-tier ladder audit.

## Results
- The **environment contract + Golden Episode** closed before the first live run
  (`498fca529`).
- Real verifiers Episode built with the audited verifier as reward (`b2698922c`);
  the experiment record was derived from the verifiers episode index (`238881b10`)
  rather than from a second trace.
- **Executing-reward replay over a saved trace passed** — Phase 1B acceptance
  (`56a6c91d1`).
- The audit's headline finding: **"the test suite is green" is not a verifier.**
  Exit-code and raw-pass-fraction rewards pay a *tampering* repair 1.000 while a
  genuine partial fix scores 0.571.

## Interpretation
The structured verdict (`per_test`, `fixed_targets`, `regressions`, `tampered`,
`timed_out`) exists because the naive scalar did not. Every later metric dispute
in this archive (`4b6854707` on `2>/dev/null`, the WRITE_RE fix, the
conditional write-rate confusion) is a descendant of this audit.

## What this rules out
- Exit-code and raw-pass-fraction as rewards.
- Any capability claim made against an unaudited verifier.
- A competing experiment record that is not regenerable from the Episode.

## Limitations
The audit is per-tier and per-instance; it does not certify the verifier on
out-of-distribution repairs. Container runtime is absent on this box, so the
SWE verifier runs containerless (in-filesystem clone + host-side test patch).

## Evidence
- Commits: `86e9e8366`, `6cb65ffce`, `17d30dbcb`, `498fca529`, `feb213c32`,
  `b2698922c`, `238881b10`, `56a6c91d1`, `57e81c8af`, `98785493e`
- Code: `tools/swe_lab/contract.py`, `golden.py`, `replay_executing.py`,
  `terrain.py`, `index_episode.py`
- Spec: `tools/swe_lab/PLAN.md` §2.1 — the three tiers of fact
  (raw stream / semantic fact / index) and the rule that the Episode wins over
  any index that disagrees with it.
- Verifier source: `deps/verifiers` (0.3.2.dev137).