# E01 — Reverse-Text: Reward Ablation and Protocol Invariance

## Question
Can a learned capability be shaped by reward and survive a non-destructive
update, without the measurement instrument quietly rewriting the answer?

## Hypothesis
H01: reward shape controls a transferable reverse-text capability
(provenance: user, P0).

## Design
- Task: reverse-text on short strings; verifier = exact match.
- Two routes: LoRA SFT on a 0.6B base (capability build-up) and offline GRPO
  on a single GPU (RL plumbing: sampler → verifier → reward → advantage →
  LoRA → delta).
- Reward ablation, three variants at a **non-destructive** learning rate:
  V1 = lcs, V2 = pos, V3 = lcs + exact bonus.
- Evaluation protocol contract introduced alongside the ablation, so that
  training / inference / eval share one serialisation and one verifier version.

## Controlled variables
Model family and base size (0.6B), string length regime, learning rate held at a
non-destructive value, single GPU, offline (no environment interaction).

## Arms
Base (no training) | SFT | GRPO-V1 | GRPO-V2 | GRPO-V3.

## Results
- SFT built a capability: **0/18 → 7/18 exact** on short strings (verified).
- RL plumbing verified end-to-end on one GPU.
- Both headline conclusions are **retracted**:
  - "Reward rises and transfers" (Experiments A/B) — **RETRACTED: protocol bug.**
    Two slightly different facts on either side of the boundary led to protocol
    tinkering instead of measurement.
  - "Every reward destroys the capability" (lr 1e-4) — **RETRACTED: optimiser
    artifact.** The destruction was the learning rate, not the reward.

## Interpretation
Nothing here is a reward-shape result. E01's output is **methodological**: the
ablation was uninterpretable until the update regime was made non-destructive
and the protocol single-sourced.

## What this rules out
- Offline ordering/correlation metrics as predictors of learning.
- "Reward rises and transfers" as a claim from a run where the eval protocol
  differed from the training protocol.
- Any reward-ablation conclusion at a destructive learning rate.

## Limitations
Single task family (reverse-text), single base size (0.6B), single GPU, offline.
Not an agent study; the transfer value is entirely procedural.

## Evidence
- Commits (branch `exp/reverse-text-pipeline`): `8ce7e10f3`, `bc29623ca`,
  `58996d1fb`, `0dc6fc314`, `b03fe4557`
- Ledger: `tools/swe_lab/PLAN.md` §0 — the retraction table is the canonical
  record of E01's two retracted claims.
- Runs (not result evidence): `outputs/sft-*`, `outputs/short-ovf*`,
  `outputs/reverse_text_local`.
- Successors: the four lessons in `PLAN.md` §0 became the gate rules applied to
  E02 (verify the verifier first) and E05 (protocol invariance).