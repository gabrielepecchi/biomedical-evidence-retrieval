"""Tests for semantic_retriever.retrieve."""

import numpy as np
import pytest

try:
    import app.retrieval.semantic_retriever as sem_module
except ImportError:
    import semantic_retriever as sem_module  # type: ignore[no-redef]


def _reset_caches() -> None:
    """Reset module-level caches so each test loads fresh data."""
    sem_module._EMBEDDINGS = None
    sem_module._NCT_IDS = None


def test_blank_query_returns_empty_list() -> None:
    """A blank or whitespace-only query should return an empty list immediately."""
    assert sem_module.retrieve(" ") == []


def test_missing_embeddings_file_raises(tmp_path, monkeypatch) -> None:
    """retrieve should raise FileNotFoundError when the embeddings file does not exist."""
    missing = tmp_path / "nonexistent.npy"
    monkeypatch.setattr(sem_module, "EMBEDDINGS_PATH", missing)
    _reset_caches()

    with pytest.raises(FileNotFoundError):
        sem_module.retrieve("parkinson levodopa")


def test_row_count_mismatch_raises(tmp_path, monkeypatch) -> None:
    """retrieve should raise ValueError when embeddings rows and nct_id count differ."""
    embeddings_file = tmp_path / "embeddings.npy"
    matrix = np.random.rand(2, 384).astype("float32")
    np.save(embeddings_file, matrix)

    monkeypatch.setattr(sem_module, "EMBEDDINGS_PATH", embeddings_file)
    monkeypatch.setattr(sem_module, "get_nct_ids", lambda: ["NCT001", "NCT002", "NCT003"])
    _reset_caches()

    with pytest.raises(ValueError):
        sem_module.retrieve("parkinson levodopa")
