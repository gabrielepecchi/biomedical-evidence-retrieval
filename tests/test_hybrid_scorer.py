"""Tests for hybrid_scorer.score."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

try:
    from app.retrieval.hybrid_scorer import score
except ImportError:
    from hybrid_scorer import score  # type: ignore[no-redef]


def test_alpha_1_follows_bm25() -> None:
    """With alpha=1.0, hybrid score should equal bm25_score and rank by BM25."""
    bm25_results = [
        {"nct_id": "NCT001", "bm25_score": 0.9},
        {"nct_id": "NCT002", "bm25_score": 0.5},
    ]
    semantic_results = [
        {"nct_id": "NCT001", "semantic_score": 0.2},
        {"nct_id": "NCT002", "semantic_score": 0.8},
    ]

    results = score(bm25_results, semantic_results, alpha=1.0)

    assert results[0]["nct_id"] == "NCT001"
    assert results[0]["hybrid_score"] == pytest.approx(0.9)


def test_alpha_0_follows_semantic() -> None:
    """With alpha=0.0, hybrid score should equal semantic_score and rank by semantic."""
    bm25_results = [
        {"nct_id": "NCT001", "bm25_score": 0.9},
        {"nct_id": "NCT002", "bm25_score": 0.3},
    ]
    semantic_results = [
        {"nct_id": "NCT001", "semantic_score": 0.2},
        {"nct_id": "NCT002", "semantic_score": 0.8},
    ]

    results = score(bm25_results, semantic_results, alpha=0.0)

    assert results[0]["nct_id"] == "NCT002"
    assert results[0]["hybrid_score"] == pytest.approx(0.8)


def test_missing_score_treated_as_zero() -> None:
    """An nct_id appearing in only one list should have 0.0 for the missing side."""
    bm25_results = [
        {"nct_id": "NCT001", "bm25_score": 0.7},
    ]
    semantic_results = [
        {"nct_id": "NCT002", "semantic_score": 0.6},
    ]

    results = score(bm25_results, semantic_results, alpha=0.5)

    nct_ids = [r["nct_id"] for r in results]
    assert "NCT001" in nct_ids
    assert "NCT002" in nct_ids

    nct001 = next(r for r in results if r["nct_id"] == "NCT001")
    nct002 = next(r for r in results if r["nct_id"] == "NCT002")

    assert nct001["semantic_score"] == 0.0
    assert nct002["bm25_score"] == 0.0
