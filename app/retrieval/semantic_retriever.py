"""
Semantic retriever for the Biomedical Evidence Retrieval and Trial Matching Platform.

Encodes a query with a SentenceTransformer model, computes cosine similarity
against all stored trial embeddings, and returns the top-K results with
clipped similarity scores.

The model, embedding matrix, and NCT ID list are each loaded once on first
use and cached at module level to avoid repeated disk and database reads.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

try:
    from app.db import EMBEDDING_MODEL_NAME, EMBEDDINGS_PATH, get_connection
except ImportError:
    from db import EMBEDDING_MODEL_NAME, EMBEDDINGS_PATH, get_connection  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Module-level cache
# ---------------------------------------------------------------------------

_MODEL: SentenceTransformer | None = None
_EMBEDDINGS: np.ndarray | None = None
_NCT_IDS: list[str] | None = None


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------


def get_model() -> SentenceTransformer:
    """Return the SentenceTransformer model, loading it once on first call."""
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _MODEL


def get_embeddings() -> np.ndarray:
    """
    Return the embedding matrix, loading it from disk once on first call.

    Raises FileNotFoundError if the .npy file does not exist.
    """
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        if not EMBEDDINGS_PATH.exists():
            raise FileNotFoundError(
                f"Embeddings file not found at {EMBEDDINGS_PATH}. "
                "Run build_embeddings.py first."
            )
        _EMBEDDINGS = np.load(EMBEDDINGS_PATH)
    return _EMBEDDINGS


def get_nct_ids() -> list[str]:
    """
    Return the ordered NCT ID list, loading it from SQLite once on first call.

    Ordered by embedding_row so that position i matches row i in the matrix.
    """
    global _NCT_IDS
    if _NCT_IDS is None:
        conn = get_connection()
        rows = conn.execute(
            "SELECT nct_id FROM embedding_index ORDER BY embedding_row"
        ).fetchall()
        conn.close()
        _NCT_IDS = [row["nct_id"] for row in rows]
    return _NCT_IDS


# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------


def cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity between a single query vector and a matrix.

    query_vec : shape (dim,)
    matrix    : shape (n, dim)
    Returns   : shape (n,) — one similarity score per row.
    """
    query_norm  = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    matrix_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10)
    return matrix_norm @ query_norm


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def retrieve(
    query: str,
    top_k: int = 100,
) -> list[dict[str, float | str]]:
    """
    Score all stored trial embeddings against the query and return the top-K.

    Returns an empty list if the query is blank or the embedding matrix is empty.
    Similarity scores are clipped to [0, 1].

    Each result dict contains:
      nct_id         — trial identifier string
      semantic_score — cosine similarity clipped to [0, 1]

    Raises FileNotFoundError if the embeddings file does not exist.
    Raises ValueError if the number of embedding rows and NCT IDs do not match.
    """
    if not query or not query.strip():
        return []

    matrix  = get_embeddings()
    nct_ids = get_nct_ids()

    if matrix.shape[0] == 0:
        return []

    if matrix.shape[0] != len(nct_ids):
        raise ValueError(
            f"Embedding matrix has {matrix.shape[0]} row(s) but "
            f"embedding_index has {len(nct_ids)} entry/entries. "
            "Re-run build_embeddings.py to rebuild both."
        )

    model     = get_model()
    query_vec = model.encode(query, convert_to_numpy=True)

    scores: np.ndarray = cosine_similarity(query_vec, matrix)
    scores = np.clip(scores, 0.0, 1.0)

    ranked = sorted(
        [
            {"nct_id": nct_id, "semantic_score": float(score)}
            for nct_id, score in zip(nct_ids, scores)
        ],
        key=lambda r: r["semantic_score"],
        reverse=True,
    )

    return ranked[:top_k]
