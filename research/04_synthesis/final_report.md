# Agent Runtime Intervention Research

**Freeze:** `research-p8c-final` = `a5975ac74` (Phase 8C, n=60, 2026-10-06)

> A repeated user-role runtime injection of phase context changes **how an agent
> allocates its actions**, and that change improves the outcome at a small
> budget. It does not change reasoning, and it does not add interaction effort.

That sentence is the ceiling of what this work supports. Everything below shows
how we got there, and what had to be dropped along the way.

## 1. Research question

Does intervening at runtime on a fixed agent — with a fixed model, a fixed
budget, a fixed tool set — change the outcome, and if so, through what?

The question was framed after the first real result appeared. Before that there
was no question, only a suspicion that a harness could help.

## 2. Initial hypothesis

*Tool availability is the lever.* The first harness comparison removed the `edit`
tool and lost 44 points. That seemed to answer the question. It did not.

The working hypothesis was revised five times, and the final one is different in
kind from the first: it is about *signalling* rather than *access*.

## 3. Experimental environment

- **Model:** `9router/dots3-note-prev`, served at `http://172.20.208.1:20128/v1`,
  temperature 0.0. One second model (`space-bunny-alpha`, 7B) completed a
  pilot-tier replication.
- **Task set:** SWE-bench Verified, first a gated 5-instance django pilot, then a
  wide 20-instance set across django and sympy.
- **Verifier:** containerless and self-built — this box has no container runtime,
  and every built-in harness declares `NEEDS_CONTAINER = True`. `prepare.py`
  clones the repo at the base commit; `verify.py` applies the oracle test patch
  to a host-side copy and runs F2P / P2P under a per-repo interpreter. A repair
  is a resolve iff all F2P and P2P pass and the tree is not tampered.
- **Budget:** `max_turns` swept over 2 / 4 / 6 / 8. T=6 was the working budget
  for E07 and E08.
- **Machine:** single workstation, RTX 4060-class GPU, 11 GB RAM. This is a
  constraint that shaped the study, not a footnote: it is why full-parameter
  training was abandoned for LoRA, why RL was never attempted, and why the
  distillation test used 20 SFT steps.

## 4. What we found

### 4.1 The harness effect is real but small, and it is budget-shaped

The pilot showed **+32 points** (H_A 2/16 = 12%, H_D 7/16 = 44%) and looked
conclusive. The wide 20-instance set reduced it to **+10 points**. A budget
sweep showed the gain peaks at T=4 (+32pt) and **crosses to −6 points at T=8**,
where the free agent self-discovers inspect → edit → test → repair.

The honest statement is: a runtime intervention buys a substantial advantage when
the budget is small, buys little when it is generous, and can cost something when
it is very generous. This is a property of *budget pressure*, not of the harness.

### 4.2 The gating hypothesis is dead

The obvious mechanism was affordance gating: the recon phase hides the `edit`
tool, so the agent cannot act until it has inspected. A 2×2 factorial tested it
directly.

- **H_P** — banner, no gate: **25%**
- **H_D** — banner and gate: **25%**
- **H_G** — gate, no banner: **1/20**

Adding the gate to the banner changed nothing. Adding the banner to the gate
changed everything. On the pilot grid, **H_P reproduced H_D exactly — 7/16 =
44%, the same instances.** Enforcement contributes nothing. The mechanism was
misnamed for one whole phase.

A deterministic adaptive scheduler (recon → execute → verify from observed calls)
also lost: it never beat the fixed schedule, it never fired its verify rule, and
it carried a two-turn recon tax that made first edit later.

### 4.3 The static-prose hypothesis is dead

Putting the same behaviour description into the system prompt as a static
paragraph recovered **none** of the gap: H_A-prime 1/16, H_A 2/16, H_D 7/16.
Instruction text is not a control signal. The same words, injected per turn, are
a different variable.

### 4.4 The banner is the mechanism, and it has three separable properties

