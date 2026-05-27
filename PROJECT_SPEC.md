# Biomedical Evidence Retrieval Benchmark — Project Specification

Current version: **V3.6**. This document describes the full project scope through V3.6. It is the authoritative specification; README.md is the authoritative run reference.

---

## 1. Project Title

**Biomedical Evidence Retrieval Benchmark**

---

## 2. Overview

A local portfolio project demonstrating end-to-end biomedical information retrieval over a curated snapshot of ClinicalTrials.gov data. A user types a plain-text query and receives a ranked list of Parkinson disease clinical trials. Retrieval combines BM25 keyword matching with dense semantic embeddings into a configurable hybrid score. Retrieval quality is measured against a 46-query graded benchmark. Additional experiments cover biomedical embeddings, cross-encoder reranking, trial matching against synthetic patient cases, qualitative retrieval error analysis, and multi-method candidate pooling.

Stack: Python, FastAPI, Streamlit, SQLite, rank-bm25, sentence-transformers, pytest.

---

## 3. Why This Project Exists

This project extends a biomedical engineering portfolio into areas expected in data science and clinical informatics roles: biomedical NLP, structured document retrieval, relational database design, REST API development, retrieval evaluation methodology, and basic UI engineering. All experiments are conducted on a publicly available, domain-relevant dataset with a defined evaluation protocol.

---

## 4. Scope by Version

### V1 — Base Retrieval Application

- Download Parkinson disease trials from ClinicalTrials.gov (V2 API) into SQLite.
- BM25 retrieval (`rank-bm25`) over a concatenated `search_text` field.
- Semantic retrieval using `all-MiniLM-L6-v2` sentence embeddings stored as `.npy`.
- Hybrid score: `alpha * bm25_norm + (1 - alpha) * semantic_norm`, default `alpha=0.5`.
- FastAPI backend: `GET /health`, `GET /search`, `GET /summary/{nct_id}`.
- Streamlit single-page UI with query input and result cards.
- Template-based grounded summary — no LLMs, no generated text.
- pytest suite covering retrieval, scoring, summaries, and API routes.
- Evaluation: Precision@5 and Hit@5 over a small manually curated query set.

### V2.1 — Filtered Search

- Optional `overall_status`, `phase`, and `study_type` filters added to `/search`.
- Filters applied after hybrid scoring; omitting a filter returns all results.
- Streamlit UI updated with an expandable "Filters (optional)" section.

### V2.2 — Evaluation Benchmark

- Query set expanded to 14 queries across five categories.
- Metrics added: Recall@10 and MRR alongside Precision@5 and Hit@5.
- Relevance labels are candidate-based (derived from top-10 results at alpha=0.5). Not a clinically validated benchmark.
- Hybrid alpha=0.5 outperforms BM25-only and semantic-only across all metrics.

### V2.3 — Biomedical Embedding Comparison

- Added `BioLORD-2023` embedding workflow as a standalone retriever.
- Biomedical embeddings saved separately; existing `semantic_retriever.py` unchanged.
- `compare_retrievers.py` runs all four methods against `eval/queries.json`.
- Result: BioLORD did not improve retrieval on this candidate-based benchmark. Standard model (`all-MiniLM-L6-v2`) remains the default.

### V2.4 — Reranker Experiment

