# Hypothesis Ledger

Every hypothesis raised, who raised it, what was run to test it, and what
happened. Rejected entries are kept — they are the archive's main payload.
Provenance: "user" = stated in a chat prompt (`05_process/hypothesis_origin.md`
keeps the prompt IDs), "ai" = proposed by the assistant and acted on, "data" =
emerged from measurement.

| ID | Hypothesis | Raised | Tested by | Outcome | Status |
| --- | --- | --- | --- | --- | --- |
| H01 | Reverse-text RL reward shapes a transferable capability | user, P0 | V1/V2/V3 reward ablation + held-out eval | "reward rises and transfers" and "every reward destroys the capability" both wrong — protocol bug, then optimiser artifact | **rejected (retracted)** |
| H02 | The audited verifier is trustworthy enough to reward against | user, P1 | Golden Episode + replay of a saved trace | Acceptance held; replay reproduced the reward | **supported** |
| H03 | A graded difficulty ladder separates behaviour | data, P2 | Tier 1–5 ladder + audits | Tiered headroom existed (12.5%–100%), but Tier 3's cliff was partly endpoint error, and Tier 5 did not de-saturate H_A | **partly rejected** |
| H04 | Harness effect = removing the edit tool (action affordance) | user, P3 | A vs B (−44pt), then A/B/C at n=32 | B confirmed a large effect; **C's claim reversed at n=32** and was retracted | **partly rejected** |
| H05 | Staged runtime (H_D) is a better *planner/executor* architecture | user, P4 | 120 episodes of traces | Planner turns that wrote a real plan: **0/120**. Framing retired; intervention is staged action allocation | **rejected (renamed)** |
| H06 | Phase gating alone carries most of H_D's gain | user, P4 | H_F attribution control | Phase prompts carry most of the tier3 gain; gating helps tier4 only | **narrowed** |
| H07 | Harness-produced trajectories can be distilled into a small policy | user, P4 | 3 contamination-free SFT views; eval under bare H_A | 0/10 tool calls untrained, 0/10 after LoRA SFT; 0/10 resolve. "The student got the teacher's text and did not get the teacher's harness." | **route rejected** |
| H08 | H_D > H_A generalises beyond the 5-instance pilot | data, P5 | Budget sweep + wide 20-instance set + second model | Direction generalised; **magnitude did not**: T=8 gap = −6pt, wide set +10pt vs pilot +32pt | **narrowed** |
| H09 | Static behaviour prose is the active ingredient | user, P5 | H_A-prime: same prose as a static system segment | 1/16 (H_A-prime) vs 2/16 (H_A) vs 7/16 (H_D) — static prose recovers none of the gap | **rejected** |
| H10 | H_D's gain is budget-independent | data, P5 | T ∈ {2,4,6,8} | Gap peaks at T=4 (+32pt), vanishes/crosses at T=8 (−6pt); H_A self-discovers verify+repair at T=8 | **rejected** |
| H11 | Affordance gating is the mechanism behind H_D | user, P6 | 2×2 prompt × gate (H_A/H_P/H_G/H_D); H_ADAPT scheduler | H_P (banner, no gate) = H_D 25%; H_G (gate, no banner) = 1/20. **Gating falsified at a signal-bearing budget.** Also: H_ADAPT never beats H_D; recon-2 tax | **rejected** |
| H12 | Repeating the phase context every turn carries the effect | user, P7 | H_ONCE vs H_NEUTRAL vs H_ACTION vs H_P (dots3, wide-20, T=6) | H_A 0%, H_ONCE 5%, H_NEUTRAL 5%, H_ACTION 15%, H_P 25% — recency necessary; neutral status inert; content secondary | **supported** |
| H13 | Message role is load-bearing | user, P7 | H_SYS (system role) vs H_P (user role), same text and cadence | H_SYS 15% vs H_P 25% — role is load-bearing, but this shows *system-role ≠ user-role*, not that interruption is causal | **supported (claim narrowed)** |
| H14 | Injection cadence/position is a further independent dimension | data, P7 | H_PHASE vs H_ACTION vs H_P | "Content and cadence each worth half, they do not substitute"; content 5%→15%, cadence 15%→25% | **supported** |
| H15 | Phase-boundary timing is a fourth load-bearing dimension | user, P8B | H_REPLAY (3 injections at turns 1/3/5) vs H_P | n=20: H_REPLAY 15% vs H_P 25% → **revised at n=60: H_REPLAY 17% > H_P 13%, p=0.77. Timing is NOT a real dimension.** | **rejected (revised)** |
| H16 | The banner effect survives replication at n=60 | data, P8C | 4 arms × 3 seeds × 20 tasks | **H_P 25% was single-seed noise** (seed-2 rerun 0/20). banner-vs-no-banner survives (p=0.031); multiple-vs-single injection survives (p=0.008) | **partly rejected** |
| H17 | The banner changes action allocation, not reasoning | user+data, P8C | Paired analysis + trajectory mediation | state_chg 0.04→0.07 (0.17→0.30 on solved-only); n_calls flat; first_edit not earlier; inspect_run_max ↓. Confirmed | **supported (current)** |
| H18 | The effect replicates across models | user, P8A | bunny / DeepSeek-v4-flash cross-model arms | **Blocked by provider, not by hypothesis**: bunny provider down then abandoned, DeepSeek-v4-flash never run. Claim stays untested | **untested (blocked)** |

## The ledger's shape

Ten of eighteen hypotheses were rejected, narrowed, or revised by their own
experiments. The two that survived untouched (H02, H12 in its narrow form) are
cheap controls. The most valuable entries are the rewrites: H05 (naming),
H10 (magnitude), H11 (mechanism), H15 (dimension), H16 (single-seed overclaim).