Holding the model, task set, budget and tool set fixed and varying only the
per-turn injection (E07, single seed, n=20 per arm):

| Arm | Injection | Solve |
| --- | --- | --- |
| H_A | none | 0% |
| H_ONCE | once, turn 1 | 5% |
| H_NEUTRAL | neutral text, every turn | 5% |
| H_ACTION | action-oriented, every turn | 15% |
| H_P | full phase context, every turn | 25% |
| H_SYS | same text, **system** role | 15% |

Three independent levers: **repetition** (once 5% → every turn 15–25%),
**content** (neutral 5% → action 15%), and **role** (user 25% → system 15%).
Neutral status text is inert. The three properties do not substitute for one
another.

The role contrast is narrower than it sounds. It shows that system-role injection
is not equivalent to user-role injection. It does **not** show that interruption
is causal, and we do not claim that.

### 4.5 Replication halved the headline and killed one dimension

E07 had seven single-seed arms. Expanding to 4 arms × 3 seeds × 20 tasks (n=60):

| Arm | seed 0 (E07) | seed 1 | seed 2 | n=60 |
| --- | --- | --- | --- | --- |
| H_A | 0% | 10.5% | 10.5% | **7%** |
| H_ONCE | 5% | 0% | 5.9% | **3%** |
| H_P | **25%** | 0% | 15% | **13%** |
| H_REPLAY | 15.8% | 21.1% | 15% | **17%** |

- **H_P's 25% was single-seed noise.** Seed-1 reran at 0/20.
- **Injection timing is not a dimension.** H_REPLAY (injections at turns 1/3/5,
  same count, different position) scored **higher** than H_P: 17% vs 13%,
  p = 0.77.
- Two claims survived, and both are paired on the same instances:
  **banner vs no-banner, p = 0.031; multiple vs single injection, p = 0.008.**

The surviving statement is smaller than the original headline by roughly half.
This is the intended outcome of replication, not a failure of it.

### 4.6 The mechanism is action allocation, not effort

The trajectory mediation chain holds at n=60:

- State-changing action ratio: **0.04 → 0.07** overall, **0.17 → 0.30** among
  solved episodes.
- Total tool calls: **flat.**
- First edit: **not earlier.**
- Longest inspect run: **shorter.**

The agent does not do more work, and it does not start editing sooner. It
*redirects the same number of actions* — fewer redundant inspections, more
state-changing calls. That is action allocation.

## 5. Final mechanistic model

A staged runtime intervention injects phase context into the user role at each
decision point. This does three things and nothing else:

1. It makes the current goal current at every decision, not once at the start.
2. It is positioned as a user-role turn, which is not interchangeable with a
   system-role turn at this model.
3. It reallocates a fixed number of actions toward state-changing calls.

It does not change reasoning, does not add interaction effort, does not make the
agent act earlier, and does not make the agent verify. Verification was never
observed in either arm — the test suite was never run in 32 pilot episodes.

## 6. Evidence strength

| Claim | Evidence | Strength |
| --- | --- | --- |
| Banner vs no-banner improves solve | E08, McNemar p = 0.031, paired, n=60 | **strong** |
| Repeated injection beats single | E08, p = 0.008, paired, n=60 | **strong** |
| Gating is not the mechanism | E06, H_P = H_D, H_G at floor | **strong** |
| Static prose is not the mechanism | E05, H_A-prime 1/16 | **strong negative** |
| Effect is budget-shaped | E05, T=4 +32pt → T=8 −6pt | moderate |
| Effect is small on the wide set | E05, +10pt | moderate |
| Direction replicates on a second model | E05, bunny 19% vs 31% | moderate |
| Action-allocation mediation | E08, observational chain | moderate |
| Role contrast (system ≠ user) | E07, single seed n=20 | weak |
| Cross-model for the banner study | — | **no evidence** |

## 7. Failed hypotheses

