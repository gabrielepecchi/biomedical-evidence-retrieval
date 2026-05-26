"""
Trial Matching Lite — retrieval-based only.

Reads eval/patient_cases.json, calls the local /search endpoint for each
case using its matching_query, and writes ranked results to
eval/patient_case_matches_alpha_0_5.json.

Compatibility labels are rank-based heuristics and do NOT indicate clinical
eligibility. No medical decision support is implied.
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

INPUT_PATH = Path("eval/patient_cases.json")
OUTPUT_PATH = Path("eval/patient_case_matches_alpha_0_5.json")
BASE_URL = "http://localhost:8000"
ALPHA = 0.5
TOP_N = 10


def search(query: str, alpha: float, top_n: int) -> list[dict]:
    """Call /search and return the results list."""
    params = urllib.parse.urlencode({"q": query, "alpha": alpha, "top_n": top_n})
    url = f"{BASE_URL}/search?{params}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read())
    return data.get("results", [])


def compatibility_label(rank: int) -> str:
    if rank <= 3:
        return "likely_relevant"
    if rank <= 10:
        return "possibly_relevant"
    return "unclear"


def compatibility_reason(rank: int) -> str:
    return (
        f"Rank {rank} in hybrid retrieval (alpha=0.5). "
        "This label reflects retrieval score and rank only. "
        "It does not indicate clinical eligibility or suitability for trial participation."
    )


def build_match(rank: int, result: dict) -> dict:
    label = compatibility_label(rank)
    return {
        "rank": rank,
        "nct_id": result.get("nct_id", ""),
        "title": result.get("title", ""),
        "overall_status": result.get("overall_status", ""),
        "phase": result.get("phase", ""),
        "study_type": result.get("study_type", ""),
        "hybrid_score": result.get("hybrid_score"),
        "compatibility_label": label,
        "compatibility_reason": compatibility_reason(rank),
    }


def process_case(case: dict) -> dict:
    results = search(case["matching_query"], ALPHA, TOP_N)
    matches = [build_match(i + 1, r) for i, r in enumerate(results)]
    return {
        "case_id": case["case_id"],
        "matching_query": case["matching_query"],
        "target_category": case["target_category"],
        "matches": matches,
    }


def main() -> None:
    if not INPUT_PATH.exists():
        print(f"Error: input file not found — {INPUT_PATH}", file=sys.stderr)
        sys.exit(1)

    cases = json.loads(INPUT_PATH.read_text())
    output = []

    for case in cases:
        case_id = case.get("case_id", "?")
        print(f"Processing {case_id} — {case['matching_query'][:60]}...")
        try:
            output.append(process_case(case))
        except urllib.error.URLError as exc:
            print(
                f"  Connection error for {case_id}: {exc}. "
                "Is the FastAPI server running at http://localhost:8000?",
                file=sys.stderr,
            )
            sys.exit(1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"\nWrote {len(output)} cases to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
