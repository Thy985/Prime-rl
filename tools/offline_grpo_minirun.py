"""Offline multi-step GRPO mini-run with a held-out eval (single GPU, no vLLM).

One run answers both experiments:
  Experiment A (RL held-out): does the GRPO reward rise leak beyond the few
    training prompts? We eval on `--held-out` prompts the LoRA never saw.
  Experiment B (reward vs exact): each step we report mean LCS (the verifier
    proxy reward) AND exact% (task success: <reversed_text> body ==
    prompt.rstrip()[::-1]) on the held-out set, to see if proxy/reward climbs
    also raise true task success.

Loop (offline, one GPU):
  step k:
    for each train prompt, sample group_size rollouts (local sampler, temp)
    verifier_reward -> group relative advantage adv=(r-mean)/(std+eps)
    objective loss = -mean(adv.detach()*log p(completion))
    one AdamW step on the project LoRA params
  then greedy-eval the held-out prompts with the SAME updated model.

usage: uv run python tools/offline_grpo_minirun.py \
         --prompts hello world 'reverse this' 'fast cars' 'The quick' gradient \
         --held-out goodbye training blocks tiny qwen --group-size 4 --steps 3
"""

from __future__ import annotations

import argparse
import re
from difflib import SequenceMatcher

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from prime_rl.configs.trainer import LoRAConfig
from prime_rl.trainer.lora import apply_lora_to_model, get_lora_state
from prime_rl.trainer.models.layers.lora import set_lora_num_tokens

BASE = "PrimeIntellect/Qwen3-0.6B"
SYSTEM = ("Reverse the text character-by-character. "
          "Put your answer in <reversed_text> tags.")
TAG = re.compile(r"<reversed_text>(.*?)</reversed_text>", re.DOTALL)
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def set_len(model, n, dev):
    set_lora_num_tokens(torch.tensor([n], dtype=torch.int32, device=dev))


def verifier_reward(prompt, completion):
    m = TAG.search(completion)
    body = m.group(1).strip() if m else ""
    return SequenceMatcher(None, body, prompt.rstrip()[::-1]).ratio()


def exact_match(prompt, completion):
    m = TAG.search(completion)
    return bool(m) and m.group(1).strip() == prompt.rstrip()[::-1]


def sample(model, tokenizer, prompt, dev, max_new=24, temp=0.7):
    ids = tokenizer(prompt, return_tensors="pt").input_ids.to(dev)
    for _ in range(max_new):
        set_len(model, ids.shape[1], dev)
        with torch.no_grad():
            logits = model(ids).logits[0, -1].float() / temp
        nxt = torch.multinomial(torch.softmax(logits, dim=-1), 1).item()
        ids = torch.cat([ids, torch.tensor([[nxt]], device=dev)], dim=1)
    return tokenizer.decode(ids[0], skip_special_tokens=True)


def greedy_completion(model, tokenizer, prompt, dev, max_new=24):
    ids = tokenizer(prompt, return_tensors="pt").input_ids.to(dev)
    for _ in range(max_new):
        set_len(model, ids.shape[1], dev)
        with torch.no_grad():
            nxt = model(ids).logits[0, -1].argmax(-1).item()
        ids = torch.cat([ids, torch.tensor([[nxt]], device=dev)], dim=1)
    return tokenizer.decode(ids[0], skip_special_tokens=True)


def completion_logprob(model, tokenizer, text, dev):
    ids = tokenizer(text, return_tensors="pt").input_ids.to(dev)
    set_len(model, len(ids[0]), dev)
    logits = model(ids).logits[:, :-1, :].float()
    lp = torch.log_softmax(logits, dim=-1)
    return lp[0].gather(1, ids[0, 1:].unsqueeze(1)).squeeze(1).sum()


def build(lora_cfg, dev):
    tok = AutoTokenizer.from_pretrained(BASE)
    if tok.pad_token_id is None:
        tok.pad_token_id = tok.eos_token_id
    model = AutoModelForCausalLM.from_pretrained(BASE).to(torch.bfloat16).to(dev)
    model.eval()
    apply_lora_to_model(model, lora_cfg)
    get_lora_state()
    return model, tok


def greedy_eval(model, tok, prompts, dev):
    lcs = [verifier_reward(p, greedy_completion(model, tok, SYSTEM + "\n\n" + p, dev)) for p in prompts]
    exact = sum(1 for p, r in zip(prompts, lcs) if exact_match(p, greedy_completion(model, tok, SYSTEM + "\n\n" + p, dev)))
    return lcs, exact


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", nargs="*", default=["hello", "world", "reverse intro"])
    ap.add_argument("--held-out", nargs="*", default=["goodbye", "blocks", "tiny", "squash"])
    ap.add_argument("--group-size", type=int, default=4)
    ap.add_argument("--steps", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    dev = torch.device("cuda")
    lf = LoRAConfig(rank=16, alpha=32.0, dropout=0.0, target_modules=TARGETS)
    model, tok = build(lf, dev)
    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(trainable, lr=args.lr)

    for step in range(1, args.steps + 1):
        flat, advs, group_means = [], [], []
        for prompt in args.prompts:
            rolls = [sample(model, tok, SYSTEM + "\n\n" + prompt, dev) for _ in range(args.group_size)]
            rr = [verifier_reward(prompt, c) for c in rolls]
            mean = sum(rr) / len(rr)
            std = (sum((r - mean) ** 2 for r in rr) / len(rr)) ** 0.5 + 1e-4
            for c, r in zip(rolls, rr):
                flat.append((prompt, SYSTEM + "\n\n" + prompt + "\n" + c, (r - mean) / std))
            group_means.append(mean)

        logprobs = torch.stack([completion_logprob(model, tok, txt, dev) for _, txt, _ in flat])
        adv = torch.tensor([a for _, _, a in flat], dtype=torch.bfloat16, device=dev)
        loss = -torch.mean(adv.detach() * logprobs)
        opt.zero_grad()
        before = {id(p): p.detach().clone() for p in trainable}
        loss.backward()
        nz = sum(1 for p in trainable if p.grad is not None and p.grad.abs().sum().item() > 0)
        opt.step()
        changed = sum(1 for p in trainable if (p.detach() - before[id(p)]).abs().sum().item() > 0)

        # Held-out greedy eval for Experiments A & B.
        h_lcs, h_exact = greedy_eval(model, tok, args.held_out, dev)
        print(f"step={step}/{args.steps} train_reward={sum(group_means)/len(group_means):.3f} "
              f"loss={loss.item():.4f} grads={nz}/{len(trainable)} | "
              f"held({len(args.held_out)}) mean_lcs={sum(h_lcs)/len(h_lcs):.3f} exact={h_exact}/{len(args.held_out)}",
              flush=True)


if __name__ == "__main__":
    main()
