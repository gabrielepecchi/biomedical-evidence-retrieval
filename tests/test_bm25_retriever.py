"""Tests for bm25_retriever.retrieve."""

import pickle

import pytest
from rank_bm25 import BM25Okapi

try:
    import app.retrieval.bm25_retriever as bm25_module
except ImportError:
    import bm25_retriever as bm25_module  # type: ignore[no-redef]


def _build_payload(corpus: list[tuple[str, str]]) -> bytes:
    """Return a serialised BM25 index payload from (nct_id, text) pairs."""
    nct_ids = [nct_id for nct_id, _ in corpus]
    tokenised = [text.lower().split() for _, text in corpus]
    index = BM25Okapi(tokenised)
    return pickle.dumps({"nct_ids": nct_ids, "index": index})


def test_exact_match_ranks_first(tmp_path, monkeypatch) -> None:
    """A query matching one document exactly should rank that document first."""
    index_file = tmp_path / "bm25_index.pkl"
    index_file.write_bytes(_build_payload([
        ("NCT001", "levodopa parkinson disease treatment"),
        ("NCT002", "insulin diabetes glucose control"),
        ("NCT003", "aspirin cardiovascular prevention"),
    ]))

    monkeypatch.setattr(bm25_module, "BM25_INDEX_PATH", index_file)

    results = bm25_module.retrieve("levodopa parkinson")

    assert len(results) > 0
    assert results[0]["nct_id"] == "NCT001"


def test_blank_query_returns_empty_list() -> None:
    """A blank or whitespace-only query should return an empty list immediately."""
    assert bm25_module.retrieve(" ") == []


def test_no_matching_tokens_returns_empty_list(tmp_path, monkeypatch) -> None:
    """A query with no matching tokens should return an empty list."""
    index_file = tmp_path / "bm25_index.pkl"
    index_file.write_bytes(_build_payload([
        ("NCT001", "levodopa parkinson disease"),
        ("NCT002", "insulin diabetes glucose"),
    ]))

    monkeypatch.setattr(bm25_module, "BM25_INDEX_PATH", index_file)

    results = bm25_module.retrieve("zzzzz xxxxxxxxx")

    assert results == []