- Added `compare_reranker.py`: retrieves top-50 hybrid candidates per query, reranks with `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- API, UI, and existing retrievers unchanged.
- Result: reranking did not improve metrics on this benchmark. Not enabled as a default.

### V3.1 — Graded Retrieval Benchmark

- `eval/queries.json` updated to graded judgments: relevance 0 (not relevant), 1 (partially relevant), 2 (highly relevant).
- Query set expanded from 14 to 46 curated Parkinson-related queries.
- Metrics updated to include nDCG@10 alongside binary metrics.
- Hybrid alpha=0.5 achieves best results across all five metrics.

### V3.2 — Trial Matching Lite

- Added 12 synthetic Parkinson disease patient cases in `eval/patient_cases.json`.
- `trial_matching_lite.py` queries `/search` for each case at alpha=0.5, top_n=10, and writes ranked results to `eval/patient_case_matches_alpha_0_5.json`.
- Compatibility labels are rank-based only (ranks 1–3: `likely_relevant`; 4–10: `possibly_relevant`).
- **Not clinical decision support.** Does not perform eligibility reasoning. No medical suitability is implied.
- Tests cover input/output schema, rank-to-label mapping, and compatibility reason content.

### V3.3 — Retrieval Error Analysis

- Added `eval/error_analysis.json` with 15 qualitative error-analysis entries.
- `eval/summarize_error_analysis.py` prints counts by failure mode, method, and category.
- `tests/test_error_analysis.py` validates the structure and content of `error_analysis.json`.
- Failure modes identified: `synonym_mismatch`, `semantic_drift`, `lexical_overmatch`, `biomarker_vs_treatment_confusion`, `nonmotor_symptom_ambiguity`, `field_specificity_gap`, `candidate_pool_bias`.
- **Qualitative analysis only.** All observations are specific to this candidate-based benchmark corpus.

### V3.6 — Multi-Method Candidate Pooling

- `eval/collect_unlabeled_candidates.py` processes all 46 queries and pools top-10 candidates from four retrieval methods: BM25, standard semantic, hybrid (alpha=0.5), and biomedical semantic (if BioLORD indexes are available).
- Candidates are deduplicated by `nct_id`; each entry records which methods returned it in a `sources` field.
- Output is written to `eval/unlabeled_candidates_alpha_0_5.json`.
- For future manual relevance auditing only. Does not change existing relevance labels, benchmark scores, retrieval code, API, or UI.
- Benchmark remains candidate-based and not clinically validated.

---

## 5. Non-Goals (Current)

- PubMed or any second data source.
- LLM-based summarisation or generated text.
- User accounts, authentication, or session state.
- Live API polling or real-time data ingestion.
- Production deployment, containerisation, or cloud infrastructure.
- FAISS or approximate nearest-neighbour search.
- Multi-language support or PDF parsing.

---

## 6. Functional Requirements

| ID | Requirement |
|---|---|
| FR-01 | The system accepts a plain-text query and returns a ranked list of trials. |
| FR-02 | Each result includes: NCT ID, title, conditions, interventions, phase, status, brief summary excerpt, BM25 score, semantic score, hybrid score, and a ClinicalTrials.gov URL. |
| FR-03 | The hybrid score is a weighted linear combination of normalised BM25 and semantic scores. |
| FR-04 | The alpha weight is configurable per request, defaulting to 0.5. |
| FR-05 | Optional filters (`overall_status`, `phase`, `study_type`) narrow results after hybrid scoring. |
| FR-06 | The system generates a template-based grounded summary for any stored trial using only database fields. |
| FR-07 | The FastAPI application exposes three endpoints: `GET /health`, `GET /search`, `GET /summary/{nct_id}`. |
| FR-08 | The ingestion script is idempotent: re-running does not create duplicate records. |
| FR-09 | All retrieval and scoring logic is covered by pytest tests using in-memory fixtures. |
| FR-10 | Retrieval quality is measured with Precision@5, Hit@5, Recall@10, MRR, and nDCG@10 over a 46-query graded benchmark. |

---

## 7. Technical Architecture

```
┌──────────────────────────────────────────┐
│              Streamlit UI                │
│   query input · filters · result cards  │
└────────────────────┬─────────────────────┘
                     │ HTTP
┌────────────────────▼─────────────────────┐
│              FastAPI App                 │
│   /health   /search   /summary/{nct_id} │
└──────┬──────────────────────┬────────────┘
       │                      │
┌──────▼──────────┐  ┌────────▼────────────┐
│ Retrieval       │  │ Summary Generator    │
│ Pipeline        │  │ (template-based)     │
│                 │  └─────────────────────┘
│  BM25Retriever  │
│  SemanticRet.   │◄──── SQLite DB (trials.db)
│  HybridScorer   │◄──── embeddings.npy
└─────────────────┘
```

| Component | Technology |
|---|---|
| Database | SQLite via `sqlite3` standard library |
| BM25 | `rank-bm25` (`BM25Okapi`) |
| Semantic embeddings | `sentence-transformers/all-MiniLM-L6-v2`, stored as `.npy` |
| Biomedical embeddings | `FremyCompany/BioLORD-2023`, standalone (V2.3, not default) |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2`, standalone (V2.4, not default) |
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Tests | pytest with in-memory fixtures |

---

## 8. Evaluation Methodology

- **Query set:** 46 Parkinson disease retrieval queries with graded relevance judgments (0/1/2).
- **Relevance labels:** Candidate-based. Produced by reviewing top-10 results per query at alpha=0.5. **Not independently verified. Not clinically validated.**
- **Metrics:** Precision@5, Hit@5, Recall@10, MRR, nDCG@10.
- **Benchmark result (hybrid alpha=0.5):** Precision@5 = 0.9913, Hit@5 = 1.0000, Recall@10 = 0.9976, MRR = 1.0000, nDCG@10 = 0.9453.

---

## 9. Limitations

- Data is limited to Parkinson disease trials from ClinicalTrials.gov.
- The default embedding model (`all-MiniLM-L6-v2`) is general-purpose, not biomedical-specialised.
- Summaries are template-based; no language generation.
- Relevance labels are candidate-based and cover only 46 queries. They should not be used as a rigorous or clinical benchmark.
- Trial Matching Lite produces rank-based compatibility labels only. It is not clinical eligibility reasoning and implies no medical suitability.
- Error analysis is qualitative and specific to this corpus.
- No authentication, no cloud deployment, no persistent user sessions.

---

## 10. Future Conservative Improvements

- Manual relevance-label audit using the pooled candidate file (`eval/unlabeled_candidates_alpha_0_5.json`).
- Dependency pinning and reproducibility documentation.
- Portfolio and README polish.
