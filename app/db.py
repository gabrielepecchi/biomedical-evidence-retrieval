"""
Database access layer for the Biomedical Evidence Retrieval and Trial Matching Platform.

All SQLite connections and queries are centralised here. No other module
should open a database connection directly.

Path constants for all data artefacts are defined here and imported
wherever they are needed.
"""

import sqlite3
from pathlib import Path

try:
    from app.models import TrialRecord
except ImportError:
    from models import TrialRecord  # type: ignore[no-redef]

# ---------------------------------------------------------------------------
# Path constants — edit these if the project layout changes.
# ---------------------------------------------------------------------------

DB_PATH: Path = Path("db") / "trials.db"
BM25_INDEX_PATH: Path = Path("indexes") / "bm25_index.pkl"
EMBEDDINGS_PATH: Path = Path("indexes") / "embeddings.npy"
EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """
    Return a SQLite connection to the trials database.

    Defaults to DB_PATH. Pass an alternative path (e.g. `:memory:` wrapped
    in a Path, or a temp file) to inject a test database without touching
    the real file.

    Parent directories are created automatically. row_factory is set to
    sqlite3.Row so columns are accessible by name.
    """
    resolved = db_path if db_path is not None else DB_PATH
    if str(resolved) != ":memory:":
        resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def create_schema(conn: sqlite3.Connection) -> None:
    """
    Create all V1 tables if they do not already exist.

    Safe to call multiple times — uses CREATE TABLE IF NOT EXISTS throughout.
    Tables: trials, conditions, interventions, embedding_index.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS trials (
            nct_id               TEXT PRIMARY KEY,
            title                TEXT NOT NULL,
            brief_summary        TEXT,
            overall_status       TEXT,
            phase                TEXT,
            study_type           TEXT,
            sponsor_name         TEXT,
            start_date           TEXT,
            eligibility_criteria TEXT,
            minimum_age          TEXT,
            maximum_age          TEXT,
            sex                  TEXT,
            url                  TEXT NOT NULL,
            search_text          TEXT NOT NULL,
            ingested_at          TEXT
        );

        CREATE TABLE IF NOT EXISTS conditions (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nct_id    TEXT NOT NULL REFERENCES trials(nct_id),
            condition TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS interventions (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            nct_id            TEXT NOT NULL REFERENCES trials(nct_id),
            intervention_type TEXT,
            intervention_name TEXT
        );

        CREATE TABLE IF NOT EXISTS embedding_index (
            nct_id        TEXT PRIMARY KEY REFERENCES trials(nct_id),
            embedding_row INTEGER NOT NULL
        );
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


def get_corpus_size(conn: sqlite3.Connection) -> int:
    """Return the total number of trial records in the database."""
    row = conn.execute("SELECT COUNT(*) FROM trials").fetchone()
    return int(row[0])


def _fetch_conditions(conn: sqlite3.Connection, nct_id: str) -> list[str]:
    """Return all condition name strings for the given trial."""
    rows = conn.execute(
        "SELECT condition FROM conditions WHERE nct_id = ? ORDER BY id",
        (nct_id,),
    ).fetchall()
    return [row["condition"] for row in rows]


def _fetch_interventions(
    conn: sqlite3.Connection, nct_id: str
) -> list[dict[str, str | None]]:
    """
    Return all intervention dicts for the given trial.

    Each dict has keys intervention_type and intervention_name.
    Either value may be None if the source data did not include it.
    """
    rows = conn.execute(
        "SELECT intervention_type, intervention_name "
        "FROM interventions WHERE nct_id = ? ORDER BY id",
        (nct_id,),
    ).fetchall()
    return [
        {
            "intervention_type": row["intervention_type"],
            "intervention_name": row["intervention_name"],
        }
        for row in rows
    ]


def _row_to_trial_record(
    row: sqlite3.Row,
    conditions: list[str],
    interventions: list[dict[str, str | None]],
) -> TrialRecord:
    """
    Convert a sqlite3.Row from the trials table into a TrialRecord.

    Accepts pre-fetched conditions and interventions so callers can
    batch those queries when processing many rows.
    """
    return TrialRecord(
        nct_id=row["nct_id"],
        title=row["title"],
        url=row["url"],
        search_text=row["search_text"],
        brief_summary=row["brief_summary"],
        overall_status=row["overall_status"],
        phase=row["phase"],
        study_type=row["study_type"],
        sponsor_name=row["sponsor_name"],
        start_date=row["start_date"],
        eligibility_criteria=row["eligibility_criteria"],
        minimum_age=row["minimum_age"],
        maximum_age=row["maximum_age"],
        sex=row["sex"],
        ingested_at=row["ingested_at"],
        conditions=conditions,
        interventions=interventions,
    )


def get_trial_by_nct_id(
    conn: sqlite3.Connection, nct_id: str
) -> TrialRecord | None:
    """
    Fetch a single trial by NCT ID.

    Returns a fully populated TrialRecord including conditions and
    interventions, or None if the NCT ID is not in the database.
    """
    row = conn.execute(
        "SELECT * FROM trials WHERE nct_id = ?", (nct_id,)
    ).fetchone()

    if row is None:
        return None

    conditions = _fetch_conditions(conn, nct_id)
    interventions = _fetch_interventions(conn, nct_id)
    return _row_to_trial_record(row, conditions, interventions)


def get_all_trials(conn: sqlite3.Connection) -> list[TrialRecord]:
    """
    Return all trials ordered by nct_id, each with conditions and interventions.

    ORDER BY nct_id guarantees a stable row order across runs so that
    embedding_index row numbers remain valid.
    """
    rows = conn.execute("SELECT * FROM trials ORDER BY nct_id").fetchall()

    trials: list[TrialRecord] = []
    for row in rows:
        nct_id = row["nct_id"]
        conditions = _fetch_conditions(conn, nct_id)
        interventions = _fetch_interventions(conn, nct_id)
        trials.append(_row_to_trial_record(row, conditions, interventions))

    return trials