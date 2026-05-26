"""Evaluation script for the Biomedical Evidence Retrieval and Trial Matching Platform.

Reads queries from queries.json, calls the local /search API for each,
and reports Precision@5, Hit@5, Recall@10, and MRR per query plus averages.
Queries with empty relevant_nct_ids are printed as SKIPPED and excluded from averages.
"""

import argparse
import json
import sys

import requests

BASE_URL = "http://localhost:8000"
TOP_N = 10
QUERIES_FILE = "eval/queries.json"


def load_queries(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def search(query: str, alpha: float, top_n: int) -> list[str]:
    response = requests.get(
        f"{BASE_URL}/search",
        params={"q": query, "top_n": top_n, "alpha": alpha},
        timeout=15,
    )
    response.raise_for_status()
    return [r["nct_id"] for r in response.json().get("results", [])]


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    return sum(1 for nct_id in top_k if nct_id in relevant) / k


def hit_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    return 1.0 if any(nct_id in relevant for nct_id in retrieved[:k]) else 0.0


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    return sum(1 for nct_id in top_k if nct_id in relevant) / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    for i, nct_id in enumerate(retrieved, start=1):
        if nct_id in relevant:
            return 1.0 / i
    return 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality.")
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.5,
        help="BM25 weight for hybrid scoring (0.0 to 1.0, default 0.5)",
    )
    args = parser.parse_args()

    queries = load_queries(QUERIES_FILE)

    try:
        requests.get(f"{BASE_URL}/health", timeout=5).raise_for_status()
    except requests.exceptions.ConnectionError:
        print(f"Error: could not connect to the API at {BASE_URL}. Make sure it is running.")
        sys.exit(1)
    except requests.exceptions.HTTPError as exc:
        print(f"Error: API returned an unexpected response: {exc}")
        sys.exit(1)

    print(f"\nEvaluating with alpha={args.alpha}, top_n={TOP_N}\n")

    header = f"{'Query ID':<10} {'P@5':>6} {'Hit@5':>6} {'R@10':>6} {'MRR':>6}  Query"
    print(header)
    print("-" * 80)

    p5_scores: list[float] = []
    h5_scores: list[float] = []
    r10_scores: list[float] = []
    mrr_scores: list[float] = []

    for item in queries:
        query_id = item["query_id"]
        query = item["query"]
        relevant = item["relevant_nct_ids"]
        short_query = query[:48] + "..." if len(query) > 48 else query

        if not relevant:
            print(f"{query_id:<10} {'SKIPPED':>6} {'':>6} {'':>6} {'':>6}  {short_query}")
            continue

        try:
            retrieved = search(query, alpha=args.alpha, top_n=TOP_N)
        except requests.exceptions.RequestException as exc:
            print(f"{query_id:<10} Error calling /search: {exc}")
            continue

        p5  = precision_at_k(retrieved, relevant, 5)
        h5  = hit_at_k(retrieved, relevant, 5)
        r10 = recall_at_k(retrieved, relevant, 10)
        mrr = reciprocal_rank(retrieved, relevant)

        p5_scores.append(p5)
        h5_scores.append(h5)
        r10_scores.append(r10)
        mrr_scores.append(mrr)

        print(f"{query_id:<10} {p5:>6.3f} {h5:>6.1f} {r10:>6.3f} {mrr:>6.3f}  {short_query}")

    if p5_scores:
        avg_p5  = sum(p5_scores)  / len(p5_scores)
        avg_h5  = sum(h5_scores)  / len(h5_scores)
        avg_r10 = sum(r10_scores) / len(r10_scores)
        avg_mrr = sum(mrr_scores) / len(mrr_scores)
        n = len(p5_scores)
        print("-" * 80)
        print(f"{'AVERAGE':<10} {avg_p5:>6.3f} {avg_h5:>6.3f} {avg_r10:>6.3f} {avg_mrr:>6.3f}  (n={n})")
    else:
        print("\nNo scored queries to average.")


if __name__ == "__main__":
    main()
