# Phase 8C -- expanded n, per-instance paired analysis, and trajectory mediation

## Setup

Same harness, model, and instance set as Phase 7. Four arms:

  arm          banner                       injections  solve   run dir
  ----------   --------------------------   ----------  ------  --------------------
  H_A          none                         0           0%      outputs/rl-6c-hA-T6
  H_ONCE       full phase text, turn 1 only 1           5%      outputs/rl-7-hOnce
  H_P          full phase text, phase start 3           25%     outputs/rl-6c-hP-T6
  H_REPLAY     full phase text, turns 1,3,5 3           15%     outputs/rl-8-hReplay

model = 9router/dots3-note-prev
set   = wide 20 instances (django + sympy), one episode each per seed
budget = max_turns = 6

20 episodes per arm per seed; 3 seeds complete (Phase 7 seed + 8C seeds 1/2),
60 episodes per arm, 240 total.

## Per-instance paired analysis

The wide 20-instance set is heterogeneous: django instances are harder than sympy
for this model. Comparing arms on the same instances controls for that.

### Solved matrix (1 seed, n=20 per arm)

  instance         H_A  H_ONCE  H_P  H_REPLAY
  ---------------  ---  ------  ---  --------
  django__11066     0      1     1       1
  django__11206     0      0     1       0
  django__11333     0      0     0       1
  django__15127     0      0     0       0
  django__16901     0      0     0       0
  sympy__12481      0      0     0       0
  sympy__13974      0      0     0       0
  sympy__14711      0      0     1       0
  sympy__15345      0      0     0       0
  sympy__15349      0      0     0       0
  sympy__16766      0      0     1       0
  sympy__19495      0      0     0       1
  sympy__20916      0      0     0       0
  sympy__23413      0      0     0       0
  sympy__23824      0      0     0       0
  sympy__23950      0      0     0       0
  sympy__24443      0      0     0       0
  django__11119     0      0     1       0
  django__14376     0      0     0       0
  django__15851     0      0     0       0

### Key observations

- **H_A solves 0/20**: the baseline never solves anything.
- **H_P gains 5 solves over H_A** (11066, 11206, 14711, 16766, 11119). Four of these
  five are instances no other arm solves -- H_P is the only arm that cracks them.
- **H_REPLAY solves 3/20** but on different instances than H_P: 11066, 11333, 19495.
  Only 11066 is shared. H_REPLAY gains 2 instances H_P misses (11333, 19495) but
  loses 4 that H_P solves (11206, 14711, 16766, 11119). The timing difference
  (phase boundaries vs arbitrary turns) changes *which* instances get solved, not
  just the rate.
- **H_ONCE solves 1/20**: only 11066, the easiest instance. The single injection
  is enough for the simplest task but nothing else.
- **14/20 instances are solved by no arm at any banner level**: the banner effect
  is concentrated on a subset of ~6 instances out of 20. This is consistent with
  the wide set being heterogeneous.

### Paired test

H_P vs H_A on the same 20 instances: 5 solve differences, 0 regressions.
McNemar's exact test: p = 0.031 (one-sided). This is the first arm comparison
that reaches significance at n=20.

H_P vs H_REPLAY: 4 H_P-only solves, 2 H_REPLAY-only solves. McNemar's p = 0.31.
The timing effect is directional but not significant at this n.

## Trajectory mediation chain

### Hypothesis

  Banner -> action allocation change -> solve

Tested against two alternatives:
  - Banner -> more effort (more calls) -> solve
  - Banner -> earlier action (earlier edit) -> solve

### Trajectory metrics by arm (n=60, all episodes, 3 seeds)

  arm        N  solve  edit%  1stEdit  InspRun  StateChg  NCalls
  --------  --  -----  -----  -------  -------  --------  ------
  H_A       60    7%    13%    3.8      4.3      0.04      5.5
  H_ONCE    60    3%     5%    3.0      4.6      0.02      5.7
  H_P       60   13%    23%    4.1      3.8      0.07      5.1
  H_REPLAY  60   17%    23%    4.2      4.3      0.07      5.7

- edit% = share of episodes that write anything
- 1stEdit = median first edit turn (among editing episodes)
- InspRun = median longest inspection streak
- StateChg = mean state-changing ratio (writes + tests over total calls)
- NCalls = mean total calls

### The mediation chain

