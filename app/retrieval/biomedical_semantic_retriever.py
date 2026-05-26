"""
Biomedical semantic retriever for V2.3.

Encodes a query with FremyCompany/BioLORD-2023, computes cosine similarity
against the biomedical embedding matrix, and returns the top-K results.

Uses indexes/biomedical_embeddings.npy and indexes/biomedical_embedding_index.json
produced by build_biomedical_embeddings.py. Does not touch semantic_retriever.py
or the general embeddings workflow.

Output format is identical to semantic_retriever.retrieve:
  list of dicts with 'nct_id' and 'semantic_score'.
"""

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BIOMEDICAL_MODEL_NAME: str = "FremyCompany/BioLORD-2023"
BIOMEDICAL_EMBEDDINGS_PATH: Path = Path("indexes") / "biomedical_embeddings.npy"
BIOMEDICAL_INDEX_PATH: Path = Path("indexes") / "biomedical_embedding_index.json"

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
    """Return the BioLORD model, loading it once on first call."""
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(BIOMEDICAL_MODEL_NAME)
    return _MODEL


def get_embeddings() -> np.ndarray:
    """Return the biomedical embedding matrix, loading it from disk once on first call.

    Raises FileNotFoundError if the .npy file does not exist.
    """
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        if not BIOMEDICAL_EMBEDDINGS_PATH.exists():
            raise FileNotFoundError(
                f"Biomedical embeddings not found at {BIOMEDICAL_EMBEDDINGS_PATH}. "
                "Run build_biomedical_embeddings.py first."
            )
        _EMBEDDINGS = np.load(BIOMEDICAL_EMBEDDINGS_PATH)
    return _EMBEDDINGS


def get_nct_ids() -> list[str]:
    """Return the ordered NCT ID list from the JSON index, loading it once on first call.

    Position i in the list corresponds to row i in the embedding matrix.
    Raises FileNotFoundError if the JSON index file does not exist.
    """
    global _NCT_IDS
    if _NCT_IDS is None:
        if not BIOMEDICAL_INDEX_PATH.exists():
            raise FileNotFoundError(
                f"Biomedical embedding index not found at {BIOMEDICAL_INDEX_PATH}. "
                "Run build_biomedical_embeddings.py first."
            )
        index: dict[str, int] = json.loads(BIOMEDICAL_INDEX_PATH.read_text(encoding="utf-8"))
        # Sort by row number to guarantee position i matches matrix row i.
        _NCT_IDS = [nct_id for nct_id, _ in sorted(index.items(), key=lambda x: x[1])]
    return _NCT_IDS


# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------


def cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between a query vector and a matrix.

    query_vec : shape (dim,)
    matrix    : shape (n, dim)
    Returns   : shape (n,)
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
    """Score all biomedical embeddings against the query and return the top-K.

    Returns an empty list if the query is blank or the embedding matrix is empty.
    Similarity scores are clipped to [0, 1].

    Each result dict contains:
      nct_id         — trial identifier string
      semantic_score — cosine similarity clipped to [0, 1]

    Raises FileNotFoundError if the embeddings or index file does not exist.
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
            f"index has {len(nct_ids)} entry/entries. "
            "Re-run build_biomedical_embeddings.py to rebuild both."
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
