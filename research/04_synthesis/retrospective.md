# Retrospective

Five days, 82 commits, 8 canonical experiments, 176 run directories, n=60 at
the freeze point. Written as a review of the process, not a summary of the
results.

## What happened, in three movements

**Movement 1 — build something measurable (Oct 1–2).** A reward had to be
audited before it could be trusted; the audit found a verifier that paid a
tampering repair more than a real fix. Then a difficulty ladder, then the first
harness comparison, which produced the study's first headline: removing one tool
cost 44 points. All of this was also the study's first six measurement bugs.

**Movement 2 — find the mechanism (Oct 2–4).** A staged runtime outperformed the
free agent on real SWE-bench by 32 points. The mechanism was named, then renamed
twice: first "planner" (retracted on its own trace data — 0 of 120 planner turns
wrote a plan), then "affordance gating" (falsified by a 2×2), then "banner".
Along the way: a budget sweep that found the effect disappears at T=8, a second
model that reproduced the direction, and a distillation attempt that produced the
cleanest negative result in the archive.

**Movement 3 — test what survives (Oct 5–6).** Seven arms were run single-seed.
Replication to n=60 halved the headline, killed one of the four dimensions, and
left two paired results. The mechanism was settled as action allocation.

## The three things that changed

**1. The instrument is part of the study.** The largest single distortion found
was a validity rule from one evaluation mode leaking into another, silently
deleting the failures the budget had just created. It would have inverted a
conclusion about whether a budget creates headroom. Eight measurement bugs were
found before the mechanism work; every one of them changed an interpretation, and
two changed a headline number.

**2. n=1 is a hypothesis, not a result.** Every mechanism claim in this study was
first made at n=1, and every one was wrong or over-scaled. The 44-point effect
reversed at n=32. The 25-point effect halved at n=60. The role claim had to be
narrowed because it was being read further than the data supported. The habit
formed here — *name the claim, then buy the replication* — is the single most
transferable thing in this work.

**3. The question got smaller, not bigger.** The study started asking "does the
harness help?" and ended asking "which property of a per-turn injection is
load-bearing?" The narrowing was deliberate: the wide-set result and the budget
sweep both shrank the claim before the mechanism was named. The final answer is
weaker and more specific than the first answer, and that is progress.

## What was handled well

- **Stopping.** Seven of the recorded decisions were stops, and each was made
  while the attractive alternative was still in hand. Stopping research into
  affordance scheduling after the 2×2 — rather than buying one more variant —
  is what let Phase 7 exist.
- **The three-layer model.** Separating "the harness changes behaviour" from "the
  gate is not the mechanism" from "the injection's properties carry it" is what
  made the later work legible.
- **Pairing on instances.** The two claims that survived replication were both
  paired McNemar on the same 20 instances. Everything else in the archive is
  weaker than that.

## What was handled badly

- **The 2×2 was run at the wrong budget.** Phase 6's factorial was executed at
  T=4 on a task set where solve rates were 0–7.5%. It was underpowered by design
  of the operating point, not by choice of n. The conclusion had to be carried by
  a different budget plus a pilot replication. The operating point should have
  been chosen first.
- **Seven single-seed arms were written up as a headline.** The E07 writeup
  presents 0/5/5/15/25% as a result. Two of those numbers are seed artefacts. The
  writeup was not corrected at the time; the freeze commit superseded it. This
  is why the archive now carries a hypothesis ledger and a failure ledger
  alongside the writeups — the writeups were never going to be the index.
- **The cross-model leg was allowed to rot.** It was blocked, diagnosed
  correctly, fixed once, and abandoned. Three months of this archive could have
  been used differently, but the cost of keeping it alive was real. The honest
  filing is *untested*, and that is what it is.
- **Cross-document numbers were left inconsistent.** One writeup quotes a
  conditional write rate from before the metric fix. A reader who trusted that
  one page would have read a 54% vs 25% gap where the corrected figure is 100% vs
  100%. Metric fixes need a back-propagation step that was never done.

## If this were run again

1. Pick the budget and task set where signal exists **before** designing the
   factorial. A underpowered factorial is not a failed experiment; it is an
   experiment that has not been run.
2. Do not write up a mechanism study from single-seed arms. Report the seed, or
   report the replication.
3. Freeze writeups as *superseded* the moment a new commit changes their numbers,
   not when the study ends.
4. Budget time for the cross-model arm from the start. It was the one missing
   dimension that was never a mechanism question — just a replication question
   that required a working provider.