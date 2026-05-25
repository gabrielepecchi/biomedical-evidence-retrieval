"""
Build and save sentence embeddings for all trials in the database.

Reads all trials from SQLite, encodes each search_text field using a
SentenceTransformer model, saves the embedding matrix to indexes/embeddings.npy,
and records each nct_id's row index in the embedding_index table.
Run this script once after ingest.py and before starting the API.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

try:
    from app.db import (
        EMBEDDING_MODEL_NAME,
        EMBEDDINGS_PATH,
        get_connection,
        get_all_trials,
    )
except ImportError:
    from db import (  # type: ignore[no-redef]
        EMBEDDING_MODEL_NAME,
        EMBEDDINGS_PATH,
        get_connection,
        get_all_trials,
    )

BATCH_SIZE: int = 64


# ---------------------------------------------------------------------------
# Index table helpers
# ---------------------------------------------------------------------------


def clear_embedding_index(conn) -> None:
    """Remove all rows from embedding_index so it can be rebuilt cleanly."""
    conn.execute("DELETE FROM embedding_index")


def insert_embedding_index(conn, nct_ids: list[str]) -> None:
    """Insert one row per nct_id mapping it to its position in the matrix."""
    rows = [(nct_id, row_index) for row_index, nct_id in enumerate(nct_ids)]
    conn.executemany(
        "INSERT OR REPLACE INTO embedding_index (nct_id, embedding_row) VALUES (?, ?)",
        rows,
    )


# ---------------------------------------------------------------------------
# Embedding builder
# ---------------------------------------------------------------------------


def build_embeddings() -> None:
    """Encode all trial search_text fields and save the embedding matrix."""
    conn = get_connection()
    trials = get_all_trials(conn)

    if not trials:
        print("No trials found in the database. Run ingest.py first.")
        conn.close()
        return

    nct_ids = [trial.nct_id for trial in trials]
    texts   = [trial.search_text for trial in trials]

    print(f"Loading model: {EMBEDDING_MODEL_NAME}")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    print(f"Encoding {len(texts)} trial(s) with batch size {BATCH_SIZE} ...")
    matrix = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
    )

    output_path = EMBEDDINGS_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, matrix)

    clear_embedding_index(conn)
    insert_embedding_index(conn, nct_ids)
    conn.commit()
    conn.close()

    print(f"\nEmbeddings built.")
    print(f"  Trials embedded : {len(nct_ids)}")
    print(f"  Matrix shape    : {matrix.shape}")
    print(f"  Saved to        : {output_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    build_embeddings()


if __name__ == "__main__":
    main()
