# Repository Structure — Biomedical Evidence Retrieval Benchmark

This document describes the current repository layout as of **V3.3**. It reflects the actual files in the project; README.md is the authoritative run reference.

---

## Repository Root Overview

| Area | Folder | Purpose |
|---|---|---|
| Setup scripts | `scripts/` | Download raw data, parse into SQLite, build retrieval indexes |
| Application logic | `app/` | Database helpers, retrieval pipeline, summary generator, FastAPI endpoints |
| User interface | `ui/` | Streamlit front end |
| Evaluation | `eval/` | Query set, evaluation scripts, experiment scripts, error analysis |
| Tests | `tests/` | pytest unit and integration tests |
| Assets | `assets/screenshots/` | UI screenshots referenced in README |

Three top-level folders hold data artefacts that are never committed to Git:

- `data/raw/` — raw JSON pages downloaded from ClinicalTrials.gov
- `db/` — the SQLite database file (`trials.db`)
- `indexes/` — serialised BM25 index, standard embeddings, and biomedical embeddings

---

## Current Folder Tree

```
biomedical-evidence-retrieval/
├── README.md
├── PROJECT_SPEC.md
├── IMPLEMENTATION_PLAN.md
├── REPO_STRUCTURE.md
├── requirements.txt
├── .gitignore
│
├── assets/
│   └── screenshots/
│       ├── search-home.png
│       ├── search-results.png
│       ├── grounded-summary.png
│       ├── api-docs.png
│       └── filtered-search.png
│
├── data/
│   └── raw/                            # git-ignored
│
├── db/
│   └── trials.db                       # git-ignored
│
├── indexes/                            # git-ignored
│   ├── bm25_index.pkl
│   ├── embeddings.npy
│   ├── biomedical_embeddings.npy       # V2.3 — BioLORD embeddings
│   └── biomedical_embedding_index.json # V2.3 — BioLORD NCT ID index
│
├── scripts/
│   ├── download.py
│   ├── ingest.py
│   ├── build_bm25_index.py
│   ├── build_embeddings.py
│   └── build_biomedical_embeddings.py  # V2.3
│
├── app/
│   ├── __init__.py
│   ├── db.py
│   ├── models.py
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── bm25_retriever.py
│   │   ├── semantic_retriever.py
│   │   ├── hybrid_scorer.py
│   │   └── biomedical_semantic_retriever.py  # V2.3 — standalone, not default
│   ├── summary/
│   │   ├── __init__.py
│   │   └── template_summary.py
│   └── api/
│       ├── __init__.py
│       ├── main.py
│       └── routes.py
│
├── ui/
│   └── streamlit_app.py
│
├── eval/
│   ├── queries.json                          # 46-query graded benchmark
│   ├── candidates_alpha_0_5.json             # top-10 candidates used for labelling
│   ├── unlabeled_candidates_alpha_0_5.json   # unlabeled candidates for future audit
│   ├── collect_unlabeled_candidates.py       # candidate collection script
│   ├── evaluate.py                           # main evaluation script
│   ├── compare_retrievers.py                 # V2.3 — multi-retriever comparison
│   ├── compare_reranker.py                   # V2.4 — reranker experiment
│   ├── patient_cases.json                    # V3.2 — 12 synthetic patient cases
│   ├── trial_matching_lite.py                # V3.2 — trial matching script
│   ├── patient_case_matches_alpha_0_5.json   # V3.2 — trial matching output
│   ├── error_analysis.json                   # V3.3 — 15 qualitative error entries
│   └── summarize_error_analysis.py           # V3.3 — error analysis summary script
│
└── tests/
    ├── conftest.py
    ├── test_bm25_retriever.py
    ├── test_semantic_retriever.py
    ├── test_hybrid_scorer.py
    ├── test_template_summary.py
    ├── test_api_routes.py
    ├── test_main.py
    ├── test_trial_matching_lite.py           # V3.2
    └── test_error_analysis.py               # V3.3
```

---

## File-by-File Purpose

### Root files

**`README.md`** — Authoritative run reference. Describes setup, run order, evaluation commands, benchmark results, and limitations through V3.3.

**`PROJECT_SPEC.md`** — Project specification covering all versions V1–V3.3: scope, functional requirements, architecture, evaluation methodology, and limitations.

**`IMPLEMENTATION_PLAN.md`** — Implementation history and build log through V3.3. Records what was built in each version and the current validation checklist.

**`REPO_STRUCTURE.md`** — This file. Current repository layout.

**`requirements.txt`** — Python dependencies.

**`.gitignore`** — Excludes `data/`, `db/`, `indexes/`, `__pycache__/`, `.venv/`.

---

### `scripts/`

Run once in order to set up data and indexes before starting the application.

