"""Offline multi-step GRPO on a fixed SFT checkpoint: one reward at a time.

Only the reward function varies; checkpoint, taskset, sampler, group size,
steps, lr, temperature and seed are held fixed, so a comparison across
--reward values is a reward ablation rather than a protocol change.

Train prompts come from the SFT task distribution and the held-out set is the
disjoint remainder, so held-out exact measures transfer rather than
memorisation. Prompt formatting, generation, extraction and verification all go
through tools/eval_contract.py.

usage: uv run python tools/offline_grpo_minirun.py --reward lcs_bonus \
         --adapter outputs/short-ovf/adapter_step30 --steps 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch

from eval_contract import (
    build_reward,
    completion_logprob,
    generate,
    generate_ids,
    lcs,
    load_model,
    parse_body,
    target_for,
)

TRAIN_PROMPTS = [
    "hello",
    "world",
    "reverse this",
    "fast cars",
    "abcdefghij",
    "The quick",
    "Qwen3 small",
    "data science",
    "my tiny text",
    "nice job now",
]
HELD_OUT_PROMPTS = [
    "few words here",
    "abc def ghi",
    "Test string",
    "machine",
    "short",
    "primer-rl",
    "lora",
    "gradient",
]


def held_out_scores(model, tokenizer, device):
    """Protocol-fixed held-out evaluation: always LCS plus task success."""
    total, exact, bodies = 0.0, 0, []
    for prompt in HELD_OUT_PROMPTS:
        target = target_for(prompt)
        body = parse_body(generate(model, tokenizer, prompt, device, temperature=0.0))
        total += lcs(body, target)
        exact += int(body == target)
        bodies.append({"prompt": prompt, "target": target, "body": body})
    return total / len(HELD_OUT_PROMPTS), exact, bodies


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reward", default="lcs", choices=["lcs", "pos", "lcs_bonus"])
    ap.add_argument("--adapter", default="outputs/short-ovf/adapter_step30")
    ap.add_argument("--group-size", type=int, default=4)
    ap.add_argument("--steps", type=int, default=5)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    device = torch.device("cuda")
    model, tokenizer, loaded = load_model(device, args.adapter)
    reward = build_reward(args.reward)
    trainable = [p for p in model.parameters() if p.requires_grad]
    optimiser = torch.optim.AdamW(trainable, lr=args.lr)

    history = []
    held_lcs, held_exact, held_bodies = held_out_scores(model, tokenizer, device)
    print(
        "reward=%-9s adapter=%s tensors=%d | step 0 held lcs=%.3f exact=%d/%d"
        % (args.reward, args.adapter, loaded, held_lcs, held_exact, len(HELD_OUT_PROMPTS)),
        flush=True,
    )
    history.append(
        {
            "step": 0,
            "train_reward": None,
            "loss": None,
            "held_lcs": held_lcs,
            "held_exact": held_exact,
            "held_bodies": held_bodies,
        }
    )

    for step in range(1, args.steps + 1):
        batch, advantages, group_means = [], [], []
        for prompt in TRAIN_PROMPTS:
            target = target_for(prompt)
            entries = []
            for _ in range(args.group_size):
                ids, start = generate_ids(model, tokenizer, prompt, device, temperature=args.temperature)
                body = parse_body(tokenizer.decode(ids[0, start:], skip_special_tokens=True))
                entries.append((ids, start, reward(body, target)))
            values = [entry[2] for entry in entries]
            mean = sum(values) / len(values)
            std = (sum((value - mean) ** 2 for value in values) / len(values)) ** 0.5 + 1e-4
            batch.extend(entries)
            advantages.extend((value - mean) / std for value in values)
            group_means.append(mean)

        # Per-token normalisation, matching the token-count scale the prime-rl RL
        # trainer uses (`rl_scale`), rather than an unweighted sum over tokens.
        logprobs = torch.stack(
            [
                completion_logprob(model, ids, start, device) / max(1, ids.shape[1] - start)
                for ids, start, _ in batch
            ]
        )
        advantage = torch.tensor(advantages, dtype=torch.bfloat16, device=device)
        loss = -torch.mean(advantage.detach() * logprobs)

        optimiser.zero_grad()
        before = {id(param): param.detach().clone() for param in trainable}
        loss.backward()
        grads = sum(1 for p in trainable if p.grad is not None and p.grad.abs().sum().item() > 0)
        optimiser.step()
        changed = sum(1 for p in trainable if (p.detach() - before[id(p)]).abs().sum().item() > 0)

        held_lcs, held_exact, held_bodies = held_out_scores(model, tokenizer, device)
        train_reward = sum(group_means) / len(group_means)
        print(
            "reward=%-9s step %d/%d train=%.3f loss=%+.4f grads=%d/%d delta=%d | held lcs=%.3f exact=%d/%d"
            % (
                args.reward,
                step,
                args.steps,
                train_reward,
                loss.item(),
                grads,
                len(trainable),
                changed,
                held_lcs,
                held_exact,
                len(HELD_OUT_PROMPTS),
            ),
            flush=True,
        )
        history.append(
            {
                "step": step,
                "train_reward": train_reward,
                "loss": loss.item(),
                "held_lcs": held_lcs,
                "held_exact": held_exact,
                "held_bodies": held_bodies,
            }
        )

    if args.out:
        Path(args.out).write_text(json.dumps({"reward": args.reward, "history": history}, indent=1))
        print("wrote", args.out, flush=True)


if __name__ == "__main__":
    main()