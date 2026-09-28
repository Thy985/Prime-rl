"""CPU-only export of a prime-rl LoRA SFT DCP step_<N>/trainer checkpoint to a
PEFT/HF adapter dir (adapter_model.safetensors + adapter_config.json) that
`uv run inference` can load via /load_lora_adapter for a standalone eval.
"""
import argparse
import json
import re
from pathlib import Path

import torch
from safetensors.torch import save_file
from torch.distributed.checkpoint import FileSystemReader, load as dcp_load

METADATA_KEY_RE = re.compile(
    r"^app\.model\.(model\..*?\.(?P<proj>[A-Za-z0-9_]+)\.lora_(?P<ab>[AB]))\.[0-9]+$"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=float, default=32.0)
    ap.add_argument("--dropout", type=float, default=0.0)
    ap.add_argument("--base-model", default="PrimeIntellect/Qwen3-0.6B")
    args = ap.parse_args()

    reader = FileSystemReader(args.ckpt)
    md = reader.read_metadata()

    template = {}
    target_modules = set()
    n = 0
    for raw, meta in md.state_dict_metadata.items():
        m = METADATA_KEY_RE.match(raw)
        if m is None:
            continue
        stem = m.group(1)  # model.layers.0.self_attn.q_proj.lora_A
        chunk = meta.chunks[0]
        size = tuple(int(s) for s in chunk.sizes)
        target_modules.add(m.group("proj"))
        template[raw] = torch.empty(size, dtype=torch.float32)
        n += 1

    raw = list(template)  # keep raw keys for dcp load
    dcp_load(state_dict=template, storage_reader=reader)

    hf = {stem + ".weight": template[raw].contiguous()
          for raw in raw
          if (stem := METADATA_KEY_RE.match(raw).group(1))}

    args.out.mkdir(parents=True, exist_ok=True)
    save_file(hf, args.out / "adapter_model.safetensors", metadata={"format": "pt"})

    with open(args.out / "adapter_config.json", "w") as f:
        json.dump(
            {
                "peft_type": "LORA",
                "task_type": "CAUSAL_LM",
                "base_model_name_or_path": args.base_model,
                "r": args.rank,
                "lora_alpha": args.alpha,
                "lora_dropout": args.dropout,
                "bias": "none",
                "target_modules": sorted(target_modules),
                "modules_to_save": None,
            },
            f,
            indent=2,
        )

    print(f"[export] wrote {n} LoRA tensors to {args.out}")


if __name__ == "__main__":
    main()