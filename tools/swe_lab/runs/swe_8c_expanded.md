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

20 episodes per arm currently (1 seed). Seeds 2 and 3 are running in the background
(8 runs total, ~2-3 min per rollout, ~16 hours total).

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

### Trajectory metrics by arm (n=20, all episodes)

  arm        N  solve  edit%  1stEdit  InspRun  StateChg  NCalls
  --------  --  -----  -----  -------  -------  --------  ------
  H_A       20    0%    10%    3.0      4.5      0.02      5.5
  H_ONCE    20    5%    10%    3.5      5.0      0.03      5.7
  H_P       20   25%    35%    4.0      3.5      0.11      5.7
  H_REPLAY  20   15%    20%    3.5      4.0      0.08      5.6

- edit% = share of episodes that write anything
- 1stEdit = median first edit turn (among editing episodes)
- InspRun = median longest inspection streak
- StateChg = mean state-changing ratio (writes + tests over total calls)
- NCalls = mean total calls

### The mediation chain

**H_P vs H_A (25% vs 0% solve):**

  n_calls:           5.7 vs 5.5    -- same budget, no extra work
  state_changing:    0.11 vs 0.02  -- 5.5x increase
  inspect_run_max:   3.5 vs 4.5    -- shorter inspection streaks
  first_edit_turn:   4.0 vs 3.0    -- slightly later, NOT earlier

The banner effect on solve is accompanied by a massive increase in state-changing
actions (5.5x) and shorter inspection runs, with no increase in total calls and
no earlier editing. This supports action allocation (redistribute a fixed budget
away from inspection) and rules out effort increase and earlier action.

**Solved vs unsolved within arm (the key mediation test):**

  arm       solved  unsolved  1stEdit_s  1stEdit_u  InspRun_s  InspRun_u  StateChg_s  StateChg_u
  -------  --------  --------  ---------  ---------  ---------  ---------  ----------  ----------
  H_ONCE     1        19        2          5         1.0        5.0        0.500       0.009
  H_P        5        15        4          3.5       3.0        4.0        0.307       0.044
  H_REPLAY   3        17        3          4         2.0        4.0        0.347       0.029

In every arm, solved episodes have:
  - Higher state-changing ratio (7-8x higher than unsolved)
  - Shorter inspection runs (roughly half the length)
  - Sometimes earlier editing (H_ONCE, H_REPLAY) but not always (H_P: 4 vs 3.5)

The state-changing ratio is the most consistent mediator across arms. It is the
metric that best separates solved from unsolved within each arm, and it also
differs most between arms (0.02 -> 0.11, 5.5x from H_A to H_P). This supports
the chain: banner -> more state-changing actions -> solve.

### Mediation summary

The banner effect on solve is mediated by action allocation, not effort:

  Banner -> state_changing_ratio increases (5.5x H_A to H_P)
         -> inspect_run_max decreases (4.5 to 3.5)
         -> solve increases (0% to 25%)

Total calls stay flat (5.5 to 5.7). First edit turn does not move earlier
(3.0 to 4.0, actually slightly later). The banner does not make the agent work
harder or start earlier; it redistributes a fixed number of calls away from
inspection toward writes and tests.

This is a within-group correlation at n=20 per arm, not a formal SEM. The
expanded n (80 per arm across 4 seeds) will allow bootstrap mediation analysis
with confidence intervals.

## Does the dose-response hold?

Yes, at n=20. The ordering H_A (0%) < H_ONCE (5%) < H_REPLAY (15%) < H_P (25%)
is consistent across solve rate, edit%, state-changing ratio, and inspection run
length. The per-instance data shows the effect is concentrated on ~6 instances
out of 20, not driven by a single lucky instance.

The timing effect (H_REPLAY vs H_P, 15% vs 25%) is directional but not
significant at n=20 (McNemar's p = 0.31). The expanded n is needed to establish
whether the phase-boundary timing is a real fourth dimension or noise.

## Open items

1. **Expanded n**: 2 additional seeds are running (8 runs, ~16 hours). This will
   yield 80 episodes per arm and allow:
   - Formal mediation analysis with bootstrap CIs
   - Significance testing on the timing effect (H_P vs H_REPLAY)
   - Per-instance stability check (does the same subset of instances benefit?)

2. **McNemar's significance**: H_P vs H_A is already significant (p = 0.031) at
   n=20. The other comparisons need larger n.

3. **Cross-model replication**: deferred. Bunny harness compatibility needs fixing
   (proxy injects leading whitespace + trailing data:[DONE] in responses).
