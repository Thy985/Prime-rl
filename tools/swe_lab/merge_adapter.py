"""Merge a LoRA adapter into its base model, writing a plain HF checkpoint.

The export step writes a PEFT-shaped adapter (adapter_model.safetensors +
adapter_config.json) under outputs/swe_runs/pi-real-D-lora-adapter. vLLM can
serve a merged checkpoint directly with the same inference/eval config used
for the untrained baseline, so no --enable-lora path is needed. This runs on
CPU only (0.6B bf16 ~1.2 GB RAM): for each adapted linear, W += (alpha/r) * B@A.

  uv run python tools/swe_lab/merge_adapter.py \
    outputs/swe_runs/pi-real-D-lora-adapter outputs/swe_runs/pi-real-D-hf
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from safetensors.torch import load_file
from transformers import AutoModelForCausalLM, AutoTokenizer

_ADAPTER_WEIGHTS = "adapter_model.safetensors"
_ADAPTER_CONFIG = "adapter_config.json"


def merge(adapter_dir: Path, out_dir: Path, base: str) -> int:
    cfg = json.loads((adapter_dir / _ADAPTER_CONFIG).read_text())
    scaling = cfg["lora_alpha"] / cfg["r"]
    adapter = load_file(adapter_dir / _ADAPTER_WEIGHTS)

    model = AutoModelForCausalLM.from_pretrained(base, torch_dtype=torch.bfloat16)
    sd = model.state_dict()

    a_keys = [k for k in adapter if k.endswith(".lora_A.weight")]
    if not a_keys:
        raise SystemExit(f"no lora_A weights in {adapter_dir / _ADAPTER_WEIGHTS}")

    for ak in a_keys:
        bk = ak.replace(".lora_A.weight", ".lora_B.weight")
        wk = ak.replace(".lora_A.weight", ".weight")
        if wk not in sd:
            raise SystemExit(f"adapter key {wk!r} has no matching base weight")
        # lora_A: (r, in), lora_B: (out, r) -> B @ A: (out, in)
        delta = (adapter[bk].float() @ adapter[ak].float()) * scaling
        sd[wk] = sd[wk].to(torch.bfloat16) + delta.to(torch.bfloat16)

    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir)
    AutoTokenizer.from_pretrained(base).save_pretrained(out_dir)
    return len(a_keys)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("adapter_dir", type=Path, help="dir with adapter_model.safetensors + adapter_config.json")
    ap.add_argument("out_dir", type=Path, help="output HF checkpoint dir")
    ap.add_argument("--base", default="PrimeIntellect/Qwen3-0.6B", help="base model id")
    args = ap.parse_args()

    n = merge(args.adapter_dir, args.out_dir, args.base)
    print(f"merged {n} adapters into {args.out_dir} (base={args.base})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())