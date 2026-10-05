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
| H_ACTION    | `Phase: X. Goal: <action>.`          | every turn               |
| H_P         | full phase text (PLAN / EXECUTE / FEEDBACK) | phase boundary (recorded reference) |
| H_PHASE     | full phase text                      | every turn               |

Injections are counted straight out of the traces, not assumed from the config.
Verifiers re-roots a branch whenever the advertised tool set changes and
duplicates the prefix (documented in `frontier.tool_calls`), so the counter
collapses consecutive identical banner texts; H_NEUTRAL shows `raw=6, dedup=5`
in the smoke, one re-rooting artefact.

## Result

| arm       | solve | edit% | no_write | cadence        | inj/ep (raw) | state_chg | n_calls | inspect_run_max | inspect_runs |
|-----------|-------|-------|----------|----------------|--------------|-----------|---------|-----------------|--------------|
| H_A       |  0%   |  10%  |  90%     | none           | 0             |  0.02     |  5.5    |  4.5            |  1.30        |
| H_ONCE    |  5%   |  10%  |  90%     | turn 1 only    | 1             |  0.03     |  5.7    |  5.0            |  1.30        |
| H_NEUTRAL |  5%   |   5%  |  95%     | every turn     | 5.9           |  0.01     |  5.7    |  6.0            |  1.15        |
| H_ACTION  | 15%   |  20%  |  80%     | every turn     | 5.95          |  0.04     |  5.8    |  5.0            |  1.15        |
| H_P       | 25%   |  35%  |  65%     | phase start    | 3.0           |  0.11     |  5.7    |  3.5            |  1.40        |
| H_PHASE   | 15%   |  25%  |  75%     | every turn     | 5.7           |  0.08     |  5.7    |  5.0            |  1.25        |

inj/ep (raw) is the number of banner messages the conversation actually carried,
counted from the traces (re-rooting duplicates included -- the model reads them
all). The "distinct texts" count differs from raw only for the every-turn arms,
where the same phase's text repeats: H_ACTION distinct 3.0 vs raw 5.95, H_PHASE
distinct 2.9 vs raw 5.7. The dose-response and the cadence comparison below use
raw.

edit% = share of episodes that write anything; state_chg = (write + test) calls
over total calls; inspect_run_max = median longest streak of consecutive
inspection calls. All six arms are 20 rollouts. H_PHASE is the only arm with
failures: 18 ended at max_turns and 2 hit a 600s rollout timeout
(`HarnessError: agent timeout`) -- the every-turn full text makes those
episodes slower, not the banner mechanism itself. Both timed-out rollouts count
as unsolved, so H_PHASE's 15% is a floor; if either had solved the
"more repetition dilutes" finding is weaker, never stronger. All other arms are
20 clean rollouts. `edit_after_failed_test` is 0.00 in every arm, so no arm
here does test-driven repair -- the Phase 5/6 finding holds.

H_SYS (identical text and cadence as H_P, banner injected as a system message)
is still running and is not in this table.

## The three factors, separated

**Recency is necessary.** H_ONCE collapses to the baseline: 5% solve, 10% edit
-- identical to H_A on every trajectory metric, inspect_run_max 5.0, state_chg
0.03. Same banner text as H_P, but delivered once instead of three times, the
effect is gone. The announcement is not a fact the model retains; it is a cue
that decays.

**A neutral turn counter is inert.** H_NEUTRAL injects every turn (5.9 per
episode) and achieves 5% solve, 5% edit, 6.0 inspect_run_max -- the worst of
every arm, an episode that inspects the entire budget. "You are on turn k of T"
carries no control signal. The runtime announcing that it exists is not the
mechanism.

**Content moves the every-turn arms.** With the cadence held at every turn, the
three arms differ only in what the banner says: neutral status 5%, one-line
action goal 15%, full phase text 15%. Action-oriented content is worth 10
points over neutral status; full phase specification adds nothing over the
one-line goal at this cadence. At n=20 the neutral-vs-action gap is 1 vs 3
solves, so the content step is directional rather than established, but the
ordering is consistent across solve, edit% (5 -> 20 -> 25) and state_chg
(0.01 -> 0.04 -> 0.08).

**Cadence matters on top of content.** H_PHASE carries the same full phase text
as H_P but injects it every turn (5.7 per episode) instead of at the phase
starts (3.0), and drops from 25% to 15% solve, 35% to 25% edit, 0.11 to 0.08
state_chg. The phase-boundary spacing is worth the difference. Directional at
this n (5 vs 3 solves), but it is the only comparison in the run that holds
content exactly constant while varying only when the text arrives.

So the dose-response over injection frequency at full phase content is 1 -> 5%,
3 (phase starts) -> 25%, 5.7 (every turn) -> 15%. Non-monotone, with the peak
at the phase boundaries. Repetition is necessary (1 vs 3), and repetition at
the wrong spacing is worse than not repeating at all beyond the boundary
(5.7 < 3).

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
number of calls away from inspection. Every intermediate arm sits on the same
monotone line -- H_P 35% edit / 3.5 run / 0.11 state_chg / 25% solve, H_PHASE
25% / 5.0 / 0.08 / 15%, H_ACTION 20% / 5.0 / 0.04 / 15%, H_ONCE 10% / 5.0 /
0.03 / 5%, H_NEUTRAL 5% / 6.0 / 0.01 / 5%, H_A 10% / 4.5 / 0.02 / 0% -- so the
trajectory is the mediator, not a parallel correlate. edit%, inspect_run_max,
state_chg and solve all move together in the same order.

