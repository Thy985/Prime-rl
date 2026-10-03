# Cross-model replication -- partial, and what it does and does not license

Goal: is the H_D > H_A effect a property of the harness, or an interaction with the one
model it was found on (`9router/dots3-note-prev`)?

Target design: 2 models x 2 harnesses x 2 tiers (tier3, tier5) x 24 episodes, holding
taskset, patch mode, subprocess runtime, `max_turns = 4` and `temperature = 0.0` fixed.

Second model: `sensenova/glm-5.2` -- a named GLM model, different family and training
lineage from dots3-note-preview. Chosen over the other candidates on capability, since a
model that cannot do the task cannot discriminate a harness effect.

## Result (3 repeats pooled, n=8 per run, -c 1)

| model | tier3 H_A | tier3 H_D | tier5 H_A | tier5 H_D |
| --- | --- | --- | --- | --- |
| dots3-note-prev | 5/24 = 21% | 14/24 = 58% | 1/24 = 4% | 4/24 = 17% |
| glm-5.2 | 19/24 = 79% | 6/6 = 100% | 1/1 | no valid episode |

tier3 direction is consistent with the dots3 result. **That is as far as it goes.** The
H_D cell has n=6, and tier5 has no usable data at all, so this is a direction read, not a
replication. It does not license "observed on at least two models".

## The finding that does survive

**The same tier is a different difficulty for each model.** On identical tasks, budget,
verifier and runtime:

    dots3-note-prev  tier3 H_A = 21%     (23 of 24 episodes fail)
    glm-5.2          tier3 H_A = 79%     ( 5 of 24 episodes fail)

The harness effect was discovered in the first regime and has almost no headroom in the
second: if a model already solves the task 79% of the time unassisted, the most H_D can
contribute is the remaining 21 points, and the most it can *lose* is nothing. So the
question is not simply "does the effect replicate", it is **where does it replicate** --
and the answer the data supports is: it is measurable where the model is failing but
capable, and it compresses as the model's unassisted rate rises. That is a model-dependent
dependence of magnitude, not a sign flip, and it is a more useful thing to know than a
flat replication would have been.

It also sharpens the Phase 3.6 result. dots3's tier3 failures were *unverified edits*
(solved H_A episodes never run a test). glm-5.2's tier3 failures -- 5 episodes -- are
almost certainly a different population, because a model that reaches 79% unassisted is
mostly already closing the loop. The behaviour H_D supplies is only binding when the
model is not already supplying it.

## Why the second model's n is small

`tenxun` routes 503 model ids. Only `9router/dots3-note-prev` has demonstrated sustained
capacity for a full run at this workload. Measured sequential throughput:

| model | 20 sequential calls | sustained |
| --- | --- | --- |
| `9router/dots3-note-prev` | 20/20 | ~32 calls/min |
| `my-combo` | 20/20 | ~42 calls/min |
| `openrouter/cohere/north-mini-code:free` | 17/20 | ~43 calls/min |
| `sensenova/deepseek-v4-flash` | 3/4 (144 errors/run) | quota-bound |
| `sensenova/glm-5.2` | 0/6 after screening | quota-bound |

A 48-episode run needs ~192 model calls; every secondary provider exhausts its quota
partway through, and exhausted episodes end `stop=ProviderError` with `reward=0.000`.
`frontier.py` excludes them from the denominator, correctly -- a rate-limit failure
measures the provider, not the harness -- but the n is gone. At `-c 4` glm-5.2 gave 0/24
valid on both tiers; at `-c 1` with n=8 it retained 8/8 on tier3 and 3/3 on tier3 H_D, so
concurrency and burst size, not the model, drive the loss. verifiers has no throttle knob:
`-c` is the only concurrency control, and the client's retry storm ("reset after 2s")
amplifies exhaustion rather than absorbing it.

## Candidates rejected on capability, not just quota

- `openrouter/cohere/north-mini-code:free` -- 15 valid tier3 episodes, **0 solved**, every
  one `no_write`: it inspects, burns the budget, never edits. A floor measurement cannot
  discriminate a harness effect.
- `Tenxun/Deepseek-v4-flash` -- hangs on the first rollout at `-c 1` (15+ min), and reports
  a hard `concurrent limit exceeded: running=10 max=6`.
- `cl/*` -- the entire prefix returns 503 on this endpoint.
- `my-combo` -- 20/20 and quota-tolerant, but it is a router, so the answering model is
  not fixed across episodes and it cannot support a "which model" claim.

## To actually finish this

A second model with quota headroom for ~400 calls. That is an access question, not a
design question -- the design is written and the configs are in `eval_patch_m2_*.toml`.
With headroom, the run is 6 invocations of `-c 4 --run.name m2-{hA,hD}{1,2,3}`.