"""Smoke tests for the FastAPI app in main.py."""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

try:
    import app.db as db_module
    from app.api.main import app
except ImportError:
    import db as db_module  # type: ignore[no-redef]
    from main import app  # type: ignore[no-redef]


def _create_empty_db(db_path: Path) -> None:
    """Create the schema in a temporary SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    db_module.create_schema(conn)
    conn.close()


def test_health_endpoint(tmp_path, monkeypatch) -> None:
    """GET /health should return 200 with status and corpus_size."""
    db_file = tmp_path / "trials.db"
    _create_empty_db(db_file)
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "corpus_size" in data


def test_openapi_docs_available() -> None:
    """GET /openapi.json should return 200 with standard OpenAPI fields."""
    client = TestClient(app)
    response = client.get("/openapi.json")

    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "paths" in data
