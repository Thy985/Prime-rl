# Hypothesis Origin

Which hypotheses came from the human, which from the assistant, which from
measurement. Prompt IDs are message IDs from the main session export; they
resolve in `01_raw/ai-sessions/dsh-session/session.v4.jsonl`.

## Human-authored (the user wrote the directive)

| H | Origin prompt | What the user did |
| --- | --- | --- |
| H01 | (pre-archive, branch `exp/reverse-text-pipeline`) | Reverse-text ablation design |
| H02 | seq=173 / id=`0c79a58a` (10-02 17:26) | Required the measurement fix **before** opening the gate for H_D |
| H05 → retracted | seq=1153 / id=`da1022df` (10-02 20:27) | "H_D 的提升已经有因果证据，但还没有证明 Planner/Executor 架构本身有效" — the user retired the naming on 0/120 trace evidence |
| H07 | seq=1688 / id=`d04e400b` (10-02 22:06) | Defined Phase 4's objective so the distillation result would be attributable |
| H08 | seq=2015 / id=`4467083f` (10-03 09:04) | Stopped SFT; required cross-model replication + attribution before real SWE |
| H09 | seq=6259 (10-05 08:38) | Set up the 2x2 so prompt and gate could be separated |
| H11 | seq=6259 / id=`a21206db` (10-05 08:38) | Defined Phase 6 as adaptive runtime control, not more fixed harnesses |
| H12 | seq=6259 | Named the banner as the object of study after gating was falsified |
| H13 | seq=7677 / id=`17795841` (10-05 19:17) | "立刻停止研究 affordance scheduling"; renamed the mechanism to per-turn control-plane signaling |
| H15 | seq=8292 / id=`029cc0a3` (10-05 21:38) | Converged the Phase 7 conclusion; Phase 8 = cross-model first, then n |
| H18 | seq=8372 / id=`070bf280` (10-05 21:48) | "那换其他模型可以吗" |

## Human stop orders

| Prompt | Stop |
| --- | --- |
| seq=5233 / id=`292b9f98` (10-04 19:36) | Freeze Phase 4 as "current route rejected"; Phase 5 = Harness Generalization; **no RL, no machine hunting, no scaled-up distillation** |
| seq=6259 (10-05 08:38) | No more fixed-harness variants |
| seq=7677 / id=`17795841` (10-05 19:17) | Stop affordance scheduling research immediately |
| seq=8292 / id=`029cc0a3` (10-05 21:38) | "不要直接写成 'harness 必须中断模型'" |
| seq=8872 / id=`02350fc3` (10-06 06:07) | Terminate all bunny tasks |

## Assistant-proposed and adopted

- H14 (content and cadence as independent, non-substitutable levers) — emerged
  from the injection-count correction, adopted and written up.
- H16 (the banner effect survives replication) — framed as the replication
  question; the answer partially falsified it.
- H17 (action allocation, not reasoning) — jointly reached: the mediator
  (`n_calls` flat while the action distribution shifts) was identified by the
  user, the chain was measured and confirmed by the assistant at n=60.

## Assistant findings the user rejected or narrowed

- "Harness must interrupt the model" — rejected as a claim (seq=8292). Replaced
  by "user-turn runtime intervention".
- H05's own framing — rejected by the user on trace evidence (seq=1153).
- The Phase 6 premise (adaptive control is the open question, seq=6259) was
  discarded inside the same phase by the 2x2 result.

## Two honesty notes

1. **The user authored the research strategy, in first person, at length.** The
   strategic prompts above are not short commands; they are multi-paragraph
   arguments that name the hypothesis, the falsification risk, and the next
   control. Every "decision" in `decision_log.md` was made by the user, not by
   the assistant. The assistant's contribution was execution, measurement, and
   the willingness to be corrected.
2. **Whether some of those paragraphs were AI-drafted and pasted back cannot be
   determined from the session.** The sessions preserve the message and its
   `role`, not its provenance. This is a limitation of the evidence, not a
   guess, and it is recorded rather than resolved.

## What the sessions cannot do

They cannot establish a result. They establish intent. Every claim in
`claim_evidence_matrix.md` resolves to a run directory or a commit, never to a
prompt.