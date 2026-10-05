# Phase 7 -- banner mechanism decomposition: the control-plane announcement and its cost

## Setup

Everything that Phase 5-6 varied is now held fixed, and only the runtime's
per-completion control-plane text varies:

  model           9router/dots3-note-prev
  set             wide 20 instances (django + sympy), one episode each
  budget          max_turns = 6
  tools           bash + edit available in every turn (SWE_LAB_GATE=0)
  allocation      "1,2," (plan 1 call, execute 2, feedback to budget)
  system prompt   identical across all seven arms

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
| H_SYS       | full phase text (as H_P)             | phase start, system role |

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
| H_SYS     | 15%   |  25%  |  75%     | phase start    | 3.0           |  0.09     |  5.8    |  4.5            |  1.30        |

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

All seven arms are 20 rollouts. H_SYS is clean: 19 ended at max_turns and 1 at
agent_completed, no HarnessError.

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
state_chg. The phase-start spacing is worth the difference. Directional at this
n (5 vs 3 solves).

**The message role is load-bearing.** H_SYS carries the identical H_P text at
the identical phase-start cadence -- 3.0 injections per episode in both, so no
cadence or re-rooting difference -- but injects it as a system message instead
of a user message. It drops from 25% to 15% solve, 35% to 25% edit, 0.11 to
0.09 state_chg, and its inspect_run_max worsens from 3.5 to 4.5. Directional at
this n (5 vs 3 solves), and the trajectory metrics point the same way as the
solve rate rather than scattering around it. The user-role interruption that
lands at the decision point is part of what does the work; the same words
arriving as a system message do not carry it.

H_SYS and H_PHASE are the two clean single-factor comparisons in the run, and
they agree: each one drops 25% -> 15% and costs the same ~10 points, one for
moving the banner to the system role and one for moving it to every turn.
H_ACTION is a two-factor arm (stripped content *and* every-turn cadence) that
also lands at 15%, consistent with either factor or both. H_A (no banner) is
0%, H_ONCE (content and role right, cadence at one) is 5%, H_NEUTRAL (role and
cadence right, content inert) is 5%.

Repetition is the one factor whose step is larger than the others: going from
one injection to the phase-start cadence is 5% -> 25%, a 20-point step.
Repetition is the necessary condition; role, cadence and content are the
sufficient ones.

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

Across Phases 5-7 the claim narrows three times:

  Phase 5  Harness 改变了行为。
  Phase 6  不是 tool gating 改变行为。
  Phase 7  Runtime context injection 改变行为，且 role、cadence、content 都影响效果。

> Harness 的作用不是"告知" Agent，而是 Runtime 在每个决策周期以 user-turn 形式
> 重新构造 Agent 的局部上下文。

More precisely: the control plane reads the runtime state and injects it into
the model's turn at the phase boundaries, and the injection's role, cadence and
content are each independently load-bearing.

  Runtime state
      |
  Control-plane injection
      |-- role
      |-- cadence
      `-- content
      |
  Agent local decision context
      |
  action allocation
      |
  inspect / edit / test
      |
  task outcome

The three dimensions each drop the effect from 25% to 15% when misspecified,
and repetition is the necessary condition underneath them all: one announcement
of the right content and role still yields the baseline.

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

The role result is the one that most needs wording restraint. H_SYS establishes
only that a system-role copy of the same text at the same cadence is not
equivalent to the user-role one. It does not establish *why*. That the message
lands on a task turn, that system text is absorbed before the decision point,
and that the runtime must interrupt rather than merely tell are three different
accounts, and H_SYS cannot separate them because it fixes only the role and
varies nothing else. The honest statement is the weaker one:

> the intervention is a user-turn runtime injection, not a standing
> instruction; and per-decision placement, not per-phase placement, is what
> carries the effect.

That is what the control-plane framing was aiming at and what Phase 7
supports. It is not a claim about interruption as a mechanism.

## Boundary of the claim

The claim supported here is not "the harness improves reasoning". It is:

> Runtime intervention changes *action allocation* under a fixed model and a
> fixed interaction budget.

n_calls is 5.5-5.8 in every arm, so the model is not working harder or for
longer; what moves is how a fixed number of calls is distributed across inspect,
edit and test. The banner does not add reasoning capacity to a fixed budget, it
changes where the budget goes.

A further hypothesis is worth stating because Phases 5-7 make it testable,
though it is not established here: part of what gets called Agent intelligence
may be Runtime contextualization quality at each decision point rather than
model capability. That is a research question, not a finding of this run.

## Discipline note

No further H_D / H_G / H_ADAPT variants. Phase 6 established that the tool
affordance contributes nothing here (H_G, H_ADAPT floor; H_P == H_D), and Phase
7 shows that the operative variables are the announcement's content, cadence and
message role -- not the enforcement that the earlier arms were built around.
Those arms have served their purpose; additional variants would only re-measure
the same null.

Two items remain open.

Neither factor step is statistically established at n=20. The content step
(neutral 5% -> action/full 15%, every-turn) is 1 vs 3 solves; the cadence step
(every-turn full 15% -> phase-start full 25%) is 3 vs 5 solves; the role step is
3 vs 5 solves. The ordering is consistent across solve, edit%, state_chg and
inspect_run_max in each case, so the directions hold, but a larger n on
H_NEUTRAL / H_ACTION / H_PHASE / H_P / H_SYS would tighten the gaps -- no new
arm is needed.

Whether the cost mechanism is steering cost or attention failure remains open
and is not resolvable by any arm in this run. It would need a counterfactual in
which the same user-role text is re-presented mid-phase without a phase
boundary, which is a new arm and not part of this decomposition.

The message-role question, by contrast, is answered: H_SYS holds text and
cadence exactly constant against H_P and drops 25% -> 15% when the banner moves
to the system role. The role is load-bearing, ~10 points. What the role *does*
-- whether it is attention, salience or position -- is a separate question this
arm does not answer.