| Script | Purpose |
|---|---|
| `download.py` | Paginates ClinicalTrials.gov API (condition: Parkinson disease); saves raw JSON to `data/raw/` |
| `ingest.py` | Parses raw JSON and loads trials into SQLite; idempotent via `INSERT OR IGNORE` |
| `build_bm25_index.py` | Builds BM25Okapi index from `search_text`; saves to `indexes/bm25_index.pkl` |
| `build_embeddings.py` | Encodes trials with `all-MiniLM-L6-v2`; saves to `indexes/embeddings.npy` |
| `build_biomedical_embeddings.py` | Encodes trials with BioLORD-2023; saves to separate index files (V2.3, optional) |

---

### `app/`

**`app/db.py`** — All database access. Returns SQLite connections and provides helper functions to fetch trials, conditions, and interventions. All other modules import from here.

**`app/models.py`** — `TrialRecord` and `SearchResult` dataclasses used throughout the application.

**`app/retrieval/bm25_retriever.py`** — Loads BM25 index; tokenises queries; returns top-K results with normalised scores.

**`app/retrieval/semantic_retriever.py`** — Loads standard embeddings; encodes queries; returns top-K results by cosine similarity.

**`app/retrieval/hybrid_scorer.py`** — Merges BM25 and semantic candidates; computes `hybrid_score = alpha * bm25_norm + (1 - alpha) * semantic_norm`.

**`app/retrieval/biomedical_semantic_retriever.py`** — Standalone retriever using BioLORD embeddings. Does not modify or replace `semantic_retriever.py` (V2.3, not default).

**`app/summary/template_summary.py`** — Generates grounded summaries from `TrialRecord` fields. No LLM. Omits sentences for null/empty fields. Never outputs the string `"None"`.

**`app/api/main.py`** — FastAPI application. Loads indexes at startup via lifespan event.

**`app/api/routes.py`** — Three endpoints: `GET /health`, `GET /search` (with `q`, `top_n`, `alpha`, and optional filter params), `GET /summary/{nct_id}`.

---

### `ui/`

**`ui/streamlit_app.py`** — Single-page search UI. Query input, alpha slider, result count selector, expandable filters, result cards with scores and summary button.

---

### `eval/`

| File | Purpose |
|---|---|
| `queries.json` | 46 graded queries (relevance 0/1/2 per NCT ID) |
| `candidates_alpha_0_5.json` | Top-10 candidates per query used for original relevance labelling |
| `unlabeled_candidates_alpha_0_5.json` | Unlabeled candidate pool for future manual audit |
| `collect_unlabeled_candidates.py` | Collects candidates from multiple retrieval methods for pooling |
| `evaluate.py` | Computes Precision@5, Hit@5, Recall@10, MRR, nDCG@10; accepts `--alpha` |
| `compare_retrievers.py` | Runs BM25, standard semantic, biomedical semantic, and hybrid; prints comparison table (V2.3) |
| `compare_reranker.py` | Retrieves top-50 hybrid candidates per query; reranks with CrossEncoder (V2.4) |
| `patient_cases.json` | 12 synthetic Parkinson disease patient cases (V3.2) |
| `trial_matching_lite.py` | Queries `/search` for each case; writes ranked results (V3.2) |
| `patient_case_matches_alpha_0_5.json` | Output of Trial Matching Lite (V3.2) |
| `error_analysis.json` | 15 qualitative error-analysis entries covering failure modes (V3.3) |
| `summarize_error_analysis.py` | Prints counts by failure mode, method, and category (V3.3) |

---

### `tests/`

All tests use in-memory fixtures from `conftest.py`. No test touches `db/trials.db`, `indexes/bm25_index.pkl`, or `indexes/embeddings.npy`.

| File | What is tested |
|---|---|
| `test_bm25_retriever.py` | Tokenisation, ranking, empty query handling |
| `test_semantic_retriever.py` | Embedding shape, score range, similarity correctness |
| `test_hybrid_scorer.py` | alpha=1.0 matches BM25 order; alpha=0.0 matches semantic order; no duplicate NCT IDs |
| `test_template_summary.py` | Null field omission, field label presence, non-empty output |
| `test_api_routes.py` | `/health` 200; `/search` returns results; `/summary` returns string; 404 for unknown NCT ID; `top_n` respected |
| `test_main.py` | Application startup and lifespan behaviour |
| `test_trial_matching_lite.py` | Input/output schema, rank-to-label mapping, compatibility reason content (V3.2) |
| `test_error_analysis.py` | Structure and content of `error_analysis.json` (V3.3) |

---

## Git-Ignored Artefacts

```
data/raw/
db/trials.db
indexes/bm25_index.pkl
indexes/embeddings.npy
indexes/biomedical_embeddings.npy
indexes/biomedical_embedding_index.json
__pycache__/
*.pyc
.venv/
.env
.vscode/
.idea/
*.DS_Store
```
