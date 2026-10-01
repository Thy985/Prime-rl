# SWE Agent Environment / Harness — plan and roadmap

Scope: build the *environment, verifier and trajectory infrastructure* for a
stateful, tool-using agent. This is the successor to the reverse-text lab.

## 0. Where we are

Reverse-text is closed and graduated. What it produced, and what transfers:

| Result | Status |
| --- | --- |
| RL plumbing (sampler -> verifier -> reward -> advantage -> LoRA -> delta) | verified on one GPU |
| SFT produced a capability (0/18 -> 7/18 exact on short strings) | verified |
| Reward ablation V1 lcs / V2 pos / V3 lcs+exact-bonus | done, at a non-destructive lr |
| "Reward rises + transfers" (Experiments A/B) | **RETRACTED** — protocol bug |
| "Every reward destroys the capability" (lr 1e-4) | **RETRACTED** — optimiser artifact |

Four lessons that must be carried into this phase, because each one cost a wrong
conclusion:

1. **Protocol invariance.** Training, inference and offline evaluation must share
   one entry point for tokenizer, prompt serialisation, extraction, generation
   config and verifier version. A mismatched prompt format produced a completely
   wrong experimental conclusion.
2. **Verify the verifier before anything else.** Corpus/terrain audits first;
   training only after the signal is shown to be sound.
3. **Offline ordering metrics do not predict learning.** LCS was the best graded
   shaper offline and yet transferred worst in GRPO.
4. **Establish a non-destructive update regime first.** Until that exists, a
   reward ablation is uninterpretable.

SWE terrain so far (`tools/swe_lab/`): a two-defect fixture with a structured
verdict (per-test, fixed_targets, regressions, tampered, timed_out) and an audit
over ten repairs. Headline: **"the test suite is green" is not a verifier** —
scoring the pytest exit code or raw pass fraction pays a test-tampering repair
1.000 while a genuine partial fix scores 0.571.

## 1. Objective and hard boundary

Objective: make **one agent episode** faithfully convertible into a record that is
(1) replayable, (2) scored by an audited verifier, and (3) consumable as a
training example.

Hard boundary, recorded rather than fought: **8 GB single GPU + a 0.6B base model
cannot train a real SWE agent.** A 0.6B policy scores ~0 on any genuine SWE task.
So this phase is **environment / evaluation / data infrastructure**, not "SWE RL".
Any training on this box is limited to SFT/distillation on reference trajectories.
RL on the harness is gated on a larger machine (Phase 4 decision gate).

## 2. Architecture

Five layers, each replaceable without touching the ones above it:

    L5 analysis/scoring     offline, WSL          verdict stats, reward audit
    L4 adapter + schema     offline, WSL          stream-json -> trajectory schema
    L3 agent runner         Windows (see 3.1)     claude / codex / future local policy
    L2 verifier             offline, WSL          terrain verdict + audited reward
    L1 environment          Windows sandbox dir   repo copy, test runner, timeout

Deployment reality found by measurement:

- `claude` in WSL is a **Windows PE binary** (`bin/claude.exe`) started through WSL
  interop, so its tools run as **Windows** processes. A WSL path is only a UNC path
  to it.
- `codex` cannot run in WSL at all (its shim needs `node`; WSL has none).
- Windows has python 3.12 (uv-managed) but **no pytest**; `uv` is present.
- The WSL repo is reachable from Windows over `\\wsl.localhost\...`.

Therefore, for now: **the agent runs on the Windows side against a Windows-path
sandbox, and scoring runs in WSL.** That boundary is the single largest source of
potential measurement contamination in this design, which is why the adapter and
the environment fingerprint (below) are mandatory rather than optional.

### 2.1 Deployment routes

- **Route A (use now):** sandbox at `D:\swe_runs\<id>`; test runner via
  `uv run --with pytest pytest`; agent driven non-interactively; final repo state
  copied back to WSL for scoring. Zero changes to the training environment.
- **Route C (adopt if SWE becomes the main line):** install node in WSL and
  `npm i -g @anthropic-ai/claude-code` to get a **native Linux** claude, so agent,
  test runner, verifier and a future local vLLM policy all live in one
  environment with no path translation.

