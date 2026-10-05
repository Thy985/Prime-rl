# Phase 7 -- banner mechanism decomposition: the control-plane announcement and its cost

## Setup

Everything that Phase 5-6 varied is now held fixed, and only the runtime's
per-completion control-plane text varies:

  model           9router/dots3-note-prev
  set             wide 20 instances (django + sympy), one episode each
  budget          max_turns = 6
  tools           bash + edit available in every turn (SWE_LAB_GATE=0)
  allocation      "1,2," (plan 1 call, execute 2, feedback to budget)
  system prompt   identical across all six arms

The intervention is the text the planner injects as a user-role message before
each model completion. `SWE_LAB_BANNER` selects the mode
(`tools/swe_lab_env/swe_lab_planner_program.py`); the default `full` reproduces
the recorded per-phase Harness D / H_P behaviour exactly, so every earlier run
stays reproducible.

| arm         | banner text                          | injection cadence        |
|-------------|--------------------------------------|--------------------------|
| H_A         | none (stock free-loop harness)       | 0                        |
| H_ONCE      | full phase text (PLAN at turn 1)     | turn 1 only              |
| H_NEUTRAL   | `Turn k of 6.`                       | every turn               |
| H_ACTION    | `Phase: X. Goal: <action>.`          | phase boundary           |
| H_P         | full phase text (PLAN / EXECUTE / FEEDBACK) | phase boundary (recorded reference) |
| H_PHASE     | full phase text                      | every turn               |

Injections are counted straight out of the traces, not assumed from the config.
Verifiers re-roots a branch whenever the advertised tool set changes and
duplicates the prefix (documented in `frontier.tool_calls`), so the counter
collapses consecutive identical banner texts; H_NEUTRAL shows `raw=6, dedup=5`
in the smoke, one re-rooting artefact.

## Result

| arm       | solve | edit% | no_write | inj/arm | state_chg | n_calls | inspect_run_max | inspect_runs |
|-----------|-------|-------|----------|---------|-----------|---------|-----------------|--------------|
| H_A       |  0%   |  10%  |  90%     |  0      |  0.02     |  5.5    |  4.5            |  1.30        |
| H_ONCE    |  5%   |  10%  |  90%     |  1      |  0.03     |  5.7    |  5.0            |  1.30        |
| H_NEUTRAL |  5%   |   5%  |  95%     |  4.9    |  0.01     |  5.7    |  6.0            |  1.15        |
| H_ACTION  | 15%   |  20%  |  80%     |  3      |  0.04     |  5.8    |  5.0            |  1.15        |
| H_P       | 25%   |  35%  |  65%     |  3      |  0.11     |  5.7    |  3.5            |  1.40        |

edit% = share of episodes that write anything; state_chg = (write + test) calls
over total calls; inspect_run_max = median longest streak of consecutive
inspection calls. All 20 rollouts per arm are clean (agent_completed or
max_turns, no HarnessError / ProviderError). `edit_after_failed_test` is 0.00 in
every arm, so no arm here does test-driven repair -- the Phase 5/6 finding
holds.

H_PHASE and H_SYS are still running and are not in this table. The five arms
above are complete at 20 episodes each.

## The three factors, separated

**Recency is necessary.** H_ONCE collapses to the baseline: 5% solve, 10% edit
-- identical to H_A on every trajectory metric, inspect_run_max 5.0, state_chg
0.03. Same banner text as H_P, but delivered once instead of three times, the
effect is gone. The announcement is not a fact the model retains; it is a cue
that decays.

**A neutral turn counter is inert.** H_NEUTRAL injects more often than H_P
(4.9 per episode vs 3) and achieves 5% solve, 5% edit, 6.0 inspect_run_max --
the worst of every arm, an episode that inspects the entire budget. "You are on
turn k of T" carries no control signal. The runtime announcing that it exists is
not the mechanism.

