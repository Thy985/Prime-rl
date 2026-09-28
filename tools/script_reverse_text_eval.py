"""Direct reverse-text eval against running local vLLM endpoint (8100)."""
import argparse, json, time
from difflib import SequenceMatcher
import re
import httpx

SYSTEM = "Reverse the text character-by-character. Put your answer in <reversed_text> tags."
_TAG = re.compile(r"<reversed_text>(.*?)</reversed_text>", re.DOTALL)
BACKEND = "http://localhost:8100/v1"
MODEL = "PrimeIntellect/Qwen3-0.6B"


def load_prompts(data_parquet, n):
    from datasets import load_dataset
    ds = load_dataset("parquet", data_files={"train": data_parquet}, split="train")
    ds = ds.select(range(min(n, len(ds))))
    return [{"prompt": r["prompt"], "answer": r["prompt"].rstrip()[::-1]} for r in ds]


SY=SYSTEM
TG=_TAG

def reward_for(completion, answer):
    m = TG.search(completion or "")
    resp = m.group(1).strip() if m else ""
    return SequenceMatcher(None, resp, answer).ratio()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data",
                   default="/home/lenovo/projects/prime-rl/outputs/reverse_text_local/data/train-00000-of-00001.parquet")
    p.add_argument("--num", type=int, default=32)
    p.add_argument("--max-tokens", type=int, default=512)
    p.add_argument("--temp", type=float, default=0.7)
    p.add_argument("--out", required=True)
    p.add_argument("--system", default=None, help="override system prompt")
    p.add_argument("--tag", default="reversed_text", help="tag to parse")
    a = p.parse_args()

    global SY, TG
    if a.system:
        SY = a.system
    if a.tag:
        # non-greedy, DOTALL
        TG = re.compile(r"<"+re.escape(a.tag)+r"(.*?)</"+re.escape(a.tag)+r">", re.DOTALL)
    items = load_prompts(a.data, a.num)
    client = httpx.Client(base_url=BACKEND, timeout=240, trust_env=False)
    results = []
    for i, it in enumerate(items):
        body = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SY},
                {"role": "user", "content": it["prompt"]},
            ],
            "max_tokens": a.max_tokens,
            "temperature": a.temp,
        }
        t0 = time.time()
        r = client.post("/chat/completions", json=body)
        if r.status_code != 200:
            res = {"idx": i, "prompt": it["prompt"], "completion": "",
                   "error": f"HTTP {r.status_code}: {r.text[:200]}", "reward": 0.0}
        else:
            comp = r.json()["choices"][0]["message"]["content"]
            res = {"idx": i, "prompt": it["prompt"], "answer": it["answer"],
                   "completion": comp, "reward": reward_for(comp, it["answer"])}
        res["_sec"] = round(time.time() - t0, 2)
        results.append(res)
        print(f"[{i+1}/{a.num}] reward={res.get('reward', 0):.3f} sec={res['_sec']}", flush=True)

    rews = [x.get("reward", 0.0) for x in results]
    n = len(rews)
    exact = sum(1 for r in rews if r >= 1.0)
    summary = {
        "n": n,
        "reward_mean": sum(rews) / n,
        "reward_median": sorted(rews)[n // 2],
        "pass_exact": exact / n,
        "pass_exact_count": exact,
        "min": min(rews),
        "max": max(rews),
    }
    with open(a.out + "_traces.json", "w") as f:
        json.dump(results, f, indent=2)
    with open(a.out + "_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\nSUMMARY:\n" + json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()