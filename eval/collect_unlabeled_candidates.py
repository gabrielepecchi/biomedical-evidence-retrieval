"""
Collect top-10 hybrid search candidates for queries with empty judgments.
Writes eval/unlabeled_candidates_alpha_0_5.json.

Usage:
    python -m collect_unlabeled_candidates
    (API must be running on http://localhost:8000)
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path

QUERIES_PATH = Path("eval/queries.json")
OUTPUT_PATH = Path("eval/unlabeled_candidates_alpha_0_5.json")
SEARCH_URL = "http://localhost:8000/search"
NCT_BASE_URL = "https://clinicaltrials.gov/study/"
ALPHA = 0.5
TOP_N = 10


def search(query: str) -> list[dict]:
    params = urllib.parse.urlencode({"q": query, "alpha": ALPHA, "top_n": TOP_N})
    url = f"{SEARCH_URL}?{params}"
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read())
        return data.get("results", [])


def main() -> None:
    queries = json.loads(QUERIES_PATH.read_text())
    unlabeled = [q for q in queries if not q.get("judgments")]

    if not unlabeled:
        print("No unlabeled queries found.")
        return

    results = []
    for q in unlabeled:
        print(f"Searching {q['query_id']}: {q['query']}")
        hits = search(q["query"])
        candidates = [
            {
                "rank": i + 1,
                "nct_id": h["nct_id"],
                "title": h.get("title", ""),
                "overall_status": h.get("overall_status", ""),
                "phase": h.get("phase", ""),
                "study_type": h.get("study_type", ""),
                "hybrid_score": h.get("hybrid_score"),
                "url": f"{NCT_BASE_URL}{h['nct_id']}",
            }
            for i, h in enumerate(hits)
        ]
        results.append({
            "query_id": q["query_id"],
            "category": q["category"],
            "query": q["query"],
            "candidates": candidates,
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {len(results)} queries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
