"""
V2.4 experimental reranker comparison script.

Compares hybrid standard retrieval against hybrid + CrossEncoder reranking
over eval/queries.json.

Workflow:
  1. Retrieve top 50 candidates with the hybrid standard pipeline.
  2. Rerank those 50 candidates using a CrossEncoder model.
  3. Evaluate both orderings with Precision@5, Hit@5, Recall@10, and MRR.

Queries with empty relevant_nct_ids are skipped.
Does not modify the API, UI, or any existing retriever.

Run from the project root:
  python -m eval.compare_reranker
"""

import json
from pathlib import Path

import numpy as np
from sentence_transformers import CrossEncoder

try:
    from app.retrieval.bm25_retriever import retrieve as bm25_retrieve
    from app.retrieval.semantic_retriever import retrieve as semantic_retrieve
    from app.retrieval.hybrid_scorer import score as hybrid_score
    from app.db import get_connection, get_trial_by_nct_id
except ImportError:
    from bm25_retriever import retrieve as bm25_retrieve          # type: ignore[no-redef]
    from semantic_retriever import retrieve as semantic_retrieve  # type: ignore[no-redef]
    from hybrid_scorer import score as hybrid_score              # type: ignore[no-redef]
    from db import get_connection, get_trial_by_nct_id           # type: ignore[no-redef]

QUERIES_FILE = Path("eval/queries.json")
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RETRIEVAL_POOL = 50   # number of hybrid candidates passed to the reranker
TOP_K = 10            # cut-off for metric computation


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def retrieve_hybrid(query: str, top_k: int = RETRIEVAL_POOL) -> list[str]:
    """Return top-k NCT IDs from the hybrid standard pipeline."""
    bm25_results     = bm25_retrieve(query)
    semantic_results = semantic_retrieve(query)
    scored           = hybrid_score(bm25_results, semantic_results, alpha=0.5)
    return [r["nct_id"] for r in scored[:top_k]]


def rerank(query: str, nct_ids: list[str], model: CrossEncoder) -> list[str]:
    """Rerank nct_ids by CrossEncoder score against the query.

    Fetches each trial's search_text from the database to form the
    (query, passage) pairs that the CrossEncoder scores.
    Returns nct_ids sorted by descending reranker score.
    """
    conn = get_connection()
    pairs: list[tuple[str, str]] = []
    valid_ids: list[str] = []

    for nct_id in nct_ids:
        trial = get_trial_by_nct_id(conn, nct_id)
        if trial is None:
            continue
        pairs.append((query, trial.search_text))
        valid_ids.append(nct_id)

    conn.close()

    if not pairs:
        return []

    scores = model.predict(pairs)
    ranked = sorted(zip(valid_ids, scores), key=lambda x: x[1], reverse=True)
    return [nct_id for nct_id, _ in ranked]


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
        return

    print(f"Loading reranker model: {RERANKER_MODEL} ...")
    reranker = CrossEncoder(RERANKER_MODEL)

    totals = {
        "hybrid":   {"p5": 0.0, "h5": 0.0, "r10": 0.0, "mrr": 0.0},
        "reranked": {"p5": 0.0, "h5": 0.0, "r10": 0.0, "mrr": 0.0},
    }
    n = 0

    for item in scored_queries:
        query_id = item["query_id"]
        query    = item["query"]
        relevant = item["relevant_nct_ids"]
        print(f"  {query_id}: {query[:60]}...")

        try:
            pool = retrieve_hybrid(query, top_k=RETRIEVAL_POOL)
        except Exception as exc:
            print(f"    Retrieval error: {exc}")
            continue

        try:
            reranked = rerank(query, pool, reranker)
        except Exception as exc:
            print(f"    Reranker error: {exc}")
            continue

        m_hybrid   = evaluate(pool[:TOP_K], relevant)
        m_reranked = evaluate(reranked[:TOP_K], relevant)

        for key in totals["hybrid"]:
            totals["hybrid"][key]   += m_hybrid[key]
            totals["reranked"][key] += m_reranked[key]
        n += 1

    if n == 0:
        print("No queries could be evaluated.")
        return

    col = 22
    print(f"\nResults over {n} scored queries (retrieval pool={RETRIEVAL_POOL}, top_n={TOP_K})\n")
    print(f"{'Method':<{col}} {'P@5':>7} {'Hit@5':>7} {'R@10':>7} {'MRR':>7}")
    print("-" * (col + 30))

    for label, key in [("Hybrid standard", "hybrid"), ("Hybrid + reranker", "reranked")]:
        p5  = totals[key]["p5"]  / n
        h5  = totals[key]["h5"]  / n
        r10 = totals[key]["r10"] / n
        mrr = totals[key]["mrr"] / n
        print(f"{label:<{col}} {p5:>7.3f} {h5:>7.3f} {r10:>7.3f} {mrr:>7.3f}")


if __name__ == "__main__":
    main()