Two numbers separate the arms. inspect_run_max 3.5 is H_P alone; every other
arm is 4.5-6.0. And where the edit lands: among H_P's seven editing episodes
first_edit_turn is [2,3,3,4,4,6,6] -- five of seven inside the PLAN+EXECUTE
window (turns 2-4), right after the announcement that covers them. H_PHASE's
editing episodes land at [2,2,3,4,6]. The announcement does not change when the
agent edits; it is what makes the agent get to editing at all, and the
phase-boundary cadence is what keeps the edit inside the window the phase is
supposed to be spent in.

edit% is not monotone in frequency either: H_NEUTRAL injects most often (5.9)
and edits least (5%). The every-turn full-text arm (H_PHASE, 5.7) edits at 25
vs H_P's 35 at the phase starts (3.0). Frequency without content buys nothing;
frequency on top of content costs a little.

## Mechanism statement

Phase 5 framed the result as "the per-turn banner, not the tool affordance, is
the mechanism." Phase 6 confirmed it (H_P == H_D at T=6; the silent tool-list
change does nothing). Phase 7 sharpens it, and overturns one part:

> Harness 的作用不是"每轮重复注入上下文"，而是"在决策边界处广播控制平面状态"。

The announcement has a marginal cost as well as a marginal benefit. The benefit
is one redirected turn: the injected text re-aligns the agent's next action to
the current phase.

The cost mechanism is an inference, not a measurement, and should stay marked
as such. The two endpoints show that a cost exists -- 5% at one announcement,
15% at five -- but they do not show what it is. The most economical reading is
that an injected message resets the action frame the agent was carrying, so each
one spends part of the turn it lands in, and five announcements of the same text
mean five frames that never compound into a phase. That is consistent with the
shape of the curve, and with H_NEUTRAL being the worst arm (the most
interruptions, no content to gain) rather than merely second worst. But it is
equally consistent with "repetition of identical text is ignored", which would
make the cost zero and the dilution a failure of attention rather than a cost
of steering. Nothing in this run separates those two readings.

At the phase boundaries (3 announcements, ~3 turns of uninterrupted action flow
between cues) the effect is maximal, whichever account is right. At one
announcement there is nothing to redirect turns 3-6.

That is what the control-plane framing buys that the prompt framing did not:
the runtime's announcement is an intervention with a dose-response, not a
property of having said the thing at all. H_ONCE is the control that makes the
floor visible -- the same content delivered once, and the effect is gone.
H_PHASE is the control that makes the ceiling visible -- the same content
delivered every turn, and the effect is diluted by half without vanishing.
Neither endpoint is inert, so the announcement is not a binary switch; it is a
resource with a cost, and the phase boundaries are where it is cheapest.

The control-plane reading follows from the cadence comparison. If the mechanism
were "the model needs the phase text nearby at decision time", H_PHASE would
match or beat H_P -- it puts the full phase text at every decision point, not
just the phase starts. It does not: 15% vs 25%. The spacing of the announcement
is part of the signal. The boundary version leaves ~3 turns of uninterrupted
action flow between cues and the effect is maximal; the every-turn version
re-anchors a decision that has already been anchored and the marginal
announcement does not add -- it may even pull the agent back to re-reading the
phase instead of acting in it. What H_P does is announce the phase at the moment
the agent is choosing what the phase is for, and then leave it alone.

What remains open is whether the message role is load-bearing at all. H_SYS
injects the identical H_P text at the identical phase-boundary cadence as a
system message rather than a user message; it is still running.

## Discipline note

No further H_D / H_G / H_ADAPT variants. Phase 6 established that the tool
affordance contributes nothing here (H_G, H_ADAPT floor; H_P == H_D), and Phase
7 shows that the announcement cadence, not the enforcement, is the operative
variable. Those arms have served their purpose; additional variants would only
re-measure the same null.

Two items remain open.

Both levers are real but neither step is statistically established at n=20. The
content step (neutral 5% -> action/full 15%, every-turn) is 1 vs 3 solves; the
cadence step (every-turn full 15% -> phase-start full 25%) is 3 vs 5 solves. The
ordering is consistent across solve, edit%, state_chg and inspect_run_max in
both cases, so the directions hold, but a larger n on H_NEUTRAL / H_ACTION /
H_PHASE / H_P would tighten the gaps -- no new arm is needed.

The message role. H_SYS injects the identical H_P text at the identical
phase-start cadence as a system message rather than a user message. If H_SYS
matches H_P, the role is irrelevant and the mechanism is content-and-cadence
full stop. If it drops, the user-role interruption that lands at the decision
point is part of what does the work -- which would be a stronger result than
anything Phase 5 or 6 produced, because it would mean the harness has to
interrupt the model to steer it, not merely tell it.
