"""Single evaluation/training protocol contract for the reverse-text task.

Training, inference and offline evaluation must agree on: tokenizer, chat
template, system prompt, prompt serialization, completion extraction,
generation config and verifier version. Every Base/SFT/RL experiment goes
through this module so a comparison cannot pick up a protocol shift.

Verifier definitions (target = prompt.rstrip()[::-1]):
  lcs      SequenceMatcher(body, target).ratio()          -- v1, graded
  pos      correct-position chars / len(target)           -- top-precise, brittle
  exact    body == target                                 -- task success
  lcs_bonus  lcs, but exactly 1.0 + alpha on exact success -- v3
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path

import torch
from safetensors.torch import load_file

from prime_rl.configs.trainer import LoRAConfig
from prime_rl.trainer.lora import apply_lora_to_model, get_lora_state
from prime_rl.trainer.models.layers.lora import set_lora_num_tokens

MODEL = "PrimeIntellect/Qwen3-0.6B"
SYSTEM = "Reverse the text character-by-character. Put your answer in <reversed_text> tags."
TAG = re.compile(r"<reversed_text>(.*?)</reversed_text>", re.DOTALL)
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
MAX_NEW = 40
ALPHA = 0.15


def target_for(prompt):
    return prompt.rstrip()[::-1]


def format_prompt(tokenizer, prompt):
    return tokenizer.apply_chat_template(
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        tokenize=False,
        add_generation_prompt=True,
    )


def parse_body(continuation):
    """Extract the answer from a generation continuation (never from a prompt)."""
    found = TAG.search(continuation)
    return found.group(1).strip() if found else ""


def set_lora_tokens(model, count, device):
    set_lora_num_tokens(torch.tensor([count], dtype=torch.int32, device=device))


def generate_ids(model, tokenizer, prompt, device, max_new=MAX_NEW, temperature=0.7):
    """Sample a continuation; return (full ids, index where the continuation starts)."""
    ids = tokenizer(format_prompt(tokenizer, prompt), return_tensors="pt").input_ids.to(device)
    start = ids.shape[1]
    for _ in range(max_new):
        set_lora_tokens(model, ids.shape[1], device)
        with torch.no_grad():
            logits = model(ids).logits[0, -1].float()
        if temperature <= 0:
            nxt = logits.argmax(-1).item()
        else:
            nxt = torch.multinomial(torch.softmax(logits / temperature, dim=-1), 1).item()
        if nxt == tokenizer.eos_token_id:
            break
        ids = torch.cat([ids, torch.tensor([[nxt]], device=device)], dim=1)
    return ids, start


def generate(model, tokenizer, prompt, device, max_new=MAX_NEW, temperature=0.7):
    """Return the generated continuation only, chat-templated (protocol-fixed)."""
    ids, start = generate_ids(model, tokenizer, prompt, device, max_new, temperature)
    return tokenizer.decode(ids[0, start:], skip_special_tokens=True)


def completion_logprob(model, ids, start, device):
    """Sum log p(continuation | prompt) over the tokens actually sampled, with grad."""
    set_lora_tokens(model, ids.shape[1], device)
    logits = model(ids).logits[:, :-1, :].float()
    logp = torch.log_softmax(logits, dim=-1)
    return logp[0, start - 1:, :].gather(1, ids[0, start:].unsqueeze(1)).squeeze(1).sum()


def edit_distance(a, b):
    """Levenshtein distance, the ground-truth cost of reaching the target."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        row = [i]
        for j, cb in enumerate(b, 1):
            row.append(min(prev[j] + 1, row[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = row
    return prev[-1]


def lcs(body, target):
    return SequenceMatcher(None, body, target).ratio()


def edit_similarity(body, target):
    return 1.0 - edit_distance(body, target) / max(len(body), len(target), 1)


def length_consistency(body, target):
    return 1.0 - abs(len(body) - len(target)) / (len(target) or 1)


def pos(body, target):
    length = len(target) or 1
    hits = sum(1 for i in range(len(target)) if i < len(body) and body[i] == target[i])
    return hits / length


def lcs_bonus(body, target, alpha=ALPHA):
    return 1.0 + alpha if body == target else lcs(body, target)


REWARDS = {
    "lcs": lcs,
    "pos": pos,
    "lcs_bonus": lcs_bonus,
}


def build_reward(name):
    if name not in REWARDS:
        raise ValueError(f"unknown reward {name!r}, expected one of {sorted(REWARDS)}")
    return REWARDS[name]


def load_lora_adapter(model, adapter_dir):
    """Copy an exported PEFT adapter into the project's LoRA modules."""
    weights = load_file(Path(adapter_dir) / "adapter_model.safetensors")
    named = dict(model.named_parameters())
    unmatched = []
    for key, value in weights.items():
        name = key.removeprefix("base_model.model.").removesuffix(".weight") + ".0"
        if name in named:
            named[name].data.copy_(value.to(named[name].dtype))
        else:
            unmatched.append(name)
    if unmatched:
        raise KeyError(f"{len(unmatched)} adapter keys had no target, e.g. {unmatched[:3]}")
    return len(weights)


def load_model(device, adapter_dir=None, rank=16, alpha=32.0):
    """Base model + project LoRA, optionally initialised from an SFT adapter."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model = AutoModelForCausalLM.from_pretrained(MODEL).to(torch.bfloat16).to(device)
    model.eval()
    apply_lora_to_model(
        model,
        LoRAConfig(rank=rank, alpha=alpha, dropout=0.0, target_modules=TARGET_MODULES),
    )
    get_lora_state()
    loaded = load_lora_adapter(model, adapter_dir) if adapter_dir else 0
    return model, tokenizer, loaded