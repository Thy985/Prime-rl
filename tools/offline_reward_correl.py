"""Offline verifier-reward correlation: which reward ranks exact success?

No training. Loads the SFT LoRA adapter, samples a trajectory corpus, then scores
every candidate verifier on the SAME trajectory and measures how well each one
orders exact task success (the label):

  lcs      SequenceMatcher(body, target).ratio()
  edit     1 - edit_distance / max(len(body), len(target))
  pos      correct-position chars / len(target)
  lencons  1 - abs(len(body)-len(target)) / len(target)
  exact    body == target

Reported as bucketed exact-rate per reward bin plus a rank correlation with the
exact label -- i.e. how good a sorting signal each reward gives GRPO.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
import torch
from safetensors.torch import load_file
from transformers import AutoModelForCausalLM, AutoTokenizer

from prime_rl.configs.trainer import LoRAConfig
from prime_rl.trainer.lora import apply_lora_to_model, get_lora_state
from prime_rl.trainer.models.layers.lora import set_lora_num_tokens

BASE = "PrimeIntellect/Qwen3-0.6B"
SYSTEM = "Reverse the text character-by-character. Put your answer in <reversed_text> tags."
TAG = re.compile(r"<reversed_text>(.*?)</reversed_text>", re.DOTALL)
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
HELD_OUT = ["goodbye", "blocks", "tiny", "qwen", "sample", "then", "first", "bright"]


def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        row = [i]
        for j, cb in enumerate(b, 1):
            row.append(min(prev[j] + 1, row[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = row
    return prev[-1]


def set_len(model, n, dev):
    set_lora_num_tokens(torch.tensor([n], dtype=torch.int32, device=dev))


def load_adapter(model, path):
    """Copy exported PEFT adapter weights into the project's LoRA modules."""
    sd = load_file(Path(path) / "adapter_model.safetensors")
    tgt = dict(model.named_parameters())
    unmatched = []
    for key, val in sd.items():
        name = key.removeprefix("base_model.model.").removesuffix(".weight") + ".0"
        if name in tgt:
            tgt[name].data.copy_(val.to(tgt[name].dtype))
        else:
            unmatched.append(name)
    if unmatched:
        raise KeyError(f"{len(unmatched)} adapter keys had no target, e.g. {unmatched[:3]}")
    return len(sd)


def sample(model, tok, prompt, dev, max_new=40, temp=0.7):
    """Return only the generated continuation (prompt echo excluded)."""
    text = tok.apply_chat_template(
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        tokenize=False,
        add_generation_prompt=True,
    )
    ids = tok(text, return_tensors="pt").input_ids.to(dev)
    start = ids.shape[1]
    for _ in range(max_new):
        set_len(model, ids.shape[1], dev)
        with torch.no_grad():
            logits = model(ids).logits[0, -1].float()
        if temp <= 0:
            nxt = logits.argmax(-1).item()
        else:
            nxt = torch.multinomial(torch.softmax(logits / temp, dim=-1), 1).item()
        if nxt == tok.eos_token_id:
            break
        ids = torch.cat([ids, torch.tensor([[nxt]], device=dev)], dim=1)
    return tok.decode(ids[0, start:], skip_special_tokens=True)


def scores(body, target):
    length = len(target) or 1
    dist = edit_distance(body, target)
    pos = sum(1 for i in range(len(target)) if i < len(body) and body[i] == target[i]) / length
    return {
        "lcs": SequenceMatcher(None, body, target).ratio(),
        "edit": 1.0 - dist / max(len(body), len(target), 1),
        "pos": pos,
        "lencons": 1.0 - abs(len(body) - len(target)) / length,
        "exact": 1.0 if body == target else 0.0,
    }


