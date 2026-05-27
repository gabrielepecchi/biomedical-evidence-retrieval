# Implementation History — Biomedical Evidence Retrieval Benchmark

Current version: **V3.6**. This document is a build log recording what was implemented in each version, the decisions made, and the current validation checklist. It is not a step-by-step build guide for V1 from scratch.

---

## V1 — Foundation

**Objective:** Local retrieval application over ClinicalTrials.gov Parkinson disease trials.

**Built:**
- `scripts/download.py` — paginated ClinicalTrials.gov API (V2), condition filter: Parkinson disease. Raw JSON saved to `data/raw/`.
- `scripts/ingest.py` — parses raw JSON, loads into SQLite (`db/trials.db`). Idempotent via `INSERT OR IGNORE`.
- `scripts/build_bm25_index.py` — builds `BM25Okapi` from `search_text`; saves to `indexes/bm25_index.pkl`.
- `scripts/build_embeddings.py` — encodes all trials with `all-MiniLM-L6-v2`; saves to `indexes/embeddings.npy`; writes NCT ID order to `embedding_index` table.
- `app/models.py` — `TrialRecord` and `SearchResult` dataclasses.
- `app/db.py` — all database access; single connection helper; fetch-by-NCT-ID helpers.
- `app/retrieval/bm25_retriever.py`, `semantic_retriever.py`, `hybrid_scorer.py` — retrieval pipeline. Hybrid: `alpha * bm25_norm + (1 - alpha) * semantic_norm`.
- `app/summary/template_summary.py` — template-based grounded summary; no LLM; null fields omitted.
- `app/api/main.py`, `routes.py` — FastAPI with `GET /health`, `GET /search`, `GET /summary/{nct_id}`; indexes loaded at startup.
- `ui/streamlit_app.py` — single-page search UI with alpha slider.
- `tests/` — pytest suite using in-memory fixtures; tests never touch real database or index files.
- `eval/queries.json`, `eval/evaluate.py` — initial query set; Precision@5 and Hit@5.

**Key decisions:**
- Embeddings stored as `.npy`, not database BLOBs; NCT ID order tracked in `embedding_index` table.
- All database access centralised in `app/db.py`.
- Tests isolated from real artefacts via `conftest.py` fixtures.
- Tokenisation (lowercase, whitespace split) identical at index-build time and query time.

---

## V2 — Retrieval and Evaluation Extensions

### V2.1 — Filtered Search

- Added optional `overall_status`, `phase`, `study_type` query parameters to `GET /search`. Applied after hybrid scoring; case-insensitive exact match.
- Streamlit UI updated with expandable "Filters (optional)" section.
- Study Type added to result cards.
- Filter tests mock the retrieval layer; no live indexes required.

### V2.2 — Evaluation Benchmark

- Query set expanded to 14 queries across five categories.
- Metrics added: Recall@10, MRR.
- Relevance labels: candidate-based (top-10 at alpha=0.5). Not clinically validated.
- Hybrid alpha=0.5 outperforms BM25-only and semantic-only across all four metrics.

### V2.3 — Biomedical Embedding Comparison

- `scripts/build_biomedical_embeddings.py` — builds BioLORD-2023 embeddings; saved separately from standard embeddings.
- `app/retrieval/biomedical_semantic_retriever.py` — standalone retriever; does not modify `semantic_retriever.py`.
- `eval/compare_retrievers.py` — runs all four methods against `eval/queries.json`; prints comparison table.
- Result: BioLORD underperformed across all metrics on this candidate-based benchmark. Standard model remains default.

### V2.4 — Reranker Experiment

