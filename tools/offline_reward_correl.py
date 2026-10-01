"""Offline verifier-reward correlation: which reward ranks exact success?

No training. Builds a trajectory corpus from a fixed SFT checkpoint, then scores
every candidate verifier on the SAME trajectory and measures how well each one
orders exact task success (the label):

  lcs      SequenceMatcher(body, target).ratio()
  edit     1 - edit_distance / max(len(body), len(target))
  pos      correct-position chars / len(target)
  lencons  1 - abs(len(body)-len(target)) / len(target)
  exact    body == target

Reported as bucketed exact-rate per reward bin, a rank correlation with the
exact label, and a within-failure ordering against the true minimum edit
distance -- i.e. how good a sorting signal each reward gives GRPO.

Prompt formatting, generation, extraction, adapter loading and all verifier
definitions come from tools/eval_contract.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import torch

from eval_contract import (
    edit_distance,
    edit_similarity,
    generate,
    lcs,
    length_consistency,
    load_model,
    parse_body,
    pos,
    target_for,
)

HELD_OUT = ["goodbye", "blocks", "tiny", "qwen", "sample", "then", "first", "bright"]


def scores(body, target):
    return {
        "lcs": lcs(body, target),
        "edit": edit_similarity(body, target),
        "pos": pos(body, target),
        "lencons": length_consistency(body, target),
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
    ap.add_argument("--limit", type=int, default=0, help="cap the number of prompts (0 = all)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="outputs/reward_corpus.json")
    ap.add_argument("--from-corpus", default=None)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    if args.from_corpus:
        rows = json.loads(Path(args.from_corpus).read_text())
        print("reused corpus:", args.from_corpus, "n =", len(rows))
    else:
        device = torch.device("cuda")
        model, tokenizer, loaded = load_model(device, args.adapter)
        print("adapter tensors loaded:", loaded)

        train_prompts = [m[1]["content"] for m in pd.read_parquet(args.train_data)["prompt"]]
        prompts = train_prompts + HELD_OUT
        if args.limit:
            prompts = prompts[: args.limit]
        print("prompts:", len(prompts))

        rows = []
        for prompt in prompts:
            target = target_for(prompt)
            split = "train" if prompt in train_prompts else "held"
            for temperature, count in ((0.0, args.greedy), (0.7, args.stoch)):
                for _ in range(count):
                    body = parse_body(generate(model, tokenizer, prompt, device, temperature=temperature))
                    rows.append({"prompt": prompt, "body": body, "target": target, "split": split})
        Path(args.out).write_text(json.dumps(rows, indent=1))
        print("corpus n =", len(rows), " exact =", sum(row["body"] == row["target"] for row in rows))

    label, per = [], defaultdict(list)
    for row in rows:
        metric = scores(row["body"], row["target"])
        label.append(metric["exact"])
        for key in ("lcs", "edit", "pos", "lencons"):
            per[key].append(metric[key])

    edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.001]
    print("\nreward bin -> exact-rate   (n per bin in parens)")
    for key in ("lcs", "edit", "pos", "lencons"):
        cells = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            idx = [j for j, value in enumerate(per[key]) if lo <= value < hi]
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

    bad = [j for j, row in enumerate(rows) if row["body"] != row["target"]]
    truth = [float(edit_distance(rows[j]["body"], rows[j]["target"])) for j in bad]

    def by_len_target(body, target):
        return 1.0 - edit_distance(body, target) / (len(target) or 1)

    def with_exact_bonus(body, target):
        return 1.15 if body == target else SequenceMatcher(None, body, target).ratio()

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

    print("\nwithin-failure ordering vs true edit distance (n=%d failures)" % len(bad))
    print("%-16s %8s %10s %14s" % ("candidate", "tau_shape", "top_exact", "groups_spread"))
    for name, fn in candidates.items():
        values = [max(0.0, min(1.0, fn(row["body"], row["target"]))) for row in rows]
        tau = kendall([1.0 - values[j] for j in bad], truth)
        top = [j for j in range(len(rows)) if values[j] >= 0.8]
        top_rate = sum(label[j] for j in top) / len(top) if top else 0.0
        spread = sum(
            1
            for idx in groups.values()
            if max(values[j] for j in idx) - min(values[j] for j in idx) > 0.01
        )
        print("%-16s %+8.3f %6.2f(%2d) %6d/%d" % (name, tau, top_rate, len(top), spread, len(groups)))


if __name__ == "__main__":
    main()