def kendall(xs, ys):
    concord = discord = 0
    for i in range(len(xs)):
        for j in range(i + 1, len(xs)):
            dx, dy = xs[i] - xs[j], ys[i] - ys[j]
            if dx == 0 or dy == 0:
                continue
            concord, discord = (concord + 1, discord) if (dx > 0) == (dy > 0) else (concord, discord + 1)
    return (concord - discord) / (concord + discord) if concord + discord else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="outputs/short-ovf/adapter_step30")
    ap.add_argument("--train-data", default="outputs/short-ovf-train/data/train-00000-of-00001.parquet")
    ap.add_argument("--greedy", type=int, default=1)
    ap.add_argument("--stoch", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="outputs/reward_corpus.json")
    ap.add_argument("--from-corpus", default=None)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    if args.from_corpus:
        rows = json.loads(Path(args.from_corpus).read_text())
        print("reused corpus:", args.from_corpus, "n =", len(rows))
    else:
        dev = torch.device("cuda")
        tok = AutoTokenizer.from_pretrained(BASE)
        model = AutoModelForCausalLM.from_pretrained(BASE).to(torch.bfloat16).to(dev)
        model.eval()
        apply_lora_to_model(model, LoRAConfig(rank=16, alpha=32.0, dropout=0.0, target_modules=TARGETS))
        get_lora_state()
        print("adapter tensors loaded:", load_adapter(model, args.adapter))

        train_prompts = [m[1]["content"] for m in pd.read_parquet(args.train_data)["prompt"]]
        prompts = train_prompts + HELD_OUT
        print("prompts:", len(train_prompts), "train +", len(HELD_OUT), "held-out")

        rows = []
        for prompt in prompts:
            target = prompt.rstrip()[::-1]
            split = "train" if prompt in train_prompts else "held"
            for temp, count in ((0.0, args.greedy), (0.7, args.stoch)):
                for _ in range(count):
                    found = TAG.search(sample(model, tok, prompt, dev, temp=temp))
                    rows.append({
                        "prompt": prompt,
                        "body": found.group(1).strip() if found else "",
                        "target": target,
                        "split": split,
                    })
        Path(args.out).write_text(json.dumps(rows, indent=1))
        print("corpus n =", len(rows), " exact =", sum(r["body"] == r["target"] for r in rows))

    label, per = [], defaultdict(list)
    for row in rows:
        metric = scores(row["body"], row["target"])
        label.append(metric["exact"])
        for key in ("lcs", "edit", "pos", "lencons"):
            per[key].append(metric[key])

    edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.001]
    print("")
    print("reward bin -> exact-rate   (n per bin in parens)")
    for key in ("lcs", "edit", "pos", "lencons"):
        cells = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            idx = [j for j, v in enumerate(per[key]) if lo <= v < hi]
            rate = sum(label[j] for j in idx) / len(idx) if idx else 0.0
            cells.append("%.2f(%d)" % (rate, len(idx)))
        print("%-7s %s  tau=%.3f" % (key, "  ".join(cells), kendall(per[key], label)))

    for split in ("train", "held"):
        idx = [j for j, row in enumerate(rows) if row["split"] == split]
        print("\n%s subset: n=%d exact=%d" % (split, len(idx), sum(label[j] for j in idx)))
        for key in ("lcs", "edit", "pos"):
            cells = []
            for lo, hi in zip(edges[:-1], edges[1:]):
                sel = [j for j in idx if lo <= per[key][j] < hi]
                rate = sum(label[j] for j in sel) / len(sel) if sel else 0.0
                cells.append("%.2f(%d)" % (rate, len(sel)))
            print("%-7s %s" % (key, "  ".join(cells)))

    # Within-failure ordering: does the reward rank near-misses like the true
    # minimum edit distance to the target does? (edit is its own transform, so
    # it is reported as the reference, not a candidate.)
    bad = [j for j, row in enumerate(rows) if row["body"] != row["target"]]
    truth = [float(edit_distance(rows[j]["body"], rows[j]["target"])) for j in bad]

    def by_len_target(body, target):
        return 1.0 - edit_distance(body, target) / (len(target) or 1)

    def with_exact_bonus(body, target):
        base = SequenceMatcher(None, body, target).ratio()
        return min(1.0, base + 0.15) if body == target else base

    def lcs_lenpenalised(body, target):
        base = SequenceMatcher(None, body, target).ratio()
        return max(0.0, base - 0.5 * abs(len(body) - len(target)) / (len(target) or 1))

    candidates = {
        "lcs (=v1)": lambda b, t: scores(b, t)["lcs"],
        "edit_maxnorm": lambda b, t: scores(b, t)["edit"],
        "edit_targetnorm": by_len_target,
        "pos": lambda b, t: scores(b, t)["pos"],
        "lencons": lambda b, t: scores(b, t)["lencons"],
        "lcs+exact_bonus": with_exact_bonus,
        "lcs_lenpen": lcs_lenpenalised,
    }

    groups = defaultdict(list)
    for j, row in enumerate(rows):
        groups[row["prompt"]].append(j)

    header = "%-16s %8s %10s %14s" % ("candidate", "tau_shape", "top_exact", "groups_spread")
    print("\nwithin-failure ordering vs true edit distance (n=%d failures)" % len(bad))
    print(header)
    for name, fn in candidates.items():
        values = [max(0.0, min(1.0, fn(r["body"], r["target"]))) for r in rows]
        tau = kendall([1.0 - values[j] for j in bad], truth)
        top = [j for j in range(len(rows)) if values[j] >= 0.8]
        top_rate = sum(label[j] for j in top) / len(top) if top else 0.0
        spread = sum(
            1 for idx in groups.values()
            if max(values[j] for j in idx) - min(values[j] for j in idx) > 0.01
        )
        print("%-16s %+8.3f %6.2f(%2d) %6d/%d" % (name, tau, top_rate, len(top), spread, len(groups)))


if __name__ == "__main__":
    main()