- `eval/compare_reranker.py` — top-50 hybrid candidates per query reranked with `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- API, UI, and existing retrievers unchanged.
- Result: reranking did not improve metrics. Not enabled as a default.

---

## V3 — Benchmark, Trial Matching, Error Analysis, and Candidate Pooling

### V3.1 — Graded Retrieval Benchmark

- `eval/queries.json` updated: flat `relevant_nct_ids` replaced with `judgments` array (`nct_id`, `relevance` 0/1/2, optional `note`).
- `eval/evaluate.py` updated to read graded schema, compute binary metrics (relevance ≥ 1 threshold), and add nDCG@10.
- Query set expanded from 14 to 46 curated queries, all with graded judgments.
- Benchmark remains candidate-based and not clinically validated.

### V3.2 — Trial Matching Lite

- `eval/patient_cases.json` — 12 synthetic Parkinson disease patient cases covering diverse clinical scenarios.
- `eval/trial_matching_lite.py` — queries `/search` for each case at alpha=0.5, top_n=10; writes ranked results to `eval/patient_case_matches_alpha_0_5.json`.
- Compatibility labels are rank-based only: ranks 1–3 = `likely_relevant`, ranks 4–10 = `possibly_relevant`.
- **Not clinical decision support.** No eligibility reasoning. No medical suitability implied.
- `tests/test_trial_matching_lite.py` — schema validation for input/output, rank-to-label mapping, compatibility reason content.

### V3.3 — Retrieval Error Analysis

- `eval/error_analysis.json` — 15 qualitative entries covering cases where BM25-only or semantic-only underperformed hybrid.
- `eval/summarize_error_analysis.py` — prints counts by failure mode, method, and category.
- `tests/test_error_analysis.py` — validates structure and content of `error_analysis.json`.
- Failure modes identified: `synonym_mismatch`, `semantic_drift`, `lexical_overmatch`, `biomarker_vs_treatment_confusion`, `nonmotor_symptom_ambiguity`, `field_specificity_gap`, `candidate_pool_bias`.
- **Qualitative analysis only.** Specific to this candidate-based corpus. Not clinical validation.

### V3.6 — Multi-Method Candidate Pooling

- `eval/collect_unlabeled_candidates.py` — processes all 46 queries; pools top-10 candidates from BM25, standard semantic, hybrid (alpha=0.5), and biomedical semantic (if BioLORD indexes are available); deduplicates by `nct_id`; records source methods in a `sources` field; writes output to `eval/unlabeled_candidates_alpha_0_5.json`.
- For future manual relevance auditing only. Does not change existing relevance labels, benchmark scores, retrieval code, API, or UI.
- No new tests added; no existing tests modified.

---

## Current Validation Checklist

Run these checks to confirm V3.6 is fully operational:

```bash
# 1. Full test suite
pytest

# 2. Evaluation (requires FastAPI running)
python -m uvicorn app.api.main:app --reload   # in a separate terminal
python -m eval.evaluate --alpha 0.5
python -m eval.evaluate --alpha 1.0
python -m eval.evaluate --alpha 0.0

# 3. Trial Matching Lite (requires FastAPI running)
python -m eval.trial_matching_lite

# 4. Error analysis summary
python -m eval.summarize_error_analysis

# 5. Multi-method candidate pooling (requires indexes; BioLORD optional)
python -m eval.collect_unlabeled_candidates

# 6. Optional standalone comparisons (require indexes and FastAPI)
python -m eval.compare_retrievers
python -m eval.compare_reranker
```

Expected: all 8 test files pass; benchmark numbers match V3.1 results in README; `trial_matching_lite` produces a valid JSON output; `summarize_error_analysis` prints a clean summary table; `collect_unlabeled_candidates` produces `eval/unlabeled_candidates_alpha_0_5.json`.

> **Reproducibility:** all dependencies are pinned in `requirements.txt`. Generated artefacts (`data/raw/`, `db/trials.db`, `indexes/`) are git-ignored and must be rebuilt locally by running the scripts in Run Order.

---

## Future Conservative Improvements

- Manual relevance-label audit using the pooled candidate file (`eval/unlabeled_candidates_alpha_0_5.json`).
- Add a short "What this project demonstrates" section to README for portfolio readability.