| Hypothesis | Verdict | Why it mattered |
| --- | --- | --- |
| Reward shapes a transferable capability | Retracted twice | Produced the two protocol rules this study runs on |
| Tool availability is the lever | Retracted | 44 points from n=1; reversed at n=32 |
| H_D is a better planner/executor | Retracted | 0 of 120 planner turns wrote a real plan |
| Distillation transfers the effect | Route rejected | 0/10 tool calls, 0/10 resolve after SFT |
| The effect is budget-independent | Falsified | Crosses to −6pt at T=8 |
| Gating is the mechanism | Falsified | H_P = H_D with no gate |
| Static prose carries the effect | Falsified | 1/16 vs 7/16 |
| Phase-boundary timing is a dimension | Falsified | 17% > 13%, p = 0.77 |
| H_P is 25% | Overclaimed | 13% at n=60 |
| Cross-model replication | Untested | Provider failure; never resolved |

## 8. Limitations

1. **No container runtime.** The verifier is self-built and containerless.
   Results are not directly comparable to official SWE-bench harnesses.
2. **20 tasks, 2 repos, no stratification.** The task set is a convenience sample.
3. **n=60 is 20 × 3.** Power for a 13% vs 7% gap is thin; the significant
   results are paired McNemar, not independent-sample tests.
4. **Single model throughout.** The banner study never reached a second model.
5. **Observational mediation.** The allocation chain is measured on the same
   trajectories as the outcome, not controlled.
6. **Cross-model claims in earlier writeups are infrastructure facts**, not
   model facts. Provider outages and silent dependency-resolution failures were
   mistaken for model behaviour twice.
7. **The distillation negative is route-specific.** What was rejected is dots3 →
   Qwen3-0.6B at 20 SFT steps with no tool-format alignment, evaluated under
   bare H_A.

## 9. Reusable experimental method

These were not planned; they were extracted from the eight failures that each
cost a wrong conclusion.

1. **Verify the verifier first.** The audit found that a tampering repair scored
   1.000 while a genuine partial fix scored 0.571. No capability claim is made
   against an unaudited reward.
2. **Protocol invariance.** One serialisation, one verifier version across
   training, inference and evaluation. Comparing numbers from two protocols is
   how two of the first conclusions were lost.
3. **Establish a non-destructive update regime before reading an ablation.**
4. **One entry point per fact.** The experiment record is an index over the
   Episode, not a competing trace; if they disagree, the Episode wins.
5. **Replicate before naming.** Every mechanism claim was attempted at n=1 and
   every one of them was wrong or over-scaled.
6. **Pair on instances, not on rates.** The two claims that survived replication
   were both paired McNemar on the same 20 instances. The unpaired aggregate
   comparisons are what produced the overclaim.
7. **Separate infrastructure failure from subject failure.** Probe the endpoint
   directly before attributing anything to the model.
8. **Freeze the mechanism, not the number.** A freeze point is a reproducibility
   marker, not a "latest code" marker.

## 10. Future work

- **Cross-model replication of the banner study** — the single most valuable
  missing piece. The arms exist; the provider problem must be solved once.
- **More seeds, not more arms.** Four arms at n=60 is the right shape; the
  replication should continue on the same four arms.
- **Formal mediation.** Bootstrap or SEM on the allocation chain; it is the
  strongest non-outcome evidence and it is currently observational.
- **A second budget.** T=6 was chosen because it had signal. T=8 is where the
  effect vanishes, and that region has never been studied.
- **Task-family stratification.** Twenty instances from two repos is a
  convenience sample.
- **Tool-format-aligned distillation.** The distillation route was rejected, not
  the question. A student that already emits tool calls was never tested.

## Where the archive is

`00_index/` (this file's indexes) · `02_experiments/` (8 canonical records) ·
`05_process/` (decisions, failures, hypothesis origin, session index) ·
`06_artifacts/` (code map) · `01_raw/` (hashes and extracts)