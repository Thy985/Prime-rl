"""Export an SFT run's final dcp checkpoint as a HF-servable safetensors dir.

The trainer saves its final checkpoint as a torch.distributed.checkpoint tree
(outputs/<run>/checkpoints/step_<N>/trainer) holding the FSDP-wrapped, fused
training-format weights. vLLM cannot load that; this tool replays the trainer's
resume path (model + dcp load, skipping optimizer/scheduler/progress state) and
then runs the same conversion the RL weight-broadcast path uses
(convert_state_dict_to_hf + save_state_dict_parallel) to write sharded
safetensors + config.json + tokenizer for serving.

Run it exactly like the trainer (single node, one rank):

  uv run torchrun --nproc-per-node=1 -m tools.swe_lab.export_pi \
    @ tools/swe_lab/sft_real_D.toml --out outputs/swe_runs/pi-real-D-hf

The config's run.name points at the trained run; --out is where the HF dir goes.
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

import torch
import torch.distributed as dist
from torch.distributed.tensor import DTensor

from prime_rl.configs.sft import SFTConfig
from prime_rl.configs.trainer import CheckpointConfig
from prime_rl.trainer.ckpt import setup_ckpt_manager
from prime_rl.trainer.model import setup_model
from prime_rl.trainer.parallel_dims import get_parallel_dims, resolve_ep
from prime_rl.trainer.utils import setup_torch_distributed
from prime_rl.trainer.world import get_world
from prime_rl.utils.config import cli
from prime_rl.utils.cp import setup_context_parallel
from prime_rl.utils.logger import setup_logger
from prime_rl.utils.process import set_proc_title
from prime_rl.utils.utils import clean_exit, get_all_ckpt_steps
from prime_rl.utils.weights import convert_state_dict_to_hf, save_state_dict, save_state_dict_parallel


@clean_exit
def export(config: SFTConfig, out_dir: Path) -> None:
    world = get_world()
    logger = setup_logger(config.log.level or "info", json_logging=config.log.json_logging)
    logger.info(f"Exporting SFT weights from run {config.run_dir}")

    setup_torch_distributed(
        timeout=timedelta(seconds=config.dist_timeout_seconds),
        enable_gloo=config.model.fsdp_cpu_offload or config.model.full_offload is not None,
    )
    torch.set_float32_matmul_precision(config.matmul_precision)
    resolve_ep(config.model)
    parallel_dims = get_parallel_dims(config.model, config.data.seq_len)

    # Weight-only restore: no optimizer/scheduler/progress state needed.
    config.ckpt = CheckpointConfig(skip_optimizer=True, skip_scheduler=True, skip_progress=True, skip_dataloader=True)
    ckpt_manager = setup_ckpt_manager(config.run_dir, config.ckpt, resume=None)
    steps = get_all_ckpt_steps(ckpt_manager.ckpt_dir)
    if not steps:
        raise SystemExit(f"no checkpoints found under {ckpt_manager.ckpt_dir}")
    step = max(steps)
    logger.info(f"Loading final checkpoint step {step}")

    model = setup_model(config.model, parallel_dims, loading_from_checkpoint_later=True)
    if parallel_dims.cp_enabled:
        setup_context_parallel(model, config.model, parallel_dims)
    if config.model.lora is not None:
        from prime_rl.trainer.lora import get_lora_state

        get_lora_state().reset_adapter_parameters()
    ckpt_manager.load(step, model, [], None, None)
    logger.info("Checkpoint loaded")

    if config.model.lora is not None:
        # LoRA run: ship the adapter (PEFT-shaped safetensors + config). The
        # serving path merges it into the base weights (merge_adapter.py).
        from prime_rl.trainer.lora import get_lora_state, save_lora_config

        adapter = get_lora_state().adapter_state_dict()
        adapter = {
            key: (
                value.full_tensor().bfloat16().cpu()
                if isinstance(value, DTensor)
                else value.bfloat16().cpu() if value.is_floating_point()
                else value
            )
            for key, value in adapter.items()
        }
        if world.is_master:
            save_state_dict(adapter, out_dir, save_sharded=False, adapter=True)
        if world.is_master:
            save_lora_config(
                model,
                out_dir,
                rank=config.model.lora.rank,
                alpha=config.model.lora.alpha,
                dropout=config.model.lora.dropout,
            )
        dist.barrier()
        logger.success(f"Exported LoRA adapter to {out_dir}")
        return

    logger.info("Converting to HF layout")
    state_dict = {k: v.detach() for k, v in model.state_dict().items()}
    hf_sd = convert_state_dict_to_hf(model, state_dict)
    hf_sd = {
        key: value.bfloat16() if value.is_floating_point() else value
        for key, value in hf_sd.items()
    }
    save_state_dict_parallel(hf_sd, out_dir)
    if world.is_master:
        from transformers import AutoConfig, AutoTokenizer

        AutoConfig.from_pretrained(config.model.name).save_pretrained(out_dir)
        AutoTokenizer.from_pretrained(config.model.name).save_pretrained(out_dir)
    dist.barrier()
    logger.success(f"Exported HF checkpoint to {out_dir}")


def main() -> int:
    set_proc_title("SFTExport")
    # Pull --out out of the argv before cli() sees it (cli() would reject a key
    # that is not a SFTConfig field). Everything else -- the @ config file and
    # dotted overrides like --run.name -- flows straight to cli().
    argv = sys.argv[1:]
    out_dir: Path | None = None
    rest: list[str] = []
    i = 0
    while i < len(argv):
        if argv[i] == "--out":
            out_dir = Path(argv[i + 1])
            i += 2
        elif argv[i].startswith("--out="):
            out_dir = Path(argv[i].split("=", 1)[1])
            i += 1
        else:
            rest.append(argv[i])
            i += 1
    if out_dir is None:
        raise SystemExit("--out is required")
    config = cli(SFTConfig, args=rest)
    export(config, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
