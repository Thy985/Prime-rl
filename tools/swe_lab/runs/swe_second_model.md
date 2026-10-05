# External validity: a second model on real SWE

The real-SWE evidence so far is one model (dots3-note-prev) on one task set (5
django instances). Two external-validity gaps: is the harness effect model-
specific, and does it hold on a wider task distribution?

## Second model: space-bunny-alpha

`openrouter/stealth/space-bunny-alpha` — a 7B-class model, same "can code but
often fails" profile as dots3 (chosen to avoid the saturated-model regime where a
harness effect cannot be measured). Same 5 gated django instances, same episode
grid (16 per arm), T=4, -c 1.

| harness | dots3 (27B?) | space-bunny (7B) |
|---------|-------------|------------------|
| H_A     | 2/16 = 12%  | 3/16 = 19%       |
| H_D     | 7/16 = 44%  | 5/16 = 31%       |
| gap     | +32pt       | +12pt            |

The effect is present in both directions of the capability axis: both models
start from a low baseline (12-19%), neither saturates, and the H_D gain is
positive for both (+32, +12). The gain is smaller for the weaker model, which is
the expected direction -- a model that is better at following a recon->edit
structure to begin with has more to gain from the structure being enforced.

Space-bunny's trajectories show the same structural signature: in the PLAN phase
it runs 9x `cd /` and 3x `find /` (it is looking for the repository, not in it),
and it does reach the execute phase and edit (3 edit calls). Its FEEDBACK phase
attempts `cd tests` to run the suite (2 TEST runs) — closer to the instructed
behavior than dots3, but the commands do not resolve to a working test invocation.

One HarnessError (turns=1, stop=HarnessError) appeared on task 0 of the first
H_D episode; the retried episode ran normally. No systematic provider failures.