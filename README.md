# Biomedical Evidence Retrieval Benchmark

[![CI](https://github.com/gabrielepecchi/biomedical-evidence-retrieval/actions/workflows/ci.yml/badge.svg)](https://github.com/gabrielepecchi/biomedical-evidence-retrieval/actions/workflows/ci.yml)

A portfolio project that benchmarks hybrid retrieval over clinical trial records, combining BM25 and semantic similarity, with a FastAPI backend and a Streamlit frontend.

---

## Overview

This platform indexes clinical trials from [ClinicalTrials.gov](https://clinicaltrials.gov) into a local SQLite database and provides keyword-based and semantic search over trial records. Results are ranked using a configurable hybrid score. A simple template-based summary is generated for each trial on request. Results can be narrowed using optional filters for status, phase, and study type. Retrieval quality is measured against a curated benchmark of 46 Parkinson-related queries with graded relevance judgments. Stack: Python, FastAPI, Streamlit, SQLite, rank-bm25, sentence-transformers, pytest.

---

## What This Project Demonstrates

- **Biomedical information retrieval** over a curated ClinicalTrials.gov snapshot, covering end-to-end pipeline design from raw API data to ranked search results.
- **Hybrid search** combining BM25 keyword matching and dense semantic embeddings into a configurable weighted score.
- **REST API and frontend engineering** via a FastAPI backend and a Streamlit UI with optional filters and an alpha slider.
- **SQLite data modelling and local indexing** including idempotent ingestion, a relational schema, and `.npy` embedding storage.
- **Retrieval evaluation methodology** measured with Precision@5, Recall@10, MRR, and nDCG@10 over a 46-query graded benchmark.
- **Error analysis and candidate-pool hardening** through qualitative failure-mode identification and multi-method candidate pooling for future label auditing.
- **Conservative clinical framing** throughout: results are not clinical decision support, relevance labels are candidate-based and not clinically validated, and all limitations are stated explicitly.

---

## V1 Scope

- **Data source:** ClinicalTrials.gov (V2 API, condition filter: Parkinson disease)
- **Storage:** SQLite
- **Retrieval:** BM25 (via `rank-bm25`) + semantic similarity (via `sentence-transformers`)
- **Scoring:** Hybrid score = `alpha * bm25_score + (1 - alpha) * semantic_score`
- **Backend:** FastAPI with three endpoints: `/health`, `/search`, `/summary/{nct_id}`
- **Frontend:** Streamlit single-page search UI
- **Summaries:** Template-based only — no LLMs, no external calls
- **Tests:** pytest unit tests for retrieval, scoring, summaries, and API routes
- **Evaluation:** Precision@5 and Hit@5 over a manually curated query set

---

## V2.1 — Filtered Search

- **`/search` optional filters:** `overall_status`, `phase`, and `study_type` query parameters added. Filters use case-insensitive exact matching and are applied after hybrid scoring. Omitting a filter returns all results as before.
- **Streamlit UI filters:** An expandable "Filters (optional)" section in the UI exposes all three filter fields as free-text inputs. Filters are passed to the API only when non-empty; leaving them blank preserves the existing search behaviour.
- **Study Type in results:** Each result card in the Streamlit UI now displays Study Type alongside Status and Phase.
- **Retrieval unchanged:** BM25 + semantic + hybrid scoring pipeline is identical to V1.
- **Tests:** All 25 tests pass. Filter tests mock the retrieval layer so they run without requiring built indexes.

---

## V2.2 — Evaluation Benchmark

- **Evaluation query set expanded** to 14 realistic Parkinson disease search queries covering five categories: `treatment`, `device`, `rehabilitation`, `symptoms`, and `gait_freezing`.
- **Metrics reported:** Precision@5, Hit@5, Recall@10, and MRR (Mean Reciprocal Rank).
- **Relevance labels** are candidate-based manual labels produced by reviewing the top-10 results per query at alpha=0.5. They are not a definitive clinical benchmark and should be treated accordingly.
- **Hybrid alpha=0.5 performed best overall** across all four metrics.

### Benchmark Results

| Method | Precision@5 | Hit@5 | Recall@10 | MRR |
|---|---:|---:|---:|---:|
| BM25-only alpha=1.0 | 0.757 | 0.929 | 0.765 | 0.817 |
| Semantic-only alpha=0.0 | 0.671 | 1.000 | 0.620 | 0.821 |
| Hybrid alpha=0.5 | 0.886 | 1.000 | 1.000 | 0.907 |

---

## V2.3 — Biomedical Embedding Comparison

- **Added a standalone biomedical embedding workflow** using `FremyCompany/BioLORD-2023`, a model trained on biomedical and clinical text. Embeddings are saved to `indexes/biomedical_embeddings.npy` with a JSON index at `indexes/biomedical_embedding_index.json`, separate from the general embeddings workflow.
- **Added `biomedical_semantic_retriever.py`** — a standalone retriever that loads the BioLORD embeddings and JSON index without touching the existing `semantic_retriever.py` or the database `embedding_index` table.
- **Added `compare_retrievers.py`** — a standalone script that runs all four methods directly against `eval/queries.json` and prints a benchmark table.
- **Biomedical embeddings did not improve retrieval** on this candidate-based benchmark. BioLORD scored lower than the general model across all metrics, likely because the relevance labels were derived from general-model candidates and the trial corpus is short search-text rather than full clinical prose.
- **The project keeps the existing standard semantic model** (`all-MiniLM-L6-v2`) as the default for now.

### Benchmark Results

| Method | Precision@5 | Hit@5 | Recall@10 | MRR |
|---|---:|---:|---:|---:|
| BM25-only | 0.757 | 0.929 | 0.765 | 0.817 |
| Semantic standard | 0.671 | 1.000 | 0.620 | 0.821 |
| Semantic biomedical | 0.243 | 0.643 | 0.241 | 0.465 |
| Hybrid standard | 0.886 | 1.000 | 1.000 | 0.907 |

---

## V2.4 — Optional Reranker Experiment

- **Added `eval/compare_reranker.py`** — a standalone script that retrieves the top 50 hybrid candidates per query and reranks them using a CrossEncoder model before evaluating metrics.
- **Reranker model:** `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- **Reranking scope:** only the top 50 results from the hybrid standard pipeline are passed to the reranker; retrieval itself is unchanged.
- **API, UI, and existing retrievers are unchanged.**
- **Reranking did not improve metrics** on this candidate-based benchmark. Scores dropped across all four metrics compared to hybrid standard, so the reranker is not enabled as a default feature.

### Benchmark Results

| Method | Precision@5 | Hit@5 | Recall@10 | MRR |
|---|---:|---:|---:|---:|
| Hybrid standard | 0.886 | 1.000 | 1.000 | 0.907 |
| Hybrid + reranker | 0.586 | 0.857 | 0.505 | 0.760 |

---

## V3.1 — Graded Retrieval Benchmark

- **`eval/queries.json` now uses graded judgments** instead of a flat list of `relevant_nct_ids`. Each query carries a `judgments` array of objects with `nct_id`, `relevance` (0, 1, or 2), and an optional `note`.
- **Relevance scale:** 2 = highly relevant, 1 = partially relevant, 0 = not relevant. NCT IDs absent from the judgments list are treated as relevance 0.
- **`eval/evaluate.py` updated** to read the new schema, compute binary metrics (Precision@5, Hit@5, Recall@10, MRR) using relevance ≥ 1 as the relevant threshold, and add **nDCG@10** using the full 0/1/2 graded values.
- **`eval/queries.json` now contains 46 curated Parkinson-related retrieval queries**, all with graded judgments, expanded from the original 14.
- **Hybrid alpha=0.5 performed best overall** across all five metrics. The benchmark remains candidate-based and should not be treated as a definitive clinical benchmark.

### Benchmark Results

| Method | Precision@5 | Hit@5 | Recall@10 | MRR | nDCG@10 |
|---|---:|---:|---:|---:|---:|
| BM25-only alpha=1.0 | 0.8391 | 0.9783 | 0.7709 | 0.9303 | 0.7556 |
| Semantic-only alpha=0.0 | 0.6652 | 1.0000 | 0.5656 | 0.8931 | 0.6268 |
| Hybrid alpha=0.5 | 0.9913 | 1.0000 | 0.9976 | 1.0000 | 0.9453 |

---

## V3.2 — Trial Matching Lite

- **Added `eval/patient_cases.json`** with 12 synthetic Parkinson disease patient cases covering diverse clinical scenarios: freezing of gait, motor fluctuations, dyskinesia, DBS consideration, focused ultrasound tremor, rehabilitation and falls, speech and swallowing, cognitive impairment, depression and anxiety, autonomic dysfunction, advanced therapy infusion, and wearable monitoring.
- **Added `eval/trial_matching_lite.py`** — a script that reads `patient_cases.json`, calls the existing `/search` API using each case's `matching_query` at alpha=0.5 with top_n=10, and writes ranked results to `eval/patient_case_matches_alpha_0_5.json`.
- **Added `eval/patient_case_matches_alpha_0_5.json`** — the output of Trial Matching Lite over all 12 synthetic cases.
- **Compatibility labels are rank-based only:** ranks 1–3 are labelled `likely_relevant`; ranks 4–10 are labelled `possibly_relevant`. These labels reflect retrieval rank and score only.
- **This is retrieval-based trial matching only.** It does not perform clinical eligibility reasoning and does not claim that a patient is eligible or suitable for any trial. No medical decision support is implied.
- **Tests expanded** to include Trial Matching Lite schema validation covering both input and output file structure, rank-to-label mapping, and compatibility reason content.

Run Trial Matching Lite with:

```bash
python -m eval.trial_matching_lite
```

The FastAPI backend must be running first.

---

## V3.3 — Retrieval Error Analysis

- **Added `eval/error_analysis.json`** with 15 representative qualitative error-analysis entries covering cases where BM25-only or semantic-only retrieval underperformed compared with hybrid retrieval at alpha=0.5.
- **Added `eval/summarize_error_analysis.py`** — a script that reads `error_analysis.json` and prints counts by failure mode, method, category, and the list of query IDs covered.
- **Added `tests/test_error_analysis.py`** — pytest tests that validate the structure and content of `error_analysis.json`.
- **Common failure modes identified:** `synonym_mismatch`, `semantic_drift`, `lexical_overmatch`, `biomarker_vs_treatment_confusion`, `nonmotor_symptom_ambiguity`, `field_specificity_gap`, and `candidate_pool_bias`.
- **This is qualitative retrieval error analysis only.** It does not constitute clinical validation and all observations are specific to this candidate-based benchmark corpus.

Summarize error analysis with:

```bash
python -m eval.summarize_error_analysis
```

---

## V3.6 — Multi-Method Candidate Pooling

- **`eval/collect_unlabeled_candidates.py` now collects candidates for all 46 queries** across multiple retrieval methods, rather than only for queries with empty judgments.
- **Pooling methods:** top-10 candidates from BM25, standard semantic, hybrid alpha=0.5, and biomedical semantic (BioLORD) if its indexes are available.
- **Candidates are deduplicated by `nct_id`** within each query. Each candidate records which method(s) produced it in a `sources` list alongside per-method scores.
- **Output written to `eval/unlabeled_candidates_alpha_0_5.json`** — a pooled candidate file for future manual relevance auditing only.
- **`eval/queries.json`, benchmark labels, benchmark scores, retrieval code, API, and UI are unchanged.**
- The benchmark remains candidate-based and not clinically validated.

Run multi-method candidate pooling with:

```bash
python -m eval.collect_unlabeled_candidates
```

---

## Project Structure

```
biomedical-evidence-retrieval/
├── data/raw/                  # Downloaded JSON pages (git-ignored)
├── db/                        # SQLite database (git-ignored)
├── indexes/                   # BM25 index and embeddings (git-ignored)
├── scripts/
│   ├── download.py            # Download raw trial data
│   ├── ingest.py              # Parse and load into SQLite
│   ├── build_bm25_index.py    # Build BM25 index
│   ├── build_embeddings.py    # Build sentence embeddings
│   └── build_biomedical_embeddings.py  # Build BioLORD embeddings (V2.3)
├── app/
│   ├── db.py                  # Database access layer
│   ├── models.py              # TrialRecord and SearchResult dataclasses
│   ├── retrieval/
│   │   ├── bm25_retriever.py
│   │   ├── semantic_retriever.py
│   │   ├── hybrid_scorer.py
│   │   └── biomedical_semantic_retriever.py  # BioLORD retriever (V2.3)
│   ├── summary/
│   │   └── template_summary.py
│   └── api/
│       ├── main.py            # FastAPI app entry point
│       └── routes.py          # API route definitions
├── ui/
│   └── streamlit_app.py       # Streamlit frontend
├── eval/
│   ├── queries.json           # Curated evaluation queries with graded judgments
│   ├── candidates_alpha_0_5.json  # Top-10 candidates used for relevance labelling
│   ├── evaluate.py            # Evaluation script
│   ├── compare_retrievers.py  # Retriever comparison script (V2.3)
│   ├── compare_reranker.py    # Reranker experiment script (V2.4)
│   ├── collect_unlabeled_candidates.py  # Multi-method candidate pooling script (V3.6)
│   ├── unlabeled_candidates_alpha_0_5.json  # Pooled candidates for future manual audit (V3.6)
│   ├── patient_cases.json           # Synthetic patient cases for Trial Matching Lite (V3.2)
│   ├── trial_matching_lite.py       # Trial Matching Lite retrieval script (V3.2)
│   ├── patient_case_matches_alpha_0_5.json  # Trial Matching Lite output (V3.2)
│   ├── error_analysis.json          # Qualitative retrieval error-analysis entries (V3.3)
│   └── summarize_error_analysis.py  # Error analysis summary script (V3.3)
├── tests/
│   ├── test_bm25_retriever.py
│   ├── test_semantic_retriever.py
│   ├── test_hybrid_scorer.py
│   ├── test_template_summary.py
│   ├── test_api_routes.py
│   ├── test_main.py
│   ├── test_trial_matching_lite.py
│   └── test_error_analysis.py
├── requirements.txt
└── README.md
```

---

## Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd biomedical-evidence-retrieval

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Run Order

Run these steps once to set up the data and indexes before starting the application.

```bash
# Step 1: Download raw trial data from ClinicalTrials.gov
python -m scripts.download

# Step 2: Parse and load trials into SQLite
python -m scripts.ingest

# Step 3: Build the BM25 index
python -m scripts.build_bm25_index

# Step 4: Build sentence embeddings (slowest step; runtime depends on dataset size and machine speed)
python -m scripts.build_embeddings

# Step 5: Start the FastAPI backend (keep this terminal open)
python -m uvicorn app.api.main:app --reload

# Step 6: Start the Streamlit frontend in a second terminal
python -m streamlit run ui/streamlit_app.py
```

- FastAPI interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Streamlit app: [http://localhost:8501](http://localhost:8501)

---

## Reproducibility Notes

- Tested with **Python 3.12**.
- All dependencies are pinned in `requirements.txt`. Install with `pip install -r requirements.txt`.
- Generated artefacts are not committed to the repository: `data/raw/`, `db/trials.db`, and `indexes/` are git-ignored and must be regenerated locally by running Steps 1–4 in Run Order above.
- To fully reproduce the local application, run `scripts/download`, `scripts/ingest`, `scripts/build_bm25_index`, and `scripts/build_embeddings` in order, then start the FastAPI backend and the Streamlit frontend.
- Biomedical embeddings (`indexes/biomedical_embeddings.npy`) are optional. They are only required for the BioLORD retriever comparison (`eval/compare_retrievers.py`) and candidate pooling with the biomedical semantic method (`eval/collect_unlabeled_candidates.py`). The main application and benchmark use only the standard embeddings.

---

## Screenshots

![Streamlit search interface with optional filters](assets/screenshots/search-home.png)
*Streamlit search interface with optional status, phase, and study type filters*

![Search results with hybrid scores](assets/screenshots/search-results.png)
*Search results with hybrid scores*

![Grounded summary view](assets/screenshots/grounded-summary.png)
*Grounded summary view*

![FastAPI interactive API docs](assets/screenshots/api-docs.png)
*FastAPI interactive API docs*

---

## Example Queries

These queries work well against the Parkinson disease trial dataset:

- `levodopa motor fluctuations Parkinson disease`
- `deep brain stimulation subthalamic nucleus`
- `dopamine agonist monotherapy early Parkinson`
- `alpha-synuclein immunotherapy clinical trial`
- `exercise rehabilitation gait freezing Parkinson`

Use the `alpha` slider in the Streamlit UI to adjust the balance between BM25 and semantic retrieval. `alpha=1.0` is BM25-only; `alpha=0.0` is semantic-only; `alpha=0.5` is balanced.

To narrow results, expand the "Filters (optional)" section and enter a value for Overall Status (e.g. `Recruiting`), Phase (e.g. `Phase 2`), or Study Type (e.g. `Interventional`). Leave any field blank to skip that filter.

---

## Evaluation

The evaluation script measures retrieval quality over 46 manually curated Parkinson-related queries defined in `eval/queries.json`. All 46 queries have graded judgments. Judgments use a graded relevance scale (0 = not relevant, 1 = partially relevant, 2 = highly relevant); NCT IDs absent from a query's judgments are treated as relevance 0.

```bash
# Evaluate with default alpha=0.5
python -m eval.evaluate --alpha 0.5

# Evaluate with BM25-only
python -m eval.evaluate --alpha 1.0

# Evaluate with semantic-only
python -m eval.evaluate --alpha 0.0
```

Metrics reported per query:

- **Precision@5** — fraction of the top 5 results that are relevant (relevance ≥ 1)
- **Hit@5** — whether at least one relevant result appears in the top 5
- **Recall@10** — fraction of all relevant results recovered in the top 10
- **MRR** — reciprocal rank of the first relevant result
- **nDCG@10** — normalised discounted cumulative gain at 10, using graded relevance values 0/1/2

> The API must be running before you run the evaluation script.

The test suite covers retrieval, scoring, summaries, API routes, graded benchmark and error analysis schema validation, and Trial Matching Lite schema validation. Run all tests with:

```bash
pytest
```

---

## Limitations

- Data is limited to trials matching a single condition filter (Parkinson disease) from ClinicalTrials.gov.
- The embedding model (`all-MiniLM-L6-v2`) is a general-purpose model, not specialised for biomedical text.
- Summaries are template-based and only include fields present in the database — no language generation.
- Evaluation relevance labels are manually assigned by reviewing retrieved candidates; the benchmark covers 46 candidate-based queries and should be expanded with broader, independently sourced judgments before being used as a rigorous benchmark.
- No authentication, no cloud deployment, no persistent user sessions.

---

## Future Improvements

- Conduct a manual relevance-label audit using the pooled candidate file to reduce candidate-pool bias.
