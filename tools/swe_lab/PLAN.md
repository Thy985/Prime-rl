# SWE Agent Environment / Harness — plan and roadmap (spec level)

Positioning, after review: **do not rebuild Verifiers.** `verifiers` is already
vendored in this repo at `deps/verifiers` (0.3.2.dev137) and `verifiers/v1`
already owns Task / Taskset / Harness / Runtime / Trace / Episode. This project
builds the **experiment-control and audit layer** on top of those abstractions,
and validates how they land on a real agent task.

## 0. Where we are

Reverse-text is closed. What transfers:

| Result | Status |
| --- | --- |
| RL plumbing (sampler -> verifier -> reward -> advantage -> LoRA -> delta) | verified on one GPU |
| SFT produced a capability (0/18 -> 7/18 exact, short strings) | verified |
| Reward ablation V1 lcs / V2 pos / V3 lcs+exact-bonus | done at a non-destructive lr |
| "Reward rises and transfers" (Experiments A/B) | **RETRACTED** — protocol bug |
| "Every reward destroys the capability" (lr 1e-4) | **RETRACTED** — optimiser artifact |

Four lessons, each of which already cost a wrong conclusion:

1. **Protocol invariance** — one entry point for prompt serialisation, generation
   config and verifier version across training/inference/eval.
2. **Verify the verifier first** — terrain/corpus audits before any training.
3. **Offline ordering metrics do not predict learning.**
4. **Establish a non-destructive update regime first**, or an ablation is
   uninterpretable.

SWE terrain so far (`tools/swe_lab/terrain.py`): two seeded defects, a structured
verdict (per_test, fixed_targets, regressions, tampered, timed_out) and a
ten-repair audit. Headline: **"the test suite is green" is not a verifier** —
exit-code and raw-pass-fraction rewards pay a tampering repair 1.000 while a
genuine partial fix scores 0.571.

## 1. Objective and hard boundary

Objective: make **one agent episode faithfully convertible into a record** that is
replayable, scored by an audited verifier, and consumable as a training example.

Hard boundaries, recorded rather than fought:

- **8 GB single GPU + a 0.6B base cannot train a real SWE agent.** This phase is
  environment / evaluation / data infrastructure. Any training here is limited to
  SFT/distillation on reference trajectories; RL on the harness is gated on a
  larger machine (Phase 4).
- **No container runtime on this box** (docker/podman/apptainer absent, daemon
  unreachable), and every real built-in harness declares `NEEDS_CONTAINER = True`
  (only `bash`/`null` override to False). This gates Phase 1B; see 2.2.

## 2. Architecture

### 2.1 Three tiers of fact — never a second source of truth

    raw agent/runtime stream        RAW FACT        archived verbatim, never parsed twice
            |
    verifiers.v1 Trace / Episode    SEMANTIC FACT    task, group, run/work, policy,
                                                     runtime, timing, tool defs, messages
            |
    SWE experiment record           INDEX/ANALYSIS   only what the layers above do not
                                                     carry: tree hashes, verdict, reward

The experiment record is an **index over the Episode**, not a competing trace. It
must be regenerable from archived artifacts at any time; if it ever disagrees with
the Episode, the Episode wins. This is the rule that prevents the reverse-text
failure of two slightly different facts leading to protocol tinkering.

What verifiers v1 already provides (so it must NOT be re-implemented): `TaskData`
with `prompt/system_prompt/workdir/network_allow/network_block/artifacts` and
`TaskTimeout{setup,agent,finalize,scoring}` and `TaskResources`; `Task.hash()`;
`Taskset.load()`; `Harness` with capability flags (`NEEDS_CONTAINER`,
`EXECUTES_CODE`, `SUPPORTS_RESUME`, `SUPPORTS_TOOL_INTERCEPTION`, `APPENDS_SYSTEM_PROMPT`)
and `setup/launch/metrics/resume/cleanup`; `Runtime` implementations
(subprocess, container, docker, modal, prime); `Trace` with `Timing`
(boot/setup/agent{model,harness}/finalize/scoring), `Error`, `AgentInfo`,
`TraceTask`; `Episode` as a durable artifact carrying env, task, group, run/work
and policy span. Built-in harnesses include `claude_code`, `codex`,
`mini_swe_agent`, `terminus_2`, `bash`, `null`.

