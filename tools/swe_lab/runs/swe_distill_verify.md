# Real-SWE distillation verification: dots3 H_D teacher -> Qwen3-0.6B student

Closes the "small-scale distillation check" the pilot left open: does the H_D
advantage (writes-at-all + recon-before-write, +32 pts on real SWE-bench Verified
under H_D vs bare H_A) transfer to a small student by SFT on the existing D_D
teacher data? Verification goal was behaviour-structure transfer, not solve rate.

## Pipeline (all on this host, no new infra)

1. Teacher data: the existing `outputs/swe_runs/sft_D/data/train-...parquet`
   (81 rows / 279 assistant turns, dots3 canonical solved traces from H_D).
2. Student: Qwen3-0.6B, LoRA r=8/alpha=32 on all q/k/v/o/gate/up/down proj,
   batch 2, max_steps 20 (sanity run: 40 row-visits over 81 rows). 4.6/8.0 GiB
   peak, ~10.4 s/step, loss 1.84 -> ~1.42. Checkpoint saved complete.
   (`outputs/swe_runs/pi-real-D-lora`, dcp tree)
3. Export: `tools/swe_lab/export_pi.py` replays the trainer resume path and writes
   a PEFT adapter (`outputs/swe_runs/pi-real-D-lora-adapter`, 392 keys).
   Fix landed this session: adapter tensors are FSDP DTensors; full_tensor().cpu()
   before safetensors (mirrors the filesystem.py LoRA broadcast path).
4. Merge: `tools/swe_lab/merge_adapter.py` folds W += (alpha/r) * B@A into the base
   on CPU -> plain HF checkpoint `outputs/swe_runs/pi-real-D-hf`.
5. Eval: native vLLM serve (needs `VLLM_WSL2_ENABLE_PIN_MEMORY=1`,
   `VLLM_USE_FLASHINFER_SAMPLER=0`, `--enable-auto-tool-choice --tool-call-parser
   hermes`, `--max-model-len 16384` for the 8192-token sampling cap) + the same
   eval_sft_local.toml used for the pilot: swe_bench taskset, bash harness,
   max_turns=4, 5 gated django instances x 2 groups, bare H_A (no phase protocol).

## Result

| model | resolve | tool calls | turns | stop | out tokens/ep |
|---|---|---|---|---|---|
| Qwen3-0.6B untrained | 0/10 | 0/10 ep | 1 (all) | agent_completed | ~530 |
| Qwen3-0.6B + pi-D LoRA | 0/10 | 0/10 ep | 1 (all) | agent_completed | ~1270 |

Pilot comparison grid (dots3): H_A 2/16 = 12%, H_D 7/16 = 44%.

Merge is confirmed active: same prompt, the SFT model's analysis text differs from
the untrained base (and output length doubles). The distilled model did NOT learn
to call tools: every episode ends after one assistant turn that only produces
prose (thinking + rephrased issue), zero bash/edit invocations, so no write
behaviour and no solve.

## Interpretation

- The lofted harness effect (H_D > H_A) comes from the *agent taking actions*:
  writing files and running the repo's own tests. A 0.6B student that never emits
  a tool call cannot show it regardless of the reward signal.
- Two compounding causes. (1) Sanity-scale SFT: 20 steps is far from convergence
  and the 81-row corpus is all dots3-format tool traces; nothing in it teaches the
  Qwen3 (hermes-parsed) tool-call syntax the eval harness requires. (2) Floor
  effect: the untrained 0.6B already scores 0 and ends in one turn, so the D_D
  signal had no observable gradient to move.
- Verdict for the parent question: distillation from big-teacher H_D traces does
  not cheaply transplant the harness effect at this scale. Policy distillation
  stays unwarranted unless a stronger setup (converged SFT on the correct tool
  format, or a model that already emits tool calls) is on the table.

## Reproduce

    # serve baseline or merged checkpoint (model dir or HF id)
    VLLM_WSL2_ENABLE_PIN_MEMORY=1 VLLM_USE_FLASHINFER_SAMPLER=0 \
      uv run vllm serve <model> --port 8000 --gpu-memory-utilization 0.80 \
      --max-model-len 16384 --attention-backend flash_attn \
      --served-model-name qwen3-06b-XXX --enable-auto-tool-choice --tool-call-parser hermes

    SWE_REAL_PY=/tmp/swe_deps/django_env/bin/python DUMMY_API_KEY=x \
    PYTHONPATH=$PWD/tools/swe_lab_env \
      uv run eval @ tools/swe_lab/eval_sft_local.toml \
      --model qwen3-06b-XXX --run.name <tag> -c 1 --clean
