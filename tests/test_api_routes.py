"""Tests for the FastAPI routes: /health and /summary/{nct_id}."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

try:
    import app.db as db_module
    from app.api.routes import router
except ImportError:
    import db as db_module  # type: ignore[no-redef]
    from routes import router  # type: ignore[no-redef]

from fastapi import FastAPI


def _make_app() -> FastAPI:
    """Create a minimal FastAPI app with the real router attached."""
    app = FastAPI()
    app.include_router(router)
    return app


def _setup_db(db_path: Path) -> None:
    """Create schema and insert one fake trial into a temporary database."""
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


def test_health_returns_status_and_corpus_size(tmp_path, monkeypatch) -> None:
    """GET /health should return status and corpus_size matching the database."""
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
    """GET /summary/{nct_id} should return summary fields for a known trial."""
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
    """GET /summary/{nct_id} should return 404 for an unknown trial."""
    db_file = tmp_path / "trials.db"
    _setup_db(db_file)
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    client = TestClient(_make_app())
    response = client.get("/summary/NCT000000000")

    assert response.status_code == 404
