"""Combines BM25 and semantic retrieval scores into a single hybrid score."""


def _merge_results(
    bm25_results: list[dict[str, float | str]],
    semantic_results: list[dict[str, float | str]],
) -> dict[str, dict[str, float]]:
    """Merge BM25 and semantic results by nct_id, filling missing scores with 0.0."""
    merged: dict[str, dict[str, float]] = {}

    for item in bm25_results:
        nct_id = item["nct_id"]
        merged[nct_id] = {"bm25_score": float(item["bm25_score"]), "semantic_score": 0.0}

    for item in semantic_results:
        nct_id = item["nct_id"]
        if nct_id in merged:
            merged[nct_id]["semantic_score"] = float(item["semantic_score"])
        else:
            merged[nct_id] = {"bm25_score": 0.0, "semantic_score": float(item["semantic_score"])}

    return merged


def score(
    bm25_results: list[dict[str, float | str]],
    semantic_results: list[dict[str, float | str]],
    alpha: float = 0.5,
) -> list[dict[str, float | str]]:
    """Compute hybrid scores from BM25 and semantic results.

    Args:
        bm25_results: List of dicts with 'nct_id' and 'bm25_score' from bm25_retriever.
        semantic_results: List of dicts with 'nct_id' and 'semantic_score' from semantic_retriever.
        alpha: Weight for BM25 score. Must be between 0.0 and 1.0 inclusive.
               Semantic weight is (1 - alpha).

    Returns:
        List of dicts with 'nct_id', 'bm25_score', 'semantic_score', and 'hybrid_score',
        sorted descending by hybrid_score.

    Raises:
        ValueError: If alpha is not between 0.0 and 1.0.
    """
    if alpha < 0.0 or alpha > 1.0:
        raise ValueError(f"alpha must be between 0.0 and 1.0, got {alpha}")

    merged = _merge_results(bm25_results, semantic_results)

    results: list[dict[str, float | str]] = []
    for nct_id, scores in merged.items():
        bm25_score = scores["bm25_score"]
        semantic_score = scores["semantic_score"]
        hybrid_score = alpha * bm25_score + (1 - alpha) * semantic_score
        results.append(
            {
                "nct_id": nct_id,
                "bm25_score": bm25_score,
                "semantic_score": semantic_score,
                "hybrid_score": hybrid_score,
            }
        )

    results.sort(key=lambda x: x["hybrid_score"], reverse=True)
    return results
