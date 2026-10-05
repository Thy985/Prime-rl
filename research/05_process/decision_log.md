# Decision Log

Each decision records the prompt that triggered it (message IDs and timestamps
are in `ai_sessions_index.md`), the state it resolved, and the consequence.
Decisions that turned out to be wrong are kept and marked.

| ID | Date | Decision | Triggered by | State resolved | Consequence |
| --- | --- | --- | --- | --- | --- |
| D01 | 10-02 17:26 | Fix measurement bug #8 **before** opening the gate for H_D | User reported the headroom table + the 8th measurement bug | "Budget binding has no effect" — a false negative produced by the instrument | Gate opened; H_D built on a trustworthy measure. Commit `6004a7559`. |
| D02 | 10-02 17:57 | Do items 1 and 2, then start writing H_D | User: "把 1、2 做掉并开始写 H_D" | Whether to begin H_D | Harness D implemented the same day. |
| D03 | 10-02 20:27 | **Retire the "planner" framing** | Trace evidence: planner turns that wrote a real plan = 0/120 | Whether H_D's gain implied a planner architecture | Renamed to staged action allocation. Commit `7cdbc5980`. Prevents the "planner/executor works" misattribution. |
| D04 | 10-02 21:46 | Enter Phase 4 as **trajectory distillation**, not "learn the H_D harness" | User directive | What Phase 4 should claim | The later negative result is attributable to a well-posed question. |
| D05 | 10-03 09:04 | **Pause SFT.** Do cross-model replication + attribution first, then real SWE | User directive | Whether to keep training | Preserved a clean harness study. SFT reopened only as a small verification (D09). |
| D06 | 10-03 19:54 | Try `openrouter/stealth/space-bunny-alpha` as the second model | User suggestion | Which model has headroom | Reproduces the effect (+12pt). Later became the repeatedly failing provider (F10). |
| D07 | 10-03 23:06 | Proceed to a small real SWE-bench set | User: "进行真实 SWE-rebench 少量任务" | Whether to leave the lab | Containerless verifier pipeline built (`14c2b34e6`). |
| D08 | 10-04 08:28 | **Top up n before deciding** | User: "先补 n 再决策" | Whether to conclude from the pilot | 11066/11206 brought to 5 eps/harness; gives the honest +32pt pilot number. |
| D09 | 10-04 08:46 | Run **one** small distillation verification | User: "做一次小规模 distillation 验证" | Whether the SFT pause was permanent | Produced the cleanest negative result in the archive (`1df2989df`). |
| D10 | 10-04 19:36 | **Freeze Phase 4 as "current route rejected"**; Phase 5 = Harness Generalization; no RL, no machine hunting, no scaled-up distillation | User directive | What Phase 4 means; what not to do next | Prevented turning a mechanism study into a training project on an 8GB box. |
| D11 | 10-04 20:34 | Prioritise three sub-studies: H_A-prime control, budget sweep, external validity | User's ordering | Which controls matter most | H_A-prime killed the static-prose explanation cheaply; the budget sweep killed budget-independence. |
| D12 | 10-05 08:38 | **Phase 6 = adaptive runtime control**, not more fixed harnesses | User directive | Whether fixed harnesses were worth extending | The 2x2 falsified gating. Phase 6's real output was a disproof. |
| D13 | 10-05 19:17 | **Stop researching affordance scheduling.** Rename the mechanism to per-turn control-plane signaling; Phase 7 = banner decomposition | H_G / H_ADAPT negative evidence | The mechanism name | Directly produced E07, which found the repetition / role / content structure. |
| D14 | 10-05 21:12 | Fix the Phase 7 objective: dots3 + wide-20 + T=6, vary only the banner, trajectory metrics first-class | Goal set | What E07 must isolate | The banner became an independent, measurable variable. |
| D15 | 10-05 21:38 | Converge the conclusion; **do not claim "the harness must interrupt the model"**; Phase 8 = cross-model first, then n | H_SYS result | How far to push the role claim | Terminology settled; prevented a causal claim E07 could not support. |
| D16 | 10-05 21:48 | Look for an alternative model to bunny | User: "那换其他模型可以吗" | Which model for replication | DeepSeek-v4-flash identified; never actually run. |
| D17 | 10-05 22:42 | **Two parallel subagents**: one fixes bunny harness compatibility, one runs Phase 8C | User directive | Whether to serialise the work | Correct call. Phase 8C completed; the bunny fix worked but was later abandoned (D18). |
| D18 | 10-06 06:07 | **Terminate all bunny tasks** | User: "bunny 这个模型不能用了，相关任务终止吧" | Whether to keep chasing the cross-model leg | Cross-model stays untested (H18). E08 frozen as `research-p8c-final`. |

## Pattern

Seven decisions were framed as *stopping* something (D03, D05, D10, D13, D15,
D17, D18). The archive's most valuable entries are those stops, because each was
made while the attractive alternative was still in hand: keep calling it a
planner, keep training, extend the fixed harness, keep chasing a model that does
not respond.

Two entries are wrong in retrospect. D12 took as its premise that adaptive
runtime control was the open question, and the same phase's 2x2 result discarded
that premise. The single-seed conclusions carried out of E07 were not flagged at
all; D17/D18 did not foresee that the point of the replication would be that
those numbers themselves were the failure.