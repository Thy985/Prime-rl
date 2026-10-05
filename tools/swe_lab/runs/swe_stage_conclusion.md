# Stage conclusion: what harness change does to agent behaviour, and where it goes

Chain: Action affordance -> behavioural control -> task outcome -> trajectory
quality -> policy transfer.

> Phase 6 update (see swe_2x2.md and swe_6c_matrix.md): the affordance framing
> below was corrected by the 2x2. The per-turn phase *banner* (H_P, edit tool
> present every turn, no gating) reproduces H_D exactly -- 7/16 = 44% on this
> pilot grid, 5/20 = 25% at wide T=6 -- while the silent tool-list change (H_G)
> sits at the free-agent floor. The "runtime enforcement that matters" is the
> per-turn announcement of phase and remaining budget, not the tool removal; the
> tool availability is a confounded channel that carried the banner in H_D.
> Section 1's tool-availability claim is the pre-decomposition statement; the
> numbers below are unchanged and still true, the causal attribution is not.

## 1. Action affordance

H_D differs from H_A in one mechanically load-bearing way: in the recon phase
the API request carries `tools=[bash]` -- the edit tool is not offered, not
discouraged. From the execute phase on the request carries `[bash, edit]`.
Across 16 episodes x 2 budgets that is 64 recon turns, all bash-only, with
execute/feedback turns offering edit.

The bash write refusal (`writes are not allowed in this turn`) is a second gate
that never fires: 0 occurrences across 64 episodes. On real SWE the model does
not try `sed`/`patch`/`>` during recon -- it runs `find .` and `git log`. So the
runtime enforcement that matters is the tool availability, and the command filter
is theatre for this task distribution.

## 2. Behavioural control

Static instruction cannot move this agent. H_A' (same free loop, same 4-turn
budget, same system prompt, plus one paragraph carrying the behavioural content
of the three phase prompts) scores 1/16 = 6% vs H_A 2/16 = 12% -- the paragraph
reinforces the exact behaviour that is failing (`inspect inspect inspect
inspect`, 6x) and produces no recovery.

Affordance-level control does. At T=4 H_D produces 7 edit calls in 16 episodes
(0.44/episode) vs H_A+H_A' 4 edit calls in 32 episodes (0.13/episode) -- 3.5x
more edits, same model, same tasks. Conditional on writing anything, resolve is
H_D 54% vs H_A 25%.

## 3. Task outcome

The budget sweep resolves the shape of the effect:

| max_turns | H_A | H_D | gap |
|-----------|-----|-----|-----|
| 2         | 0%  | 6%  | +6  |
| 4         | 12% | 44% | +32 |
| 6         | 31% | 50% | +19 |
| 8         | 50% | 44% | -6  |

Both arms are monotone in budget. The gap peaks at T=4 and disappears by T=8.
At T=8 the free loop self-discovers the full inspect->edit->test->repair cycle
(test_after_edit 50%, repair 12%) and the fixed 1-recon/2-execute allocation
starts to cost turns in feedback. H_D is unit-budget efficiency, not a structural
improvement: it buys about +30 points at a scarce budget and nothing at a
generous one.

## 4. Trajectory quality

The verify loop is inert at low budget and emerges only when turns are plenty.
At T=4: 0 test-suite runs in any arm, in any episode, including H_D whose
feedback phase explicitly says "re-run the failing tests". At T=6 H_D runs 5;
at T=8 both arms run tests (H_D 10). This is the sharpest form of the finding
from section 2: the same agent that will not verify when told to verify does
verify when it has enough turns to afford the cost. Instructions to this model
about test-driven repair are inert at T=4; giving it the turns does the work.

## 5. Policy transfer

This is the reason the Phase 4 distillation route is closed, in sharper terms
than "0/10". The effect to transfer is "edit before you run out of turns" -- a
scheduling property of the harness, not a content property of the conversation.
SFT on the teacher's conversation can at best teach a student to imitate prose
that describes recon, edit, and verify. It cannot teach the student to
experience a turn whose tool list contains no edit option, which is the only
thing that produced the effect. And the 0.6B student never calls a tool at all,
so it never experiences any of the affordance structure regardless of what it
was shown. The student got the teacher's text and did not get the teacher's
harness.

## External validity

Second model (space-bunny 7B), same 5 instances, same grid: H_A 3/16 = 19%,
H_D 5/16 = 31%, gap +12pt. The effect is present for both models and scales with
capability in the expected direction. The gain is smaller for the weaker model,
which has less to gain from an enforced recon->edit structure.

### Wider task set: the pilot overestimated the effect

The pilot's 5 instances were gated for having a small, well-formed P2P set, which
also selected for instances where a single-file fix is achievable in 4 turns.
On the wider set (20 instances: 8 django + 12 sympy, 2 repos, 2 test runners,
1-2 gold files, 143-2103 char statements) at T=4, both arms collapse:

| arm | pilot (5 instances) | wide (20 instances) |
|-----|--------------------:|--------------------:|
| H_A | 2/16 = 12%          | 0/40 = 0%           |
| H_D | 7/16 = 44%          | 4/40 = 10%          |
| gap | +32pt               | +10pt               |

H_D solves django-11066 reliably (2/2 wide, 5/5 pilot) and two sympy
instances partially (1/2 each), and nothing else. H_A solves nothing.

This is not a refutation of the harness effect; it is a measurement of its
ceiling. The pilot's 44% was on the easy end of the distribution. The gap
shrinks from +32 to +10 points because the harder instances do not reward
early editing -- they require more inspection, more context, and sometimes a
multi-file change that 4 turns cannot complete. The mechanism finding from
section 1 still holds on the instances where it does fire, but its scope is
narrower than the pilot suggested.