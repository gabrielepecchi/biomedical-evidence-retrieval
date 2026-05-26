"""Tests for the FastAPI routes: /health, /summary/{nct_id}, and /search filters."""

import sys
from pathlib import Path

# Ensure the project root is on sys.path when running:
#   pytest tests/test_api_routes.py
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import sqlite3
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

try:
    import app.db as db_module
    import app.api.routes as routes_module
except ImportError:
    import db as db_module  # type: ignore[no-redef]
    import routes as routes_module  # type: ignore[no-redef]

try:
    from app.api.routes import router
except ImportError:
    from routes import router  # type: ignore[no-redef]

from fastapi import FastAPI


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _setup_db(db_path: Path) -> None:
    """Create schema and insert one fake trial."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    db_module.create_schema(conn)
    conn.execute(
        """
        INSERT OR IGNORE INTO trials (
            nct_id, title, brief_summary, overall_status, phase,
            study_type, sponsor_name, start_date, eligibility_criteria,
            minimum_age, maximum_age, sex, url, search_text, ingested_at
        ) VALUES (
            'NCT999001', 'Test Trial for Parkinson Disease',
            'This study tests a new treatment.', 'Recruiting', 'Phase 2',
            'Interventional', 'Test Sponsor', '2023-01-01',
            'Inclusion: adults over 40.', '40 Years', '80 Years', 'All',
            'https://clinicaltrials.gov/study/NCT999001',
            'test trial parkinson disease treatment',
            :ingested_at
        )
        """,
        {"ingested_at": datetime.now(timezone.utc).isoformat()},
    )
    conn.commit()
    conn.close()


def _setup_db_multi(db_path: Path) -> None:
    """Create schema and insert three trials with varied filter fields."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    db_module.create_schema(conn)
    now = datetime.now(timezone.utc).isoformat()
    trials = [
        (
            "NCT999001", "Parkinson Treatment A", "Study A.", "Recruiting", "Phase 2",
            "Interventional", "Sponsor A", "2023-01-01", "Inclusion: adults.",
            "40 Years", "80 Years", "All",
            "https://clinicaltrials.gov/study/NCT999001",
            "parkinson treatment levodopa", now,
        ),
        (
            "NCT999002", "Parkinson Treatment B", "Study B.", "Completed", "Phase 3",
            "Observational", "Sponsor B", "2022-06-01", "Inclusion: adults.",
            "50 Years", "75 Years", "All",
            "https://clinicaltrials.gov/study/NCT999002",
            "parkinson treatment dopamine", now,
        ),
        (
            "NCT999003", "Parkinson Treatment C", "Study C.", "Recruiting", "Phase 3",
            "Interventional", "Sponsor C", "2021-03-01", "Inclusion: adults.",
            "45 Years", "70 Years", "Female",
            "https://clinicaltrials.gov/study/NCT999003",
            "parkinson gait wearable sensor", now,
        ),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO trials (
            nct_id, title, brief_summary, overall_status, phase,
            study_type, sponsor_name, start_date, eligibility_criteria,
            minimum_age, maximum_age, sex, url, search_text, ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        trials,
    )
    conn.commit()
    conn.close()


# Fake retrieval returns all three NCT IDs with descending scores.
_FAKE_BM25 = [
    {"nct_id": "NCT999001", "bm25_score": 1.0},
    {"nct_id": "NCT999002", "bm25_score": 0.9},
    {"nct_id": "NCT999003", "bm25_score": 0.8},
]
_FAKE_SEMANTIC = [
    {"nct_id": "NCT999001", "semantic_score": 1.0},
    {"nct_id": "NCT999002", "semantic_score": 0.9},
    {"nct_id": "NCT999003", "semantic_score": 0.8},
]
_FAKE_HYBRID = [
    {"nct_id": "NCT999001", "bm25_score": 1.0, "semantic_score": 1.0, "hybrid_score": 1.0},
    {"nct_id": "NCT999002", "bm25_score": 0.9, "semantic_score": 0.9, "hybrid_score": 0.9},
    {"nct_id": "NCT999003", "bm25_score": 0.8, "semantic_score": 0.8, "hybrid_score": 0.8},
]


def _search_with_mocks(client: TestClient, **params) -> list[dict]:
    """Call /search with retrieval mocked to return the three fake trials."""
    with (
        patch.object(routes_module, "bm25_retrieve", return_value=_FAKE_BM25),
        patch.object(routes_module, "semantic_retrieve", return_value=_FAKE_SEMANTIC),
        patch.object(routes_module, "hybrid_score", return_value=_FAKE_HYBRID),
    ):
        response = client.get("/search", params={"q": "parkinson", **params})
    assert response.status_code == 200
    return response.json()["results"]


# ---------------------------------------------------------------------------
# Existing tests (unchanged)
# ---------------------------------------------------------------------------


def test_health_returns_status_and_corpus_size(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "trials.db"
    _setup_db(db_file)
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    client = TestClient(_make_app())
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "corpus_size" in data
    assert data["corpus_size"] >= 1


def test_summary_valid_nct_id(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "trials.db"
    _setup_db(db_file)
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    client = TestClient(_make_app())
    response = client.get("/summary/NCT999001")

    assert response.status_code == 200
    data = response.json()
    assert "nct_id" in data
    assert "summary" in data
    assert "fields_used" in data
    assert data["nct_id"] == "NCT999001"


def test_summary_missing_nct_id_returns_404(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "trials.db"
    _setup_db(db_file)
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    client = TestClient(_make_app())
    response = client.get("/summary/NCT000000000")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Filter tests
# ---------------------------------------------------------------------------


def test_filter_overall_status_returns_matching_only(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "trials.db"
    _setup_db_multi(db_file)
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    client = TestClient(_make_app())
    results = _search_with_mocks(client, overall_status="Completed")

    assert len(results) >= 1
    for r in results:
        assert r["overall_status"].lower() == "completed"


def test_filter_overall_status_case_insensitive(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "trials.db"
    _setup_db_multi(db_file)
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    client = TestClient(_make_app())
    results_lower = _search_with_mocks(client, overall_status="recruiting")
    results_upper = _search_with_mocks(client, overall_status="RECRUITING")

    assert len(results_lower) == len(results_upper)
    assert all(r["overall_status"].lower() == "recruiting" for r in results_lower)


def test_filter_phase_returns_matching_only(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "trials.db"
    _setup_db_multi(db_file)
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    client = TestClient(_make_app())
    results = _search_with_mocks(client, phase="Phase 3")

    assert len(results) >= 1
    for r in results:
        assert r["phase"].lower() == "phase 3"


def test_filter_study_type_returns_matching_only(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "trials.db"
    _setup_db_multi(db_file)
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    client = TestClient(_make_app())
    results = _search_with_mocks(client, study_type="Observational")

    assert len(results) >= 1
    for r in results:
        assert r["study_type"].lower() == "observational"


def test_filter_combined_status_and_phase(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "trials.db"
    _setup_db_multi(db_file)
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    client = TestClient(_make_app())
    results = _search_with_mocks(client, overall_status="Recruiting", phase="Phase 3")

    assert len(results) >= 1
    for r in results:
        assert r["overall_status"].lower() == "recruiting"
        assert r["phase"].lower() == "phase 3"


def test_filter_no_match_returns_empty(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "trials.db"
    _setup_db_multi(db_file)
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    client = TestClient(_make_app())
    results = _search_with_mocks(client, overall_status="Withdrawn")

    assert results == []


def test_filter_results_ranked_from_one(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "trials.db"
    _setup_db_multi(db_file)
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    client = TestClient(_make_app())
    results = _search_with_mocks(client, overall_status="Recruiting")

    ranks = [r["rank"] for r in results]
    assert ranks == list(range(1, len(ranks) + 1))


def test_search_result_includes_study_type(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "trials.db"
    _setup_db_multi(db_file)
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    client = TestClient(_make_app())
    results = _search_with_mocks(client)

    assert len(results) > 0
    assert "study_type" in results[0]
