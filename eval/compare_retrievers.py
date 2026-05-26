"""
V2.3 retriever comparison script.

Compares four retrieval methods over eval/queries.json:
  - BM25-only          (alpha=1.0)
  - Semantic standard  (alpha=0.0, general model)
  - Semantic biomedical(alpha=0.0, BioLORD model)
  - Hybrid standard    (alpha=0.5, BM25 + general semantic)

Metrics: Precision@5, Hit@5, Recall@10, MRR.
Queries with empty relevant_nct_ids are skipped.

Run with the API NOT required — retrieval is called directly.
"""

import json
import sys
from pathlib import Path

try:
    from app.retrieval.bm25_retriever import retrieve as bm25_retrieve
    from app.retrieval.semantic_retriever import retrieve as semantic_retrieve
    from app.retrieval.hybrid_scorer import score as hybrid_score
except ImportError:
    from bm25_retriever import retrieve as bm25_retrieve          # type: ignore[no-redef]
    from semantic_retriever import retrieve as semantic_retrieve  # type: ignore[no-redef]
    from hybrid_scorer import score as hybrid_score              # type: ignore[no-redef]

try:
    from app.retrieval.biomedical_semantic_retriever import retrieve as bio_retrieve
except ImportError:
    from biomedical_semantic_retriever import retrieve as bio_retrieve  # type: ignore[no-redef]

QUERIES_FILE = Path("eval/queries.json")
TOP_K = 10


# ---------------------------------------------------------------------------
# Retrieval methods
# ---------------------------------------------------------------------------


def retrieve_bm25(query: str) -> list[str]:
    return [r["nct_id"] for r in bm25_retrieve(query, top_k=TOP_K)]


def retrieve_semantic_standard(query: str) -> list[str]:
    return [r["nct_id"] for r in semantic_retrieve(query, top_k=TOP_K)]


def retrieve_semantic_biomedical(query: str) -> list[str]:
    return [r["nct_id"] for r in bio_retrieve(query, top_k=TOP_K)]


def retrieve_hybrid_standard(query: str) -> list[str]:
    bm25_results = bm25_retrieve(query)
    semantic_results = semantic_retrieve(query)
    scored = hybrid_score(bm25_results, semantic_results, alpha=0.5)
    return [r["nct_id"] for r in scored[:TOP_K]]


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    top_k = retrieved[:k]
    return sum(1 for r in top_k if r in relevant) / k if top_k else 0.0


def hit_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    return 1.0 if any(r in relevant for r in retrieved[:k]) else 0.0


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    return sum(1 for r in retrieved[:k] if r in relevant) / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    for i, r in enumerate(retrieved, start=1):
        if r in relevant:
            return 1.0 / i
    return 0.0


def evaluate(retrieved: list[str], relevant: list[str]) -> dict[str, float]:
    return {
        "p5":  precision_at_k(retrieved, relevant, 5),
        "h5":  hit_at_k(retrieved, relevant, 5),
        "r10": recall_at_k(retrieved, relevant, 10),
        "mrr": reciprocal_rank(retrieved, relevant),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    queries = json.loads(QUERIES_FILE.read_text(encoding="utf-8"))
    scored_queries = [q for q in queries if q.get("relevant_nct_ids")]

    if not scored_queries:
        print("No queries with relevance labels found in queries.json.")
        sys.exit(1)

    methods = {
        "BM25-only":           retrieve_bm25,
        "Semantic standard":   retrieve_semantic_standard,
        "Semantic biomedical": retrieve_semantic_biomedical,
        "Hybrid standard":     retrieve_hybrid_standard,
    }

    # Accumulate scores per method.
    totals: dict[str, dict[str, float]] = {name: {"p5": 0.0, "h5": 0.0, "r10": 0.0, "mrr": 0.0} for name in methods}
    counts: dict[str, int] = {name: 0 for name in methods}

    for item in scored_queries:
        relevant = item["relevant_nct_ids"]
        query    = item["query"]
        print(f"  {item['query_id']}: {query[:60]}...")

        for name, fn in methods.items():
            try:
                retrieved = fn(query)
            except Exception as exc:
                print(f"    [{name}] error: {exc}")
                continue
            m = evaluate(retrieved, relevant)
            for key in totals[name]:
                totals[name][key] += m[key]
            counts[name] += 1

    # Print table.
    n = len(scored_queries)
    col = 22
    print(f"\nResults over {n} scored queries (top_n={TOP_K})\n")
    print(f"{'Method':<{col}} {'P@5':>7} {'Hit@5':>7} {'R@10':>7} {'MRR':>7}")
    print("-" * (col + 30))

    for name in methods:
        c = counts[name]
        if c == 0:
            print(f"{name:<{col}} {'ERROR':>7}")
            continue
        p5  = totals[name]["p5"]  / c
        h5  = totals[name]["h5"]  / c
        r10 = totals[name]["r10"] / c
        mrr = totals[name]["mrr"] / c
        print(f"{name:<{col}} {p5:>7.3f} {h5:>7.3f} {r10:>7.3f} {mrr:>7.3f}")


if __name__ == "__main__":
    main()
