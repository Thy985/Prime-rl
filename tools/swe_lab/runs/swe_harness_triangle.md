# H_A' : how much of the harness effect is the instruction text?

The real-SWE pilot measured a 32-point gap (H_A 2/16 = 12%, H_D 7/16 = 44%) but
H_D differs from H_A in two entangled ways at once: (i) it injects per-phase
instructions and (ii) it enforces them at runtime -- the edit tool is absent in
recon, commands that change the tree are refused there, and each early phase is
capped. H_A' separates the two: the same free bash+edit loop, the same 4-turn
budget, the same system prompt as H_A, plus ONE static paragraph carrying the
behavioural content of the three phase prompts (inspect -> edit early -> verify).
No phase numbering, no gating, no tool removal. The config is byte-identical to
eval_real_hA.toml apart from comments; the taskset appends the paragraph when
SWE_REAL_H_A_PRIME=1 (tools/swe_lab_env/swe_bench/taskset.py).

Same 5 gated django instances and the same episode grid as the pilot (5x2 plus a
2-task x3 topup = 16 episodes per arm), same model (dots3-note-prev), -c 1.
Injection verified in the recorded traces: system_prompt length 724 with the
paragraph present, 428 without.

## The triangle

| harness   | free loop | static behaviour text | runtime gating | resolve |
|-----------|-----------|-----------------------|----------------|---------|
| H_A       | yes       | no                    | no             | 2/16 = 12% |
| H_A'      | yes       | yes                   | no             | 1/16 = 6%  |
| H_D       | no        | yes (per phase)       | yes            | 7/16 = 44% |

## What the behaviour profile says

| harness | no_write | calls (unsolved / solved) | top unsolved sequence |
|---------|----------|---------------------------|----------------------|
| H_A     | 57%      | 3 / 4                    | `inspect inspect inspect inspect` x8 |
| H_A'    | 47%      | 4 / 4                    | `inspect inspect inspect inspect` x6 |
| H_D     | 33%      | 3 / 3                    | `inspect inspect inspect inspect` x2 |

Conditional on the episode writing anything at all, resolve is H_A 2/8 = 25%,
H_A' 1/9 = 11%, H_D 7/13 = 54%. So H_D helps twice: more episodes reach a write
(13 vs 8-9 of 16), and writes that happen are about twice as likely to land.

## Two findings worth keeping

**The instruction text is not the mechanism.** H_A' does not recover any of the
gap (1/16 vs 2/16 is noise at this n), and its dominant failure is still the
all-inspect episode. Worse, the paragraph's own wording ("first spend a turn or
two with bash locating the code that matters") is what a model already prone to
inspecting needs least: the static text reinforces inspection rather than
converting it into an edit. Behavioural advice delivered as prose cannot move an
agent whose failure is that it never stops reading.

**The real-SWE gain is not test-driven either.** test_after_edit is 0% in all
three arms: no episode in any arm -- including H_D, whose phase 3 says "re-run the
failing tests" -- ever invokes `tests/runtests.py`. This confirms the pilot's
"0 test-suite runs in all 32 episodes" across a third arm and pins the mechanism
more tightly than the toy-terrain profile did. On the tiers, H_D's gain was
attributed to the verify turn; on real SWE that turn never fires, so what remains
is the write discipline: a bounded recon turn followed by turns that can and must
edit. The gating does not merely suggest editing, it removes the option of not
editing (the edit tool is simply not there in recon), and a model that never
writes cannot pass.

## Consequence for the program

The causal story is now: **runtime-enforced structure > static instruction**, and
the pilot's +32 points are attributable to the enforcement, not to the prompt
wording. This is why the Phase 4 route failed for an additional reason worth
recording: SFT on the teacher's conversation can at best teach prose that mimics
the guidance. The part that produced the effect -- being unable to spend a turn
without editing -- is a property of the harness, and a 0.6B student that emits no
tool call at all never experiences it.

Follow-ups in priority order: the budget sweep (does the gap live only at low
budget?), more real-SWE tasks, and a second model on real SWE.

## Reproduce

    SWE_REAL_PY=/tmp/swe_deps/django_env/bin/python SWE_REAL_H_A_PRIME=1 \
    bash /tmp/run_swe_eval.sh tools/swe_lab/eval_real_hA_prime.toml \
      --run.name rl-hAp -c 1 --clean
    # same, plus: --run.name rl-hAp-topup -c 1 --clean -n 2 -r 3

    uv run python tools/swe_lab/behavior_real.py \
      --pattern "H_A=outputs/rl-hA" "H_A=outputs/rl-hA-topup" \
               "H_A'=outputs/rl-hAp*" \
               "H_D=outputs/rl-hD" "H_D=outputs/rl-hD-topup"
## Mechanism, turn by turn

`tools/swe_lab/gating.py` reads the recorded traces and asks what the runtime
actually did, rather than what the prompts said. Two things fall out, and one of
them corrects the pilot's earlier reading of the mechanism.

**Which tools were on the table.** In the recon request the tool list carried by
the API call is `[bash]`; the edit tool is not merely discouraged, it is absent.
From the execute phase on the list is `[bash, edit]`. So H_D is not a prompt that
asks for edits -- it is a turn whose affordances contain no way to edit, followed
by turns whose affordances do. Across the 16 pilot episodes: 32 recon turns all
bash-only, then 16 execute and 16 feedback turns all with edit available.

**The bash write refusal never fired.** The planner refuses tree-changing bash in
the recon phase, but the recorded refusal string (`writes are not allowed in this
turn`) appears **0 times** in 48 episodes. On real SWE the model does not try to
patch the file with `sed`/`patch`/`>` during recon; it runs `find .` (24x) and
`git log` (4x). So the load-bearing part of the enforcement is the tool
availability, not the command filter. (An earlier pass of this probe "found" 5
refusals; those were false positives from loose keyword matching against file
contents the agent had catted back. The matcher is now the exact refusal string.)

**At the 4-turn budget, instructions to verify are not obeyed.** The feedback
phase says "Re-run the failing tests and read the output. Repair what is still
failing." In 16/16 feedback turns the model ran **no test at all**: 7x `cat -n`,
4x `grep -rn`, 1x `sed -n`, 1x `cat`. Zero `runtests.py`, zero `pytest`, in any
arm at T=4. The same agent that never verifies when told to verify is the one for
whom a static paragraph about verifying (H_A') does nothing. Instruction-level
control of this agent is inert at low budget; affordance-level control is not.
(The budget sweep shows this changes: at T>=6 H_D runs tests in feedback, at T=8
both arms verify -- see swe_budget_sweep.md.)

**Edits per episode, by harness:**

| harness | acts | edit calls | edits per episode |
|---------|------|-----------|-------------------|
| H_A + H_A' | 127 | 4 | 0.13 |
| H_D | 41 | 7 | 0.44 |

H_D produces ~3.5x more edits per episode from the same model and the same tasks.
That, rather than any difference in what the model was told, is the mechanism the
+32 points rides on.