# Cross-model replication: H_A vs H_D on a second model

Goal: is the H_D > H_A effect a property of the harness, or an interaction with the one
model it was found on (`9router/dots3-note-prev`)?

Design: 2 models x 2 harnesses x 2 tiers (tier3, tier5) x 24 episodes, holding taskset,
patch mode, subprocess runtime, `max_turns = 4` and `temperature = 0.0` fixed. Configs in
`eval_patch_m2_budget.toml` (H_A) and `eval_patch_m2_hd.toml` (H_D).

Second model: `openrouter/stealth/space-bunny-alpha`. Chosen on regime, not on label:
tier3 H_A measures 6%, so there is headroom for H_D to move. Two earlier candidates were
rejected because they could not discriminate a harness effect:
`openrouter/cohere/north-mini-code:free` sits at the floor (15 valid, 0 solved, every
episode `no_write`), and `sensenova/glm-5.2` saturates the tier (79% H_A, 100% H_D on
6 episodes, no headroom left).

## Solve rates

| model | tier3 H_A | tier3 H_D | tier5 H_A | tier5 H_D |
| --- | --- | --- | --- | --- |
| dots3-note-prev | 5/24 = 21% | 14/24 = 58% | 1/24 = 4% | 4/24 = 17% |
| space-bunny-alpha | 3/47 = 6% | 16/40 = 40% | 2/45 = 4% | 5/23 = 22% |
| glm-5.2 | 19/24 = 79% | 6/6 = 100% | no data | no data |

`valid` is the denominator: episodes ending on a rate-limit or transport failure are
excluded, because those failures measure the provider, not the harness.

H_D > H_A on **both** tiers, with dots3's direction reproduced on both:

    tier3: dots3  +37 points (21% -> 58%)     space-bunny  +34 ( 6% -> 40%)
    tier5: dots3  +13 points ( 4% -> 17%)     space-bunny  +18 ( 4% -> 22%)

That upgrades the claim from "found on dots3" to "observed on two models", and it covers
the tier where the effect was smallest on dots3 (tier5) -- the harder half to reproduce,
since H_A sits near zero there and any positive H_D number is noise-adjacent.

## The behaviour replicates too

Same action-sequence profile as `behavior.py`, space-bunny only (155 valid episodes):

    tier3-regression-trap  H_A  yes      3   ...   tstAft= 0%  noWr= 0%
    tier3-regression-trap  H_A  no      44   ...   tstAft= 9%  noWr=41%
    tier3-regression-trap  H_D  yes     16   ...   tstAft=56%  noWr= 6%
    tier3-regression-trap  H_D  no      24   ...   tstAft=62%  noWr= 0%

Two independent channels point at the same mechanism found on dots3:

- `test_after_edit` rises from 9% (H_A unsolved) to 56-62% (H_D), against 0% to 64% on
  dots3. tier3 punishes an unverified edit: its trap is a change that looks correct and
  breaks a previously passing test, so an edit with no following test scores the same as
  a wrong one.
- `no_write` collapses from 41% (H_A unsolved) to 0% (H_D unsolved). H_D's read-only
  recon turn keeps the model off the inspect-and-leave branch that is half of H_A's
  failure mode.

On tier5 the channel differs: H_D's gain does not come from `test_after_edit` (22% H_D
unsolved vs 28% H_A unsolved) but from editing at all -- `no_write` 0% vs 21% -- which
matches the earlier finding that tier5's binding constraint is exploration budget, not
sequencing.

## Magnitude is model-dependent, direction is not

The effect is measurable where the model is failing but capable, and it does not vanish as
the unassisted rate rises to ~80%, where glm-5.2 had no tier3 headroom left to show it:

    dots3  H_A = 21%  ->  H_D gains +37 points
    bunny  H_A =  6%  ->  H_D gains +34 points
    glm    H_A = 79%  ->  no headroom, H_D cell unusable

glm-5.2's 79% H_A is a different population than the other two: a model that already
closes the loop unassisted has little for H_D to supply. That is why a cross-model claim
needs a second model in the failing-but-capable band, not a stronger model.

## Limits of this replication

n is not equal across cells. Three of the six runs hit the endpoint's quota ceiling and
lost most or all episodes, so H_D pools two usable repeats (40 tier3, 23 tier5) while
H_A pools two (47 tier3, 45 tier5), and the remaining tier5 H_D cell is a single repeat.
Per-repeat wobble inside H_A is real (4.2% and 8.7% on tier3). The pooled gap (+34 /
+18) is large relative to that wobble, which is why the direction claim holds, but the
point estimates should not be quoted as precise rates.

## Endpoint facts worth recording

- verifiers' model client has **no read timeout**; the rollout timeout is the only bound
  and its default is 4 hours. One hung episode on space-bunny-alpha stalled a whole `-c 1`
  run for 25 minutes at 40/48. `env.agent.timeout.rollout = 600` fixes it (~15x a normal
  episode), failing the hung episode instead of blocking the run.
- WSL inherits `http_proxy`/`ALL_PROXY` pointing at the Windows host's proxy port. When
  the proxy is down, every request fails with connection refused rather than a provider
  error, which is easy to misread as the model being unreachable.
- Quota exhaustion does not always read as a clean 429. At `-c 4` it destroyed both tiers
  on every candidate tried; at `-c 1` a single run loses 0-24 of 48 episodes at random.
