# 01_raw — Raw Evidence

**Rule: nothing in this directory is edited for appearance.** Raw material is
kept verbatim, or is not kept at all. This directory holds pointers, hashes, and
extracts — it is not a copy of the working tree.

## What lives here

| Path | Contents |
| --- | --- |
| `manifest.tsv` | Every run directory, every session export, every canonical writeup: sha256 prefix, byte size, mtime, file count, and role. Generated at archive time. |
| `ai-sessions/user_prompts_extract.txt` | The 88 substantive user prompts from the main session export, with message IDs and timestamps. Everything else in the export (harness context, compaction checkpoints, tool results) is dropped. |
| `git-export/` | Empty by design. The Git repository **is** the primary evidence for commit history; duplicating it here would create a second, drifting source of truth. `00_index/git_snapshot.md` and `00_index/git_milestones.md` point into it instead. |
| `runs/`, `traces/`, `logs/` | Empty by design. 176 run directories live under `outputs/`, which is **gitignored** — they are reachable by path and covered by `manifest.tsv`, but are not copied here. |

## Why nothing is copied

1. `outputs/` is gitignored, so copying it into a tracked directory would create
   a duplicate that git cannot see and that no one can audit.
2. The session exports are ~86 MB total. They are reachable at their original
   paths and hashed in `manifest.tsv`.
3. A copy drifts. A pointer does not.

The one thing that **is** copied is the prompts extract, because the only
research-relevant part of 86 MB of JSONL is 280 KB of human text.

## Immutability

- Do not edit a file in this directory to make it clearer. Annotate in
  `02_experiments/` instead.
- Do not delete a run directory without recording it in `manifest.tsv`.
- If a run is re-run, the new directory gets its own row. The old row stays.