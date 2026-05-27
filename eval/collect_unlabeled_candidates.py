"""
Multi-method candidate pooling script for V3.6.

Collects top-10 candidates per query from multiple retrieval methods:
  - BM25-only
  - Semantic-only (standard model)
  - Hybrid alpha=0.5
  - Biomedical semantic (BioLORD), if indexes are available

Deduplicates candidates by nct_id within each query and records which
method(s) produced each candidate. Writes the pooled output to
eval/unlabeled_candidates_alpha_0_5.json for future manual relevance auditing.

Does NOT call the API. Does NOT modify eval/queries.json.
Does NOT change any relevance labels or benchmark scores.

Usage:
    python -m eval.collect_unlabeled_candidates
"""

import json
from pathlib import Path

from app.retrieval.bm25_retriever import retrieve as bm25_retrieve
from app.retrieval.semantic_retriever import retrieve as semantic_retrieve
from app.retrieval.hybrid_scorer import score as hybrid_score

# Attempt to import the biomedical retriever; warn and skip if unavailable.
try:
    from app.retrieval.biomedical_semantic_retriever import retrieve as bio_retrieve
    _BIO_AVAILABLE = True
except Exception:
    bio_retrieve = None
    _BIO_AVAILABLE = False

QUERIES_PATH = Path("eval/queries.json")
OUTPUT_PATH = Path("eval/unlabeled_candidates_alpha_0_5.json")
NCT_BASE_URL = "https://clinicaltrials.gov/study/"
TOP_N = 10
ALPHA = 0.5


# ---------------------------------------------------------------------------
# Per-method retrieval helpers
# ---------------------------------------------------------------------------


def run_bm25(query: str) -> dict[str, float]:
    """Return {nct_id: bm25_score} for top-N BM25 results."""
    results = bm25_retrieve(query, top_k=TOP_N)
    return {r["nct_id"]: float(r.get("bm25_score", 0.0)) for r in results}


def run_semantic(query: str) -> dict[str, float]:
    """Return {nct_id: semantic_score} for top-N semantic results."""
    results = semantic_retrieve(query, top_k=TOP_N)
    return {r["nct_id"]: float(r.get("semantic_score", 0.0)) for r in results}


def run_hybrid(query: str) -> dict[str, float]:
    """Return {nct_id: hybrid_score} for top-N hybrid results at alpha=0.5."""
    bm25_results = bm25_retrieve(query)
    semantic_results = semantic_retrieve(query)
    scored = hybrid_score(bm25_results, semantic_results, alpha=ALPHA)
    return {r["nct_id"]: float(r.get("hybrid_score", 0.0)) for r in scored[:TOP_N]}


def run_biomedical(query: str) -> dict[str, float]:
    """Return {nct_id: biomedical_semantic_score} for top-N BioLORD results."""
    results = bio_retrieve(query, top_k=TOP_N)
    return {r["nct_id"]: float(r.get("semantic_score", 0.0)) for r in results}


# ---------------------------------------------------------------------------
# Pooling
# ---------------------------------------------------------------------------


def pool_candidates(
    bm25_hits: dict[str, float],
    semantic_hits: dict[str, float],
    hybrid_hits: dict[str, float],
    bio_hits: dict[str, float] | None,
) -> list[dict]:
    """Merge results from all methods, deduplicate by nct_id, record sources."""
    # Collect all unique nct_ids across methods.
    all_nct_ids: set[str] = set(bm25_hits) | set(semantic_hits) | set(hybrid_hits)
    if bio_hits:
        all_nct_ids |= set(bio_hits)

    candidates = []
    for nct_id in all_nct_ids:
        sources = []
        scores: dict[str, float | None] = {}

        if nct_id in bm25_hits:
            sources.append("bm25")
            scores["bm25_score"] = bm25_hits[nct_id]

        if nct_id in semantic_hits:
            sources.append("semantic")
            scores["semantic_score"] = semantic_hits[nct_id]

        if nct_id in hybrid_hits:
            sources.append("hybrid")
            scores["hybrid_score"] = hybrid_hits[nct_id]

        if bio_hits and nct_id in bio_hits:
            sources.append("biomedical_semantic")
            scores["biomedical_semantic_score"] = bio_hits[nct_id]

        candidates.append({
            "nct_id": nct_id,
            "sources": sources,
            "scores": scores,
            "url": f"{NCT_BASE_URL}{nct_id}",
        })

    # Sort by hybrid_score descending where available, then bm25_score.
    candidates.sort(
        key=lambda c: (
            c["scores"].get("hybrid_score") or 0.0,
            c["scores"].get("bm25_score") or 0.0,
        ),
        reverse=True,
    )
    return candidates


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if not _BIO_AVAILABLE:
        print(
            "Warning: biomedical embeddings not available. "
            "Run build_biomedical_embeddings.py to enable BioLORD candidates. "
            "Continuing without biomedical_semantic method.\n"
        )

    queries = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    output = []

    bio_enabled = _BIO_AVAILABLE

    for q in queries:
        query_id = q["query_id"]
        query_text = q["query"]
        print(f"Processing {query_id}: {query_text[:60]}...")

        bm25_hits = run_bm25(query_text)
        semantic_hits = run_semantic(query_text)
        hybrid_hits = run_hybrid(query_text)

        bio_hits = None
        if bio_enabled:
            try:
                bio_hits = run_biomedical(query_text)
            except Exception as exc:
                print(
                    f"Warning: biomedical retrieval failed ({exc}). "
                    "Disabling BioLORD for remaining queries."
                )
                bio_enabled = False
                bio_hits = None

        candidates = pool_candidates(bm25_hits, semantic_hits, hybrid_hits, bio_hits)

        output.append({
            "query_id": query_id,
            "category": q.get("category", ""),
            "query": query_text,
            "candidates": candidates,
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {len(output)} queries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
