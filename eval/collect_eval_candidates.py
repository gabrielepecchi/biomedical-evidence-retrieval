"""
Collect retrieval candidates for manual relevance annotation.

Reads eval/queries.json, calls /search for each query, and writes
eval/candidates_alpha_0_5.json with the top-10 results per query.
"""

import json
import sys
from pathlib import Path

import requests

BASE_URL = "http://localhost:8000"
QUERIES_FILE = Path("eval/queries.json")
OUTPUT_FILE = Path("eval/candidates_alpha_0_5.json")
ALPHA = 0.5
TOP_N = 10

CANDIDATE_FIELDS = ("rank", "nct_id", "title", "overall_status", "phase", "study_type", "hybrid_score", "url")


def search(query: str) -> list[dict]:
    response = requests.get(
        f"{BASE_URL}/search",
        params={"q": query, "top_n": TOP_N, "alpha": ALPHA},
        timeout=60,
    )
    response.raise_for_status()
    return response.json().get("results", [])


def main() -> None:
    try:
        requests.get(f"{BASE_URL}/health", timeout=30).raise_for_status()
    except requests.exceptions.Timeout:
        print("Error: health check timed out after 30 seconds. Make sure the API is running.")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"Error: could not connect to the API at {BASE_URL}. Make sure it is running.")
        sys.exit(1)

    queries = json.loads(QUERIES_FILE.read_text(encoding="utf-8"))
    output = []

    for item in queries:
        query_id = item["query_id"]
        query = item["query"]
        print(f"Fetching {query_id}: {query[:60]}...")

        try:
            results = search(query)
        except requests.exceptions.Timeout:
            print(f"  Timeout: /search did not respond within 60 seconds for {query_id}. Skipping.")
            results = []
        except requests.exceptions.RequestException as exc:
            print(f"  Error: {exc}")
            results = []

        candidates = [{field: r.get(field) for field in CANDIDATE_FIELDS} for r in results]
        output.append({
            "query_id": query_id,
            "category": item.get("category", ""),
            "query": query,
            "candidates": candidates,
        })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved {len(output)} queries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
