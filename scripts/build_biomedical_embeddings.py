"""
Build and save sentence embeddings using a biomedical-domain model (V2.3).

Reads all trials from SQLite, encodes each search_text field using
FremyCompany/BioLORD-2023, saves the embedding matrix to
indexes/biomedical_embeddings.npy, and saves a JSON index mapping
each nct_id to its row in the matrix to indexes/biomedical_embedding_index.json.

This script is standalone and does not modify the embedding_index database
table or the general embeddings file produced by build_embeddings.py.
Run it once after ingest.py.
"""

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

try:
    from app.db import get_connection, get_all_trials
except ImportError:
    from db import get_connection, get_all_trials  # type: ignore[no-redef]

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BIOMEDICAL_MODEL_NAME: str = "FremyCompany/BioLORD-2023"
BIOMEDICAL_EMBEDDINGS_PATH: Path = Path("indexes") / "biomedical_embeddings.npy"
BIOMEDICAL_INDEX_PATH: Path = Path("indexes") / "biomedical_embedding_index.json"
BATCH_SIZE: int = 64


# ---------------------------------------------------------------------------
# Embedding builder
# ---------------------------------------------------------------------------


def build_biomedical_embeddings() -> None:
    """Encode all trial search_text fields with a biomedical model and save the matrix."""
    conn = get_connection()
    trials = get_all_trials(conn)
    conn.close()

    if not trials:
        print("No trials found in the database. Run ingest.py first.")
        return

    nct_ids = [trial.nct_id for trial in trials]
    texts   = [trial.search_text for trial in trials]

    print(f"Loading model: {BIOMEDICAL_MODEL_NAME}")
    model = SentenceTransformer(BIOMEDICAL_MODEL_NAME)

    print(f"Encoding {len(texts)} trial(s) with batch size {BATCH_SIZE} ...")
    matrix = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
    )

    BIOMEDICAL_EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.save(BIOMEDICAL_EMBEDDINGS_PATH, matrix)

    index = {nct_id: row for row, nct_id in enumerate(nct_ids)}
    BIOMEDICAL_INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")

    print(f"\nEmbeddings built.")
    print(f"  Model           : {BIOMEDICAL_MODEL_NAME}")
    print(f"  Trials embedded : {len(nct_ids)}")
    print(f"  Matrix shape    : {matrix.shape}")
    print(f"  Embeddings      : {BIOMEDICAL_EMBEDDINGS_PATH}")
    print(f"  Index           : {BIOMEDICAL_INDEX_PATH}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    build_biomedical_embeddings()


if __name__ == "__main__":
    main()
