# E03 — SWE Micro Terrain: Difficulty Ladder, Audits, Budget Frontier

## Question
Does a graded task set actually separate the agent's behaviour — and does the
measurement survive contact with the endpoint?

## Hypothesis
H03: a tiered ladder with per-tier audits produces real, discriminating headroom.

## Design
- Tier ladder built and **audited per tier**, not assumed: tier 1/2 (easy),
  tier 3 (cliff), tier 4 (hidden configuration layer), tier 5 (stress).
- Per-tier audits record what the audit caught *in the tier itself* (tier 4 is
  named for exactly that).
- **Patch-mode taskset** added so harness comparisons could mean anything at all;
  patch-mode reporting surfaces recorded verdicts and real tool-call extraction.
- **Budget frontier**: per-tier budgets measured as a function of
  `max_turns`, with errored episodes excluded.

## Controlled variables
Same model, same verifier, same runtime across tiers; tier assignment recorded in
the record so tier-level aggregation is auditable; attempts repeated (8/tier)
before pooling.

## Arms
H_A (free bash + edit) across tiers 1–5, with and without a turn budget.

## Results
- Solve curve over 8 attempts per tier, errored excluded (`9142c2632`).
- **The tier-3 cliff was partly an artifact**: endpoint error rate had to be
  fixed before the cliff could be trusted (`5ef3bf8ee`).
- Repeated runs exposed **endpoint contention**; pooled rates were not yet
  trustworthy (`b43c3f1d4`).
- Tier 4 is a *hidden configuration layer* — the audit, not the solve rate, is
  the finding (`2755ba56f`). In patch mode, tool calls resolve where solve rate
  does not (`997935c9b`).
- **Tier 5 does NOT de-saturate Harness A** (`a56e6ae13`) — a negative result on
  the difficulty axis: adding difficulty did not open headroom.
- **A binding turn budget creates the headroom Harness A lacked — and a bug hid
  it** (`6004a7559`). This is the commit that made E04's comparison possible.

## Interpretation
The ladder's value is the audit trail, not the ranking. Two of the five most
valuable commits in this archive (`5ef3bf8ee`, `6004a7559`) are E03 measurement
fixes, not experiments.

## What this rules out
- Saturated baselines as experimental setups — Harness A has no headroom on
  tier 1/2 and on tier 5 without a budget.
- Pooled rates from runs with endpoint contention.
- Difficulty as a substitute for headroom.

## Limitations
Lab terrain, not real SWE. Tier construction is authored, so difficulty ordering
is an author's claim validated only by audit and solve rate. `no_write` (ended
without writing) had to be made a first-class outcome (`ee1466a8c`) before it
could be compared at all.

## Evidence
- Commits: `57e81c8af`, `9142c2632`, `5ef3bf8ee`, `b43c3f1d4`, `517bb2826`,
  `5d00b430e`, `2755ba56f`, `997935c9b`, `ee1466a8c`, `a56e6ae13`, `6004a7559`,
  `462d6a866`
- Code: `ladder.py`, `frontier.py`, `terrain.py`, `behavior.py`
- Artifact: `tools/swe_lab/frontier_budget.json`
- Analysis script: `analyze_matrix.py`
- Runs: `outputs/swe-lab-harnessA`, `outputs/swe-lab-harnessB-noedit`,
  `outputs/swe-lab-harnessC-patchfirst` (E04 arms also live here)