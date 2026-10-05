# AI Sessions Index

The raw session exports live in `01_raw/ai-sessions/`. This index is the only
thing that should be read to understand the research conversation; the exports
are ~28 MB each of JSONL and should be opened by script, not by hand.

## Extracts

| File | Role | Size | Records | Unique prompts | Span |
| --- | --- | --- | --- | --- | --- |
| `dsh-session/session.v4.jsonl` | main conversation, continued to the end | 28.9 MB | 8,982 | 85 | 2026-10-02 17:13:52 to 2026-10-06 06:17:21 |
| `subagents/55978c6a-46c0-441b-8f1c-31afcbf12348/session.v4.jsonl` | fork export | 29.1 MB | 9,233 | 81 | to 2026-10-05 23:41:53 |
| `subagents/e374ab45-75e4-4c58-998d-7c8f95e29656/session.v4.jsonl` | fork export | 28.2 MB | 8,808 | 81 | to 2026-10-05 22:50:06 |

Model in all three: `LunXun` (`router`). Tool-use profile (main):
`pwsh` 2370 calls, `job_output` 406, `read` 290, `grep` 98, `todo_write` 50,
`edit` 30, `job_kill` 28, `write` 26.

## Important: these are three copies, not three conversations

The two `subagents/` exports are forks of the main conversation, not independent
research threads. Of 81 unique user prompts in either fork, **77 are shared
verbatim** with the main export. The three files therefore document **one
research conversation**, exported three times. Do not treat them as three
replications of a research process, and do not count them as three independent
sources of a decision.

Total across the three files: 406 `user/message` records, of which 302 survive
after dropping system-injected context, and 88 in the main file after also
dropping compaction checkpoints and model-change notices.

## Record schema

```
{ "type": "user/message", "seq": N, "time": <epoch ms>,
  "data": { "role": "user", "id": "<message id>",
            "content": [ { "type": "text", "text": "..." } ] } }
```

- `type` values: `user/message`, `assistant/message`, `tool/call`, `tool/result`,
  `step/start`, `step/end`, `turn/start`, `agent/inbox/spliced`,
  `compaction/prune`, `request/header`.
- Session metadata: the `session` record carries `id`, `createdAt`, `cwd`,
  `agentPreset`, `version`, `isSeeded`.
- `data.model` is **not** populated; the model is only in `request/header`.

## Filter rules for extracting human intent

Four things must be dropped before the file is readable as a research log:

1. `<system-reminder>...</system-reminder>` blocks — these are harness context,
   not the user.
2. `Current runtime context...` messages — sandbox/policy snapshots.
3. Compaction checkpoints (`<compacted-summary>`) — useful for state, but they
   are model-written, not human-written.
4. `[model changed: ...]` notices.

After filtering, the main export holds the 88 substantive user prompts that
drove every decision in `decision_log.md` and the prompt-origin IDs in
`hypothesis_origin.md`.

## What the sessions are for

The sessions are the only record of *why* a hypothesis was proposed, *why* a
decision was made, and *when* a framing was corrected. Three entries matter
most and are worth opening directly:

- The **planner-framing retirement** (D03) — the conversation that produced
  "0/120 planner turns wrote a real plan".
- The **Phase 4 freeze** (D10) — "不要再让 SFT 继续钻", and the three-layer
  framing that replaced it.
- The **role-claim narrowing** (D15) — "不要直接写成'harness 必须中断模型'".

AI-session evidence is never primary evidence. It explains design intent; it
cannot establish a result. Every claim in `claim_evidence_matrix.md` resolves
to a run directory or a commit.