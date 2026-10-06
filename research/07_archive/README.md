# 07_archive — Superseded Material

This directory is where a document goes once a later commit has changed its
numbers. Nothing here is load-bearing; the load-bearing version is wherever it
currently lives.

## Contents at freeze time

This README only. No superseded document has been moved here, and that is recorded deliberately, not omitted.

The writeups under `tools/swe_lab/runs/` are still the canonical text for
E01–E08, and they are git-tracked, so their superseded versions are recoverable
from history without a copy here. The two known inconsistencies are recorded in
`05_process/failure_ledger.md`:

- **F11** — `swe_7_banner.md` presents 0 / 5 / 5 / 15 / 25% as a result. Two of
  those numbers are single-seed artefacts. The freeze commit `a5975ac74`
  superseded the writeup; the writeup itself was not edited, because a writeup
  is a dated artifact and should not be quietly rewritten.
- **F12** — `swe_stage_conclusion.md` quotes a conditional write rate from before
  the metric fix `4b6854707`. `swe_harness_triangle.md` holds the corrected
  figures and is authoritative for that metric.

## Rule

Do not edit a writeup to make an old number correct. Record the correction here
or in the failure ledger, and let the writeup keep its original date. A research
archive in which every number looks current is an archive that cannot be audited.