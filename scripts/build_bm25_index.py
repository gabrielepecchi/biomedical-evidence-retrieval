"""
Build and save the BM25 index from trial search_text fields in the database.

Reads all trials from SQLite, tokenises each document, builds a BM25Okapi
index, and saves it alongside the ordered NCT ID list to indexes/bm25_index.pkl.
Run this script once after ingest.py and before starting the API.
"""

import pickle
from pathlib import Path

from rank_bm25 import BM25Okapi

try:
    from app.db import BM25_INDEX_PATH, get_connection, get_all_trials
except ImportError:
    from db import BM25_INDEX_PATH, get_connection, get_all_trials  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------


def tokenise(text: str) -> list[str]:
    """
    Convert a document or query string into a list of tokens.

    Lowercase and whitespace-split only. This must be identical to the
    tokenisation used at query time in the BM25 retriever.
    """
    return text.lower().split()


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------


def build_bm25_index() -> None:
    """Read all trials from the database, build a BM25 index, and save it."""
    conn = get_connection()
    trials = get_all_trials(conn)
    conn.close()

    if not trials:
        print("No trials found in the database. Run ingest.py first.")
        return

    nct_ids  = [trial.nct_id for trial in trials]
    corpus   = [tokenise(trial.search_text) for trial in trials]
    index    = BM25Okapi(corpus)

    payload = {
        "nct_ids": nct_ids,
        "index":   index,
    }

    output_path: Path = BM25_INDEX_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pickle.dumps(payload))

    print(f"BM25 index built for {len(nct_ids)} trial(s).")
    print(f"Saved to {output_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    build_bm25_index()


if __name__ == "__main__":
    main()