Decision trigger for C: the first phase that needs many runs (Phase 2 or later),
or the first time a Windows/WSL discrepancy is suspected of changing a result.
Maintaining a translation layer across two OSes is exactly the class of bug that
invalidated Experiments A/B.

## 3. Trajectory schema (the central deliverable)

One record per episode, append-only, with the raw agent stream preserved verbatim
and never mutated:

    run_id            stable id
    task_id           which fixture/tier
    agent             {name, version, model}
    env_fingerprint   {os, python, pytest, git, fixture hash, tool policy}
    started_at, duration_s, exit_status
    steps[]           {index, kind: message|tool_call|tool_result,
                       tool, args, observation, files_touched, cwd}
    diff              final unified diff against the task baseline
    final_state_hash  content hash of the sandbox tree
    verdict           {per_test, fixed_targets, regressions, tampered,
                       timed_out, exit_code}
    reward            {target_fix_fraction, shaped}
    raw_ref           path to the untouched stream-json

Invariants: every record carries the env fingerprint (so two numbers from
different protocols are never compared); the verdict is computed from the
**final repository state**, never from the agent's own claim of success; the raw
stream is the ground truth for the step list.

## 4. Roadmap

**Phase 0 — terrain and audit. DONE.**
Two-defect fixture, structured verdict, ten-repair audit, five candidate rewards.
Acceptance met: naive "tests pass" rewards are proven exploitable; two rewards
pass all seven properties.

**Phase 1 — adapter and one end-to-end episode.**
Do: trajectory schema; stream-json -> schema adapter; one sandboxed agent run;
verdict + reward computed from the final state.
Acceptance: exactly one schema-valid record exists; its verdict is reproducible by
re-running the verifier on the stored final state; raw stream archived; the
agent's tamper behaviour is recorded either way.
Deliverable: `tools/swe_lab/schema.py`, `tools/swe_lab/adapters/claude_stream.py`,
one record under `outputs/swe_runs/`.

**Phase 2 — difficulty ladder.**
Do: at least three tiers — single-file two-defect (have), multi-file coordinated
change, and long-horizon with a regression trap and a misleading test. Each tier
ships baseline repairs (no-op / partial / full / regression / tamper) so the
reward gradient is audited **per tier**, not just once.
Acceptance: for every tier, the terrain audit passes; a no-op scores at the floor
and the tamper repair is not paid.
Reasoning: two bugs is a ceiling test for a frontier agent, so the tier ladder is
what turns this from plumbing into a capability probe.

**Phase 3 — reference trajectories and the frontier.**
Do: N runs per tier with the reference agent; record solve rate, steps, and where
it degrades. Keep trajectories as SFT data.
Acceptance: a solve-rate curve across tiers, every record schema-valid and
verifier-scored, and a written statement of which tier is the current frontier.

**Phase 4 — decision gate (do not pre-commit).**
If a larger GPU is available: RL on the harness with the audited reward, reusing
the reverse-text discipline (non-destructive regime first, reward ablation only
after). If not: SFT/distillation on the Phase 3 reference trajectories for the
local model, with protocol-invariant evaluation. Recording "cannot train here" is
an acceptable outcome; forcing it is not.

**Phase 5 — environment generalisation.**
Tool misuse, partial credit spanning files, longer horizons, and a second task
family (so the verifier is not fitted to one fixture).

## 5. Anti-scope-creep rules

1. One environment at a time; no new tier until its verifier audit passes.
2. The agent only ever touches a sandbox copy. Never the working repo.
3. Protocol/environment fingerprint on every record; never compare across versions.
4. Any reward used for training must have passed the terrain audit first.
5. Verdicts come from the final repository state, never from agent self-report.
6. Record resource boundaries instead of forcing the full chain.

## 6. Open questions

- Route A vs Route C (see 2.1) — A is fine for Phase 1; the trigger for C is a
  high run count or a suspected cross-OS discrepancy.
- Reference agent: claude only, codex only, or both (two ceilings is better for
  calibration, but doubles cost and needs the codex-on-Windows path).
- Whether to add an explicit **tamper-pressure** task variant ("make the suite
  pass") to harvest genuine reward-hacking trajectories rather than hand-written
  ones. Recommended: yes, as a labelled negative class, in Phase 3.
- pytest on the Windows side: install once into the uv-managed environment, or
  use `uv run --with pytest` per run (slower, no persistent change).