### 2.2 Deployment reality (measured, not assumed)

- `claude` in WSL is a **Windows PE binary** started through WSL interop, so its
  tools run as Windows processes; a WSL path is only a UNC path to it.
- `codex` cannot run in WSL at all (shim needs `node`; WSL has none).
- `ClaudeCodeHarness` does **not** shell out to `claude -p`: it installs
  `@anthropic-ai/claude-code` + `@anthropic-ai/claude-agent-acp` via `npm install`
  **inside the runtime** and drives Claude over **ACP**.
- It inherits `NEEDS_CONTAINER = True`: on a host/subprocess runtime it would leak
  host state (auth, config, processes) in both directions.
- Windows has python 3.12 (uv-managed) but no pytest; `uv` is present.

Consequence: the canonical path (built-in `claude_code` harness) is **blocked on
this box until a container runtime exists**. Two unblocked routes:

- **Route G (do first, no container, no API cost):** Golden Episode + the whole
  closure on the `bash`/`null` harness with the **subprocess** runtime, which is
  deterministic and exercises Task -> Runtime -> Episode/Trace -> record ->
  verifier -> verdict -> replay.
- **Route A (temporary, only if a live episode is needed before a container):**
  drive `claude.exe` on the Windows side against a Windows-path sandbox and treat
  it as a **stand-in harness** behind the same interface, clearly marked as such.
- **Route C (the real fix):** provide docker in WSL2, then use the built-in
  `claude_code` harness and delete the stand-in. Preferred as soon as SWE becomes
  the main line.

### 2.3 What "Environment" means here

An environment is not a directory. It is:

    initial state     repository, files, dependencies, services
    action interface  shell, file editing, tools exposed to the model
    transition        action -> changed state
    observation       stdout/stderr, files, test results
    terminal          success, failure, timeout, budget exhaustion

## 3. SWE experiment record (index layer)

    run_id, task_id, task_hash
    env_fingerprint   os, path_policy, shell, locale, line_endings, python,
                      pytest, git, agent, harness, runtime, fixture_hash,
                      task_hash, tool_policy, network_policy, workdir
    episode_ref       pointer to the verifiers Episode (semantic fact)
    raw_ref           pointer to the untouched raw stream
    initial_state_hash, final_state_hash, diff
    verdict           per_test, fixed_targets, regressions, tampered, timed_out
    reward            target_fix_fraction, shaped
    timing/tokens     copied from Trace.Timing, never recomputed

`initial_state_hash` is mandatory: `diff = final - baseline` is meaningless without
proof of the baseline the episode actually started from. It was missing from the
first draft.

Invariants: verdict is computed from the **final repository state**, never from the
agent's self-report; every record carries `env_fingerprint` so two numbers from
different protocols are never compared; the raw stream is never mutated.

## 4. Roadmap

**Phase 0 — terrain and audit. DONE.**

**Phase 1A — environment contract + Golden Episode.**
Do: implement the fixture as a verifiers `Taskset`/`Task`; `run_dir` with
`initial/ work/ final/ task.json env_fingerprint.json`; record
`initial_state_hash`; then build a **Golden Episode** — a known task, a known
correct repair, a known final state and a known verdict — and require
adapter -> schema -> verifier -> reward to reproduce it exactly.
Acceptance: the golden record round-trips; the verifier reproduces the known
verdict; a deliberately corrupted final state is detected (negative control).
Rationale: this is the blame-isolation boundary. Without it, a live failure cannot
be attributed to agent, adapter, environment or verifier — the exact trap already
paid for once.

**Phase 1B — one live episode + replay closure.**
Do: 1 task x 1 agent x 1 harness = 1 episode, on the built-in harness where a
runtime allows, otherwise the marked stand-in. Then: live verdict, then rescore
from the archived final state, and require **live verdict == replayed verdict**.
Acceptance: the full `run_dir` exists (task.json, env_fingerprint.json,
raw_stream.jsonl, trajectory/record, initial_state.json, final_state.json,
diff.patch, verdict.json, reward.json) and the two verdicts are identical.

**Phase 2 — difficulty ladder.**
Tiers: single-file two-defect (have), multi-file coordinated change, long-horizon
with a regression trap and a misleading test. Every tier fixes an **action budget,
time budget and tool budget**, so a harder tier is genuinely harder rather than
just given more time. Audits are per tier.

