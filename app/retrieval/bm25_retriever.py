"""
BM25 retriever for the Biomedical Evidence Retrieval and Trial Matching Platform.

Loads the serialised BM25 index, scores all documents against a query,
and returns the top-K results with normalised scores.
"""

import pickle

try:
    from app.db import BM25_INDEX_PATH
except ImportError:
    from db import BM25_INDEX_PATH  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------


def tokenise(text: str) -> list[str]:
    """
    Convert a string into a list of tokens.

    Lowercase and whitespace-split only. Must be identical to the
    tokenisation used in build_bm25_index.py.
    """
    return text.lower().split()


# ---------------------------------------------------------------------------
# Index loading
# ---------------------------------------------------------------------------


def load_index() -> dict:
    """
    Load the BM25 index from disk and return the payload dict.

    The dict contains:
      nct_ids — ordered list of NCT ID strings
      index   — BM25Okapi object

    Raises FileNotFoundError if the index file does not exist.
    """
    if not BM25_INDEX_PATH.exists():
        raise FileNotFoundError(
            f"BM25 index not found at {BM25_INDEX_PATH}. "
            "Run build_bm25_index.py first."
        )
    return pickle.loads(BM25_INDEX_PATH.read_bytes())


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def retrieve(
    query: str,
    top_k: int = 100,
) -> list[dict[str, float | str]]:
    """
    Score all indexed trials against the query and return the top-K results.

    Returns an empty list if the query is blank or all BM25 scores are zero.
    Scores are normalised to [0, 1] by dividing by the maximum score.

    Each result dict contains:
      nct_id     — trial identifier string
      bm25_score — normalised score in [0, 1]
    """
    if not query or not query.strip():
        return []

    payload  = load_index()
    nct_ids: list[str]  = payload["nct_ids"]
    index                = payload["index"]

    tokens = tokenise(query)
    scores: list[float] = index.get_scores(tokens).tolist()

    max_score = max(scores)
    if max_score == 0.0:
        return []

    normalised = [score / max_score for score in scores]

    ranked = sorted(
        [
            {"nct_id": nct_id, "bm25_score": norm_score}
            for nct_id, norm_score in zip(nct_ids, normalised)
        ],
        key=lambda r: r["bm25_score"],
        reverse=True,
    )

    return ranked[:top_k]
