"""FastAPI application entry point for the Biomedical Evidence Retrieval and Trial Matching Platform."""

from fastapi import FastAPI

try:
    from app.api.routes import router
except ImportError:
    from routes import router  # type: ignore[no-redef]


app = FastAPI(
    title="Biomedical Evidence Retrieval and Trial Matching Platform",
    description=(
        "Search clinical trials using hybrid BM25 and semantic retrieval. "
        "Returns ranked results with template-based summaries."
    ),
    version="1.0.0",
)

app.include_router(router)