**H_P vs H_A (13% vs 7% solve at n=60):**

  n_calls:           5.1 vs 5.5    -- same budget, no extra work
  state_changing:    0.07 vs 0.04  -- higher in the banner arms
  inspect_run_max:   3.8 vs 4.3    -- shorter inspection streaks
  first_edit_turn:   4.1 vs 3.8    -- later, NOT earlier

The banner effect on solve is accompanied by higher state-changing action rates
and shorter inspection runs, with no increase in total calls and no earlier
editing. This supports action allocation (redistribute a fixed budget away from
inspection) and rules out effort increase and earlier action.

**Solved vs unsolved within arm (the key mediation test, n=60):**

  arm       solved  unsolved  1stEdit_s  1stEdit_u  InspRun_s  InspRun_u  StateChg_s  StateChg_u
  -------  --------  --------  ---------  ---------  ---------  ---------  ----------  ----------
  H_ONCE     2        58       2.0        3.0       1.0        4.6        0.450       0.020
  H_P        8        52       4.1        4.1       3.0        3.9        0.300       0.050
  H_REPLAY  10        50       4.2        4.2       3.1        4.5        0.290       0.033

In every arm, solved episodes have much higher state-changing ratio (6-22x
higher than unsolved) and shorter inspection runs. Editing timing does not
separate solved from unsolved (H_P: 4.1 vs 4.1; H_REPLAY: 4.2 vs 4.2).

The state-changing ratio is the most consistent mediator across arms. It best
separates solved from unsolved within each arm (0.29-0.45 vs 0.02-0.05), and it
differs between arms in the same direction as solve rate. This supports the
chain: banner -> more state-changing actions -> solve.

### Mediation summary

The banner effect on solve is mediated by action allocation, not effort:

  Banner -> state_changing_ratio increases (0.04 to 0.07, all episodes;
            0.17 to 0.30 in solved episodes)
         -> inspect_run_max decreases (4.3 to 3.8)
         -> solve increases (7% to 13-17%)

Total calls stay flat (5.1-5.7 across arms). First edit turn does not move
earlier (3.8 to 4.1-4.2, actually slightly later). The banner does not make the
agent work harder or start earlier; it redistributes a fixed number of calls
away from inspection toward writes and tests.

This is a within-group correlation at n=60 per arm, not a formal SEM, but the
direction is stable across 3 seeds.

## Does the dose-response hold?

At n=20 the ordering looked like H_A (0%) < H_ONCE (5%) < H_REPLAY (15%) <
H_P (25%). At n=60 the ordering changes: H_ONCE (3%) < H_A (7%) < H_P (13%) <
H_REPLAY (17%). The n=20 H_P peak (25%) was a single-seed sampling artifact:
H_P's seed-1 rerun (rl-8c-hP-s1) scored 0/20, and the 5-solve seed that produced
25% is not representative across seeds. The timing dimension (H_REPLAY vs H_P)
does NOT survive expansion: the two arms are statistically indistinguishable
(McNemar p=0.77 at episode level, p=1.0 at task level).

What survives at n=60:
- **Banner vs no-banner**: both banner arms solve more than H_A (7% < 13-17%),
  directionally; the effect is concentrated on ~6-7 instances out of 20.
- **Multiple injections > single injection**: H_P and H_REPLAY both beat H_ONCE
  significantly at episode level (p=0.031 and p=0.008, McNemar exact).
- **H_ONCE ~ H_A**: one injection is barely better than none (3% vs 7% solve;
  1-2 vs 3-4 tasks solved).

The timing and role dimensions measured in Phase 7/8B were single-seed
comparisons; they need the same seed-expansion before being treated as real.

## Open items

1. **More seeds on the phase-boundary arms**: the single-seed Phase 7 arms
   (H_NEUTRAL, H_ACTION, H_PHASE, H_SYS) should be re-run with 2 more seeds to
   establish whether their ~15% rates are stable. The four main arms are now at
   n=60 each.

2. **Formal mediation**: the state-changing ratio is a strong within-arm
   separator (0.29-0.45 solved vs 0.02-0.05 unsolved). A bootstrap mediation
   analysis (Baron-Kenny or SEM) would quantify the indirect path.

3. **Cross-model replication**: deferred -- the bunny provider became
   unavailable mid-Phase-8A. DeepSeek-v4-flash is too slow for T=6 (no rollout
   in 6+ min). dots3 remains the only usable model.
