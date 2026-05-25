"""
Data models for the Biomedical Evidence Retrieval and Trial Matching Platform.

Defines the core dataclasses shared across the database layer, retrieval
pipeline, summary generator, and API.
"""

from dataclasses import dataclass, field


@dataclass
class TrialRecord:
    """
    A single clinical trial record as stored in the database.

    Optional fields map to NULLABLE columns in the trials table.
    conditions and interventions are populated from their related tables.
    """

    nct_id: str
    title: str
    url: str
    search_text: str

    brief_summary: str | None = None
    overall_status: str | None = None
    phase: str | None = None
    study_type: str | None = None
    sponsor_name: str | None = None
    start_date: str | None = None
    eligibility_criteria: str | None = None
    minimum_age: str | None = None
    maximum_age: str | None = None
    sex: str | None = None
    ingested_at: str | None = None

    conditions: list[str] = field(default_factory=list)
    interventions: list[dict[str, str | None]] = field(default_factory=list)


@dataclass
class SearchResult:
    """
    A trial result returned by the retrieval pipeline.

    Combines all TrialRecord fields with ranking and per-signal scores
    produced by the hybrid scorer.
    """

    nct_id: str
    title: str
    url: str
    search_text: str

    brief_summary: str | None = None
    overall_status: str | None = None
    phase: str | None = None
    study_type: str | None = None
    sponsor_name: str | None = None
    start_date: str | None = None
    eligibility_criteria: str | None = None
    minimum_age: str | None = None
    maximum_age: str | None = None
    sex: str | None = None
    ingested_at: str | None = None

    conditions: list[str] = field(default_factory=list)
    interventions: list[dict[str, str | None]] = field(default_factory=list)

    rank: int = 0
    bm25_score: float = 0.0
    semantic_score: float = 0.0
    hybrid_score: float = 0.0

    @classmethod
    def from_trial_record(
        cls,
        trial: TrialRecord,
        rank: int,
        bm25_score: float,
        semantic_score: float,
        hybrid_score: float,
    ) -> "SearchResult":
        """Build a SearchResult from a TrialRecord and retrieval scores."""
        return cls(
            nct_id=trial.nct_id,
            title=trial.title,
            url=trial.url,
            search_text=trial.search_text,
            brief_summary=trial.brief_summary,
            overall_status=trial.overall_status,
            phase=trial.phase,
            study_type=trial.study_type,
            sponsor_name=trial.sponsor_name,
            start_date=trial.start_date,
            eligibility_criteria=trial.eligibility_criteria,
            minimum_age=trial.minimum_age,
            maximum_age=trial.maximum_age,
            sex=trial.sex,
            ingested_at=trial.ingested_at,
            conditions=trial.conditions,
            interventions=trial.interventions,
            rank=rank,
            bm25_score=bm25_score,
            semantic_score=semantic_score,
            hybrid_score=hybrid_score,
        )