**Phase 3 — reference trajectories; harness evaluation begins here.**
Fix model, taskset, environment, verifier and budgets; vary the harness
(Harness A vs B) over 10-30 tasks; measure success, partial, regression, tamper,
timeout, steps, tokens, latency, recovery.
Outputs stay split: **raw trajectories** and **curated SFT views** are different
artifacts. A trajectory is not a training example: it passes through
filter -> turn selection -> masking -> training example, and advertised tool
definitions belong to that transformation, not to the record.

**Phase 4 — decision gate (do not pre-commit).** Larger GPU: RL on the harness
with the audited reward, reusing reverse-text discipline. Otherwise
SFT/distillation only. "Cannot train here" is an acceptable recorded outcome.

**Phase 5 — environment generalisation.** Tool misuse, cross-file partial credit,
longer horizons, a second task family.

## 5. Anti-scope-creep rules

1. One environment at a time; no new tier until its verifier audit passes.
2. The agent only ever touches a sandbox copy, never the working repo.
3. Environment fingerprint on every record; never compare across versions.
4. Any reward used for training must have passed the terrain audit first.
5. Verdicts come from the final repository state, never from agent self-report.
6. The Episode is the semantic fact; the experiment record is derived and
   regenerable. Never let a second trace become authoritative.
7. Record resource boundaries instead of forcing the full chain.

## 6. Open questions

- **Container runtime** (docker in WSL2) — required for the canonical
  `claude_code` harness; without it Phase 1B runs on Route A or Route G only.
- Reference agent for Phase 3: `claude_code` only, or also `codex` (two ceilings is
  better calibration, doubles cost).
- Tamper-pressure task variant ("make the suite pass") to harvest genuine
  reward-hacking trajectories as a labelled negative class. Recommended.
- pytest on the Windows side: install once, or `uv run --with pytest` per run.
---

## Phase 1B status (measured)

Achieved: a real verifiers Episode runs and is scored by the audited verifier.

    Env swe-lab ready in 6.5s (num_tasks=1)
    rollout start: task=0 harness=null runtime=subprocess
    rollout done:  task=0 reward=0.000 turns=1 stop=agent_completed
    Evaluated swe-lab (Step 0) | 44.2s | Reward 0.0000 | Truncation 100.0%
    episode=c192516f5621 trace=cc0784a29b94 env=swe-lab reward=0.000 tokens=535/2048

`tools/swe_lab/index_episode.py` now derives the experiment record FROM the
verifiers episode index (ids, reward, tokens, turns, stop condition, truncation
copied verbatim; only task identity, env fingerprint and replay metadata added),
so the record is an index over a genuine Episode rather than a parallel structure.

### The replay closure must be split in two

`vf-replay` is documented as re-scoring "judges + trace-only signals; **no
runtime**". A reward that executes the suite -- this task's `target_fix_fraction`
-- is therefore **outside its scope**. Two replay modes, not interchangeable:

| reward kind | replay |
| --- | --- |
| trace-only signals, judges | `vf-replay` over saved `traces.jsonl` |
| **executing (this task)** | re-run the verifier over the **archived repository state** |

Proven on the deterministic episodes: `golden.py` and `episode_scripted.py` both
re-derive an identical verdict from the frozen final state. Not yet proven on a
live episode, because prime-rl's `eval` monitor persists only
`monitors/file/traces/stream.index.jsonl`; full `traces.jsonl` (with the model's
reply, which is what the executing reward re-applies) is written by the
**`vf-eval`** CLI path instead.

### Remaining for Phase 1B acceptance

1. Run through `vf-eval` (verifiers-native config, no `[[source]]`) so full
   `traces.jsonl` is persisted.
2. Write the executing-replay runner: read the saved trace, re-extract the
   proposed file, re-run the verifier, and require
   `live reward == replayed reward`.
3. Only then is "live verdict == replayed verdict" satisfied for the live episode.

### Capability note

The 0.6B scores 0 because it exhausts the 2048-token cap without emitting a
complete fenced file (`truncated: true`, `output_tokens: 2048`). This is the
expected capability boundary, not a chain failure; capability probing is Phase 3.
