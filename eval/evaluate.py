"""Evaluation script for the Biomedical Evidence Retrieval and Trial Matching Platform.

Reads queries from queries.json, calls the local /search API for each,
and reports Precision@5 and Hit@5 per query plus overall averages.
"""

import argparse
import json
import sys

import requests

BASE_URL = "http://localhost:8000"
TOP_K = 5
QUERIES_FILE = "eval/queries.json"


def load_queries(path: str) -> list[dict]:
    """Load the query list from a JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def search(query: str, alpha: float, top_n: int) -> list[str]:
    """Call /search and return the top returned nct_id values."""
    response = requests.get(
        f"{BASE_URL}/search",
        params={"q": query, "top_n": top_n, "alpha": alpha},
        timeout=15,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    return [r["nct_id"] for r in results]


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Compute Precision@K: fraction of top-K results that are relevant."""
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for nct_id in top_k if nct_id in relevant)
    return hits / k


def hit_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Compute Hit@K: 1.0 if any relevant result appears in top-K, else 0.0."""
    top_k = retrieved[:k]
    return 1.0 if any(nct_id in relevant for nct_id in top_k) else 0.0


def main() -> None:
    """Run evaluation for all queries and print per-query and aggregate metrics."""
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

    print(f"\nEvaluating with alpha={args.alpha}, top_n={TOP_K}\n")
    print(f"{'Query ID':<10} {'Precision@5':>12} {'Hit@5':>8}  Query")
    print("-" * 80)

    precision_scores: list[float] = []
    hit_scores: list[float] = []

    for item in queries:
        query_id = item["query_id"]
        query = item["query"]
        relevant = item["relevant_nct_ids"]

        try:
            retrieved = search(query, alpha=args.alpha, top_n=TOP_K)
        except requests.exceptions.RequestException as exc:
            print(f"{query_id:<10} Error calling /search: {exc}")
            continue

        p5 = precision_at_k(retrieved, relevant, TOP_K)
        h5 = hit_at_k(retrieved, relevant, TOP_K)

        precision_scores.append(p5)
        hit_scores.append(h5)

        short_query = query[:55] + "..." if len(query) > 55 else query
        print(f"{query_id:<10} {p5:>12.3f} {h5:>8.1f}  {short_query}")

    if precision_scores:
        avg_p5 = sum(precision_scores) / len(precision_scores)
        avg_h5 = sum(hit_scores) / len(hit_scores)
        print("-" * 80)
        print(f"{'AVERAGE':<10} {avg_p5:>12.3f} {avg_h5:>8.3f}")
    else:
        print("\nNo results to average.")


if __name__ == "__main__":
    main()
