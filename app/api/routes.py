"""FastAPI route definitions for the V1 Biomedical Evidence Retrieval API."""

import re

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

try:
    from app.db import get_connection, get_corpus_size, get_trial_by_nct_id
    from app.retrieval.bm25_retriever import retrieve as bm25_retrieve
    from app.retrieval.semantic_retriever import retrieve as semantic_retrieve
    from app.retrieval.hybrid_scorer import score as hybrid_score
    from app.summary.template_summary import generate_summary
except ImportError:
    from db import get_connection, get_corpus_size, get_trial_by_nct_id  # type: ignore[no-redef]
    from bm25_retriever import retrieve as bm25_retrieve  # type: ignore[no-redef]
    from semantic_retriever import retrieve as semantic_retrieve  # type: ignore[no-redef]
    from hybrid_scorer import score as hybrid_score  # type: ignore[no-redef]
    from template_summary import generate_summary  # type: ignore[no-redef]


router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Response model for the /health endpoint."""

    status: str
    corpus_size: int


class InterventionItem(BaseModel):
    """A single intervention with type and name."""

    intervention_type: str | None
    intervention_name: str | None


class SearchResultItem(BaseModel):
    """A single ranked trial result returned by /search."""

    rank: int
    nct_id: str
    title: str
    overall_status: str | None
    phase: str | None
    conditions: list[str]
    interventions: list[InterventionItem]
    brief_summary: str | None
    bm25_score: float
    semantic_score: float
    hybrid_score: float
    url: str


class SearchResponse(BaseModel):
    """Response model for the /search endpoint."""

    query: str
    top_n: int
    alpha: float
    results: list[SearchResultItem]


class SummaryResponse(BaseModel):
    """Response model for the /summary/{nct_id} endpoint."""

    nct_id: str
    summary: str
    fields_used: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fields_used_from_summary(summary: str) -> list[str]:
    """
    Extract the ordered, deduplicated list of bracketed field labels from the summary.

    For example, '[Title]' and '[Conditions]' become ['Title', 'Conditions'].
    """
    labels = re.findall(r"\[([^\]]+)\]", summary)
    seen: set[str] = set()
    unique: list[str] = []
    for label in labels:
        if label not in seen:
            seen.add(label)
            unique.append(label)
    return unique


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return API status and the number of trials currently in the database."""
    conn = get_connection()
    size = get_corpus_size(conn)
    conn.close()
    return HealthResponse(status="ok", corpus_size=size)


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(default="", description="Search query"),
    top_n: int = Query(default=10, ge=1, le=20, description="Number of results to return (1–20)"),
    alpha: float = Query(default=0.5, ge=0.0, le=1.0, description="BM25 weight (0.0–1.0)"),
) -> SearchResponse:
    """
    Search for clinical trials using hybrid BM25 + semantic retrieval.

    Returns up to top_n results ranked by hybrid score.
    Returns an empty results list if the query is blank.
    """
    if not q or not q.strip():
        return SearchResponse(query=q, top_n=top_n, alpha=alpha, results=[])

    bm25_results = bm25_retrieve(q)
    semantic_results = semantic_retrieve(q)
    scored = hybrid_score(bm25_results, semantic_results, alpha=alpha)
    top_scored = scored[:top_n]

    conn = get_connection()
    results: list[SearchResultItem] = []

    for rank, item in enumerate(top_scored, start=1):
        nct_id = str(item["nct_id"])
        trial = get_trial_by_nct_id(conn, nct_id)
        if trial is None:
            continue

        results.append(
            SearchResultItem(
                rank=rank,
                nct_id=trial.nct_id,
                title=trial.title,
                overall_status=trial.overall_status,
                phase=trial.phase,
                conditions=trial.conditions,
                interventions=[
                    InterventionItem(
                        intervention_type=i["intervention_type"],
                        intervention_name=i["intervention_name"],
                    )
                    for i in trial.interventions
                ],
                brief_summary=trial.brief_summary,
                bm25_score=float(item["bm25_score"]),
                semantic_score=float(item["semantic_score"]),
                hybrid_score=float(item["hybrid_score"]),
                url=trial.url,
            )
        )

    conn.close()
    return SearchResponse(query=q, top_n=top_n, alpha=alpha, results=results)


@router.get("/summary/{nct_id}", response_model=SummaryResponse)
def summary(nct_id: str) -> SummaryResponse:
    """
    Return a template-based plain-text summary for a single trial.

    Raises HTTP 404 if the NCT ID is not found in the database.
    """
    conn = get_connection()
    trial = get_trial_by_nct_id(conn, nct_id)
    conn.close()

    if trial is None:
        raise HTTPException(status_code=404, detail="Trial not found")

    text = generate_summary(trial)
    fields = _fields_used_from_summary(text)

    return SummaryResponse(nct_id=nct_id, summary=text, fields_used=fields)
