"""
Usage: python -m eval.evaluate --alpha 0.5
"""

import argparse
import json
import math
import sys
import urllib.request
import urllib.parse

QUERIES_FILE = "eval/queries.json"
BASE_URL = "http://localhost:8000"


def search(query: str, alpha: float, top_n: int = 10) -> list[str]:
    params = urllib.parse.urlencode({"q": query, "alpha": alpha, "top_n": top_n})
    url = f"{BASE_URL}/search?{params}"
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read())
    if isinstance(data, dict):
        data = data.get("results", [])
    return [r["nct_id"] if isinstance(r, dict) else r for r in data]


def precision_at_k(results: list[str], judgments: dict, k: int = 5) -> float:
    hits = sum(1 for nct in results[:k] if judgments.get(nct, 0) >= 1)
    return hits / k


def hit_at_k(results: list[str], judgments: dict, k: int = 5) -> float:
    return 1.0 if any(judgments.get(nct, 0) >= 1 for nct in results[:k]) else 0.0


def recall_at_k(results: list[str], judgments: dict, k: int = 10) -> float:
    relevant = sum(1 for v in judgments.values() if v >= 1)
    if relevant == 0:
        return 0.0
    found = sum(1 for nct in results[:k] if judgments.get(nct, 0) >= 1)
    return found / relevant


def mrr(results: list[str], judgments: dict) -> float:
    for i, nct in enumerate(results, 1):
        if judgments.get(nct, 0) >= 1:
            return 1.0 / i
    return 0.0


def ndcg_at_k(results: list[str], judgments: dict, k: int = 10) -> float:
    ideal = sorted(judgments.values(), reverse=True)[:k]
    ideal_dcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(ideal))
    if ideal_dcg == 0:
        return 0.0
    actual_dcg = sum(
        judgments.get(nct, 0) / math.log2(i + 2)
        for i, nct in enumerate(results[:k])
    )
    return actual_dcg / ideal_dcg


def evaluate(alpha: float) -> None:
    with open(QUERIES_FILE) as f:
        queries = json.load(f)

    metrics = ["P@5", "Hit@5", "R@10", "MRR", "nDCG@10"]
    col_w = 10
    q_w = 40

    header = f"{'Query':<{q_w}}" + "".join(f"{m:>{col_w}}" for m in metrics)
    print(header)
    print("-" * len(header))

    totals = {m: 0.0 for m in metrics}
    count = 0

    for entry in queries:
        raw = entry.get("judgments", [])
        if not raw:
            continue

        judgments = {j["nct_id"]: j["relevance"] for j in raw}
        query = entry["query"]

        try:
            results = search(query, alpha)
        except Exception as e:
            print(f"WARN: search failed for '{query}': {e}", file=sys.stderr)
            continue

        row = {
            "P@5":     precision_at_k(results, judgments),
            "Hit@5":   hit_at_k(results, judgments),
            "R@10":    recall_at_k(results, judgments),
            "MRR":     mrr(results, judgments),
            "nDCG@10": ndcg_at_k(results, judgments),
        }

        label = query[:q_w]
        print(f"{label:<{q_w}}" + "".join(f"{row[m]:>{col_w}.4f}" for m in metrics))

        for m in metrics:
            totals[m] += row[m]
        count += 1

    if count == 0:
        print("No queries evaluated.")
        return

    print("-" * len(header))
    avg_label = f"AVG (n={count})"
    print(f"{avg_label:<{q_w}}" + "".join(f"{totals[m]/count:>{col_w}.4f}" for m in metrics))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--alpha", type=float, default=0.5)
    args = parser.parse_args()
    evaluate(args.alpha)