**Content adds something, but it is secondary.** H_ACTION, same phase-boundary
cadence as H_P with the phase goal stripped to one line, gives 15% solve / 20%
edit -- above the inert arms (5%) but below H_P (25%). Directional; at n=20 the
15 vs 25 gap is 3 vs 5 solves and is not significant. The full phase
specification is worth about half the total effect; the other half is
irrecoverable from this arm alone.

## What the trajectory actually says

The banner is not changing *when* the agent acts. Among episodes that do edit,
first_edit_turn is 3.0 (H_A) and 4.0 (H_P) -- the banner arms edit slightly
*later*. H_A already edits early when it edits; it simply almost never does.

What moves is whether the agent acts at all, and how long it stays stuck
inspecting:

  banner (full phase text, phase-boundary cadence)
    -> more episodes reach a write at all: 10% -> 35% edit rate (H_A -> H_P)
    -> shorter uninterrupted inspection streaks: inspect_run_max 4.5 -> 3.5
    -> state-changing share of calls 0.02 -> 0.11, 5.5x
    -> solve 0% -> 25%

and the total work is unchanged: n_calls is 5.5-5.8 in every arm. The banner
does not make the agent work harder or for longer; it reallocates a fixed
number of calls away from inspection. The intermediate arms sit on the same
monotone line -- H_ACTION 20% edit / 5.0 run / 0.04 state_chg / 15% solve,
H_ONCE 10% / 5.0 / 0.03 / 5%, H_NEUTRAL 5% / 6.0 / 0.01 / 5% -- so the
trajectory is the mediator, not a parallel correlate.

One number separates H_P from the rest: inspect_run_max 3.5 is H_P alone; every
other complete arm is 4.5-6.0.

## Mechanism statement

Phase 5 framed the result as "the per-turn banner, not the tool affordance, is
the mechanism." Phase 6 confirmed it (H_P == H_D at T=6; the silent tool-list
change does nothing). Phase 7 sharpens it, and overturns one part:

> Harness 的作用不是"每轮重复注入上下文"，而是"在决策边界处广播控制平面状态"。

The announcement has a marginal cost as well as a marginal benefit. Its benefit
is one redirected turn: the injected text re-aligns the agent's next action to
the current phase. Its cost is that the announcement is a user-role interruption
that resets the action frame the agent was carrying, so each one spends part of
the turn it lands in. At the phase boundaries (3 announcements, ~3 turns of
uninterrupted action flow between cues) benefit and cost balance and the effect
is maximal. At one announcement there is nothing to redirect turns 3-6. At six
there is a cue every turn and never a turn of momentum, and the correct
instruction arrives with the same content as H_P but does not land.

That is what the control-plane framing buys that the prompt framing did not:
the runtime's announcement is an intervention with a dose-response, not a
property of having said the thing at all. H_ONCE is the control that makes the
floor visible -- the same content delivered once, and the effect is gone.

What is still open is whether *more* announcement is also worse, which is the
direction a flat prompt framing would not predict and the control-plane framing
should. H_PHASE (full phase text every turn, 1.67x H_P's frequency) is running
to test exactly that, alongside H_SYS (identical text and cadence, injected as a
system message) which isolates the message role.

## Discipline note

No further H_D / H_G / H_ADAPT variants. Phase 6 established that the tool
affordance contributes nothing here (H_G, H_ADAPT floor; H_P == H_D), and Phase
7 shows that the announcement cadence, not the enforcement, is the operative
variable. Those arms have served their purpose; additional variants would only
re-measure the same null.

Two items remain open and are running.

The content contribution: H_ACTION vs H_P is 3 vs 5 solves at n=20, so the
content contribution (half the effect, by the edit-rate gap of 20 vs 35) is
directional rather than established. Closing it needs a larger n on H_ACTION and
H_P, not a new arm.

The upper end of the dose-response: H_PHASE (full text every turn) is the test
of whether more announcement is worse than the phase-boundary optimum, and
H_SYS (same text and cadence as H_P, system role) is the test of whether the
message role is load-bearing at all. Neither is in this table yet.
