"""Offline tiny GRPO trainer-smoke.

Closes the Python/LoRA update path on a single GPU without co-hosting a vLLM
server:

    sampler -> verifier_v1 (LCS, answer=prompt.rstrip()[::-1])
            -> group normalization (adv = (r-mean)/(std+eps))
            -> GRPO objective  loss = -mean(adv.detach() * log p(completion))
            -> LoRA backward -> AdamW step -> non-zero LoRA delta

Proof: the LoRA adapter parameters change (delta != 0) after one update.
"""

import re
import sys
from difflib import SequenceMatcher

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from prime_rl.configs.trainer import LoRAConfig
from prime_rl.trainer.lora import apply_lora_to_model, get_lora_state
from prime_rl.trainer.models.layers.lora import set_lora_num_tokens

BASE = "PrimeIntellect/Qwen3-0.6B"
SYSTEM = ("Reverse the text character-by-character."
          " Put your answer in <reversed_text> tags.")
TAG = re.compile(r"<reversed_text>(.*?)</reversed_text>", re.DOTALL)
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def set_len(model, n, dev):
    set_lora_num_tokens(torch.tensor([n], dtype=torch.int32, device=dev))


def verifier_reward(prompt, completion):
    m = TAG.search(completion)
    body = m.group(1).strip() if m else ""
    return SequenceMatcher(None, body, prompt.rstrip()[::-1]).ratio()


def sample_backoff(model, tokenizer, prompt, dev, max_new=24, temp=0.7):
    """Token-by-token sampling so lora_num_tokens stays correct each step."""
    ids = tokenizer(prompt, return_tensors="pt").input_ids.to(dev)
    for _ in range(max_new):
        set_len(model, ids.shape[1], dev)
        with torch.no_grad():
            logits = model(ids).logits[0, -1].float() / temp
        nxt = torch.multinomial(torch.softmax(logits, dim=-1), 1).item()
        ids = torch.cat([ids, torch.tensor([[nxt]], device=dev)], dim=1)
    return tokenizer.decode(ids[0], skip_special_tokens=True)


def completion_logprob(model, tokenizer, full_text, dev):
    ids = tokenizer(full_text, return_tensors="pt").input_ids.to(dev)
    set_len(model, len(ids[0]), dev)
    logits = model(ids).logits[:, :-1, :].float()
    lp = torch.log_softmax(logits, dim=-1)
    return lp[0].gather(1, ids[0, 1:].unsqueeze(1)).squeeze(1).sum()


def main():
    torch.manual_seed(0)
    dev = torch.device("cuda")

    tokenizer = AutoTokenizer.from_pretrained(BASE)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model = AutoModelForCausalLM.from_pretrained(BASE).to(torch.bfloat16).to(dev)
    model.eval()

    cfg = LoRAConfig(rank=16, alpha=32.0, dropout=0.0, target_modules=TARGETS)
    apply_lora_to_model(model, cfg)
    get_lora_state()

    prompts = ["hello", "world", "reverse this"]
    group_size = 4

    groups = []
    for prompt in prompts:
        rolls = []
        for _ in range(group_size):
            gen = sample_backoff(model, tokenizer, SYSTEM + "\n\n" + prompt, dev)
            rolls.append(gen)
        groups.append((prompt, rolls))

    rewards, advs, texts = [], [], []
    for prompt, rolls in groups:
        rr = [verifier_reward(prompt, c) for c in rolls]
        mean, std = sum(rr) / len(rr), (sum((x - sum(rr) / len(rr)) ** 2 for x in rr) / len(rr)) ** 0.5 + 1e-4
        for i, c in enumerate(rolls):
            rewards.append(rr[i])
            advs.append((rr[i] - mean) / std)
            texts.append(SYSTEM + "\n\n" + prompt + "\n" + c)

    print("VERIFIER per-group rewards:",
          {p: [round(verifier_reward(p, c), 3) for c in rolls] for p, rolls in groups})

    logprobs = torch.stack([completion_logprob(model, tokenizer, t, dev) for t in texts])
    adv = torch.tensor(advs, dtype=torch.bfloat16, device=dev)
    loss = -torch.mean(adv.detach() * logprobs)

    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(trainable, lr=1e-4)
    opt.zero_grad()
    before = {id(p): p.detach().clone() for p in trainable}
    loss.backward()
    nz = sum(1 for p in trainable if p.grad is not None and p.grad.abs().sum().item() > 0)
    opt.step()

    tot = 0.0
    changed = 0
    for p in trainable:
        d = (p.detach() - before[id(p)]).abs().sum().item()
        if d > 0:
            changed += 1
        tot += d * d

    print("lora token-len forward counts handled; groups:", len(groups))
    print("sample sizes :", [len(t) for t in texts])
    print("ADVANTAGE    :", [round(a, 3) for a in advs])
    print("VOLTAGE/LOSS :", loss.item())
    print("LoRA grads   :", nz, "/", len(trainable), " delta nonzero:", changed, " total_abs=%.5f" % (tot ** 0.5))
    ok = nz > 0 and changed > 0
    print("\nCLOSED on GPU offline: sampler -> verifier -> reward -> advantage -> LoRA delta." if ok
          else "\nLOOP FAILED.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
