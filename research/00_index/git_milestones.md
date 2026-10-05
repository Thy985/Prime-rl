# Git Milestones

Milestone commits only. Not a changelog: each row is the commit that **closes a
research step**, so later re-reads can jump straight to the state that mattered.
Range `86e9e8366..83c990b00` (82 commits, 2026-10-01 → 2026-10-06).

Tags: `research-p8c-final` = `a5975ac74` (freeze point). Earlier phases are
identified by commit hash because the tag is deliberately a freeze marker, not
a per-phase cursor.

| Commit | Phase | Meaning |
| --- | --- | --- |
| `86e9e8366` | P0 | SWE feedback-terrain lab — define and audit a code-repair reward |
| `17d30dbcb` | P0 | Plan revised to spec level (verifiers v1 alignment, golden episode, replay) |
| `498fca529` | P1A | Environment contract + Golden Episode (closure before live run) |
| `b2698922c` | P1B | Real verifiers Episode with the audited verifier as reward |
| `56a6c91d1` | P1B | Executing-reward replay over a saved trace — **Phase 1B acceptance** |
| `57e81c8af` | P2 | Difficulty ladder with per-tier budgets and audits |
| `5ef3bf8ee` | P2 | Endpoint error rate fixed — "the tier3 cliff was partly an artifact" |
| `1746c6c05` | P3 | Capability frontier across the three swe-lab tiers |
| `2755ba56f` | P3 | Tier 4 — hidden configuration layer, and what the audit caught |
| `d43b15861` | P3 | **First harness A/B — removing one tool costs 44 points** |
| `6a1177c45` | P3 | **RETRACT the Harness C claim — at n=32 the effect reverses** |
| `d732e5ffd` | P3 | Harness A/B/C at 3 runs each — tool support is the effect; difficulty is task × harness |
| `a56e6ae13` | P3 | Tier 5 does **NOT** de-saturate Harness A — negative result on the difficulty axis |
| `6004a7559` | P3 | A binding turn budget creates the headroom Harness A lacked (**and a bug hid it**) |
| `08e6b1a1d` | P4 | Harness D — plan/execute/feedback as a runtime program |
| `76d91806e` | P4 | Harness E — the ablation of Harness D |
| `7cdbc5980` | P4 | **Retire the 'planner' framing** — the validated intervention is staged action allocation |
| `1416ba43f` | P4 | H_F attribution — the phase prompts carry most of the tier3 gain; gating helps tier4 only |
| `649d5ab21` | P4 | Phase 4 data layer — trajectory to training view, transformation recorded |
| `3c6bfb48b` | P3.6 | Behavior profile — H_D's tier3 gain is the verify turn and nothing else |
| `ade6250c4` | P4.5 | Cross-model replication completes on space-bunny-alpha; H_D > H_A on both tiers |
| `14c2b34e6` | P5 | **Real SWE-bench Verified pilot** — containerless verifier pipeline; 10% vs 30% |
| `22f40cd41` | P5 | Real-SWE pilot topup — H_D 7/16=44% vs H_A 2/16=12% |
| `1df2989df` | P5 | Distillation verification — **no behaviour transfer** (0/10 tool calls both) |
| `625653bb4` | P5 | H_A-prime control — static behaviour text recovers none of the gap |
| `9136aac03` | P5 | Turn-by-turn mechanism probe — load-bearing gate is edit-tool absence |
| `a867f112d` | P5 | Budget sweep — gap peaks at T=4 (+32pt), vanishes at T=8 (−6pt) |
| `6bc971c6b` | P5 | Stage conclusion — wide-set calibration (**pilot overestimated by 4×**: +32pt → +10pt) |
| `2bae38d38` | P6 | Phase 6A/6B — H_P/H_G 2×2 switches + H_ADAPT deterministic scheduler |
| `4b6854707` | P6 | **Fix behavior classifier** — `2>/dev/null` / `2>&1` no longer counted as tree writes |
| `6aea58419` | P6 | 6C T=6 decomposition — H_P 5/20 = H_D 25%, H_G 1/20; **affordance scheduling falsified** |
| `ce618eed3` | P6 | Pilot H_P reproduces H_D exactly (7/16=44%) — enforcement adds nothing |
| `f3a91ba36` | P7 | Phase 7 banner decomposition — `SWE_LAB_BANNER` modes + trajectory metrics |
| `610450d35` | P7 | H_SYS at 15% — message role is load-bearing; repetition is the necessary condition |
| `d0985e941` | P7 | **Tone down the role claim** + three-layer model + Boundary-of-the-claim |
| `323655757` | P8B | H_REPLAY at 15% — timing is a fourth dimension (to be revised below) |
| `6315a6e06` | P8 | `--no-sync` fix — unblocks bunny (`deep-ep` metadata fails on aarch64) |
| `0807caa0c` | P8C | Per-instance paired analysis (McNemar p=0.031) + trajectory mediation chain |
| `a5975ac74` | **P8C** | **FREEZE — n=60 revises Phase 8B: H_P 25% was single-seed noise** |
| `83c990b00` | — | chore: tier4/tier5 materialized fixture dirs (working-tree head at archive time) |

## Reading notes

- Three milestones are retraction/fix commits, not feature commits. They are the
  highest-value entries in the history: `6a1177c45` (claim reversal at n=32),
  `7cdbc5980` (naming correction), `4b6854707` (metric redefinition that
  changes an earlier conclusion), `6004a7559` ("a bug hid it").
- `5ef3bf8ee` is the earliest measurement-instrument bug in the line.
- `b257519fe` and `a5975ac74` share an identical subject; the latter differs
  only by a 120-line revision to `tools/swe_lab/runs/swe_8c_expanded.md`
  (+65/−55). The tag points at `a5975ac74`.
- No milestone before `a5975ac74` is tagged. If a per-phase cursor is needed,
  the honest options are `d732e5ffd` (P3), `a867f112d` (P5), `ce618eed3` (P6),
  `d0985e941` (P7).