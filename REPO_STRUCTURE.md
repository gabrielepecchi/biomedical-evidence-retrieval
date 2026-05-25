# Repository Structure — Biomedical Evidence Retrieval and Trial Matching Platform

This document translates the V1 specification into a concrete repository layout. It explains what every file does, in what order to build them, and what to watch out for. Use it as a build blueprint before writing any code.

---

## 1. Repository Root Overview

The repository is a single Python project with five clearly separated areas:

| Area | Folder | Purpose |
|---|---|---|
| Setup scripts | `scripts/` | Download raw data, parse it into SQLite, build retrieval indexes |
| Application logic | `app/` | Database helpers, retrieval pipeline, summary generator, FastAPI endpoints |
| User interface | `ui/` | Streamlit front end |
| Evaluation | `eval/` | Manually curated query set and evaluation script |
| Tests | `tests/` | pytest unit and integration tests |

Three additional top-level folders hold data artefacts that are never committed to Git:

- `data/raw/` — raw JSON pages downloaded from the ClinicalTrials.gov API
- `db/` — the SQLite database file
- `indexes/` — the serialised BM25 index and the numpy embeddings matrix

Everything else lives at the root: `README.md`, `requirements.txt`, and `.gitignore`.

---

## 2. Final V1 Folder Tree

```
biomedical-evidence-retrieval/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── data/
│   └── raw/                        # git-ignored
│       └── page_001.json           # example downloaded page
│       └── page_002.json
│       └── ...
│
├── db/
│   └── trials.db                   # git-ignored
│
├── indexes/
│   ├── bm25_index.pkl              # git-ignored
│   └── embeddings.npy              # git-ignored
│
├── scripts/
│   ├── download.py
│   ├── ingest.py
│   ├── build_bm25_index.py
│   └── build_embeddings.py
│
├── app/
│   ├── __init__.py
│   ├── db.py
│   ├── models.py
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── bm25_retriever.py
│   │   ├── semantic_retriever.py
│   │   └── hybrid_scorer.py
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
│   ├── queries.json
│   └── evaluate.py
│
└── tests/
    ├── conftest.py
    ├── test_bm25_retriever.py
    ├── test_semantic_retriever.py
    ├── test_hybrid_scorer.py
    ├── test_template_summary.py
    └── test_api_routes.py
```

**Total Python files to write for V1: 18**
Scripts: 4 · App: 10 (including `__init__.py` files) · UI: 1 · Eval: 1 · Tests: 6

---

## 3. File-by-File Purpose

### Root files

**`README.md`**
- Explains what the project does, how to install dependencies, and how to run each step in order.
- Includes the evaluation results table comparing BM25-only and hybrid retrieval.

**`requirements.txt`**
- Lists all Python dependencies with pinned versions.
- See Section 6 for the recommended dependency list by area.

**`.gitignore`**
- Excludes `data/`, `db/`, `indexes/`, `__pycache__/`, `.env`, and any IDE folders.
- Prevents large or auto-generated files from being committed.

---

### `scripts/`

These four scripts are run once, in order, to set up the project before starting the API.

**`scripts/download.py`**
- Calls the ClinicalTrials.gov REST API (`/api/v2/studies`) with a condition filter (e.g., Parkinson's disease).
- Paginates through all result pages using the `nextPageToken` field.
- Saves each page as a separate JSON file in `data/raw/`.

**`scripts/ingest.py`**
- Reads every JSON file in `data/raw/` and parses the trial records.
- Inserts trials, conditions, and interventions into the SQLite database (`db/trials.db`).
- Uses `INSERT OR IGNORE` so re-running the script does not create duplicates.

**`scripts/build_bm25_index.py`**
- Reads the `search_text` column from every row in the `trials` table.
- Tokenises each document (lowercase, whitespace split) and builds a `BM25Okapi` index.
- Serialises the index to `indexes/bm25_index.pkl` using `pickle`.

**`scripts/build_embeddings.py`**
- Reads the `search_text` column from the `trials` table.
- Encodes every document using `sentence-transformers/all-MiniLM-L6-v2`.
- Saves the embedding matrix as `indexes/embeddings.npy` and writes the NCT ID order to the `embedding_index` table in SQLite.

---

### `app/`

**`app/__init__.py`**
- Empty file. Makes `app` a Python package.

**`app/db.py`**
- Creates and returns a SQLite connection pointed at `db/trials.db`.
- Provides helper functions to fetch a single trial by NCT ID and to fetch conditions and interventions for a given NCT ID.
- All other modules import database access from here; nothing else opens the database directly.

**`app/models.py`**
- Defines two dataclasses used throughout the application:
  - `TrialRecord`: all fields stored for a single trial, plus its conditions and interventions lists.
  - `SearchResult`: a `TrialRecord` extended with `rank`, `bm25_score`, `semantic_score`, and `hybrid_score`.
- These are plain Python dataclasses, not ORM models.

---

### `app/retrieval/`

**`app/retrieval/__init__.py`**
- Empty file. Makes `retrieval` a Python package.

**`app/retrieval/bm25_retriever.py`**
- Loads `indexes/bm25_index.pkl` at import time (or on first call).
- Exposes a `retrieve(query: str, top_k: int) -> list[dict]` function that tokenises the query, scores all documents, and returns the top-K results as `{nct_id, bm25_score_norm}` dicts.
- Normalises scores to [0, 1]; returns an empty list if all scores are zero.

**`app/retrieval/semantic_retriever.py`**
- Loads `indexes/embeddings.npy` and the NCT ID order from `embedding_index` at import time.
- Encodes queries using `SentenceTransformer("all-MiniLM-L6-v2")`.
- Exposes a `retrieve(query: str, top_k: int) -> list[dict]` function that computes vectorised cosine similarity and returns the top-K results as `{nct_id, semantic_score_norm}` dicts.
- Clips scores to [0, 1].

**`app/retrieval/hybrid_scorer.py`**
- Accepts the BM25 candidate list, the semantic candidate list, and an `alpha` float.
- Merges the two lists on `nct_id`, assigning 0 for any missing signal.
- Computes `hybrid_score = alpha * bm25_norm + (1 - alpha) * semantic_norm` for each candidate.
- Returns a list of `{nct_id, bm25_score, semantic_score, hybrid_score}` dicts sorted by `hybrid_score` descending.

---

### `app/summary/`

**`app/summary/__init__.py`**
- Empty file. Makes `summary` a Python package.

**`app/summary/template_summary.py`**
- Exposes a single function: `generate_summary(trial: TrialRecord) -> str`.
- Fills a fixed template with values from the `TrialRecord` fields.
- Appends a bracketed field label after each value (e.g., `[Brief Summary]`) as an inline citation.
- Omits any sentence whose corresponding field is null or empty. Never invents content.
- Has no side effects and makes no external calls.

---

### `app/api/`

**`app/api/__init__.py`**
- Empty file. Makes `api` a Python package.

**`app/api/main.py`**
- Creates the FastAPI application instance.
- Registers the router from `routes.py`.
- Loads the BM25 index and embedding matrix on startup using FastAPI's `lifespan` or `startup` event so they are loaded once, not on every request.
- Entry point for Uvicorn: `uvicorn app.api.main:app`.

**`app/api/routes.py`**
- Defines the three V1 endpoints:
  - `GET /health` — returns `{"status": "ok", "corpus_size": N}`.
  - `GET /search` — accepts `q`, `top_n` (default 10, max 20), and `alpha` (default 0.5); runs the full retrieval pipeline and returns a ranked list of `SearchResult` objects.
  - `GET /summary/{nct_id}` — fetches the trial from the database, calls `generate_summary`, and returns the summary string and the list of fields used. Returns 404 if the NCT ID is not found.
- All request and response shapes are defined as Pydantic models, which enables automatic OpenAPI documentation at `/docs`.

---

### `ui/`

**`ui/streamlit_app.py`**
- Single-page Streamlit application.
- Renders a query input box, an alpha slider (0.0–1.0), and a result count selector.
- On search, calls the FastAPI `/search` endpoint via `requests` and renders one expandable card per result.
- Each card shows: rank, NCT ID, title, status, phase, conditions, interventions, score display, and a ClinicalTrials.gov link.
- Includes a "Show Grounded Summary" button per card that calls `/summary/{nct_id}` and renders the returned summary text inline.
- Shows appropriate messages for empty queries, no results, and API connection errors.

---

### `eval/`

**`eval/queries.json`**
- A JSON array of 10–15 manually curated query objects.
- Each object has three keys: `query_id` (string), `query` (string), and `relevant_nct_ids` (array of NCT ID strings).
- Relevance labels are assigned by manually reviewing ClinicalTrials.gov search results for each query.

**`eval/evaluate.py`**
- Loads `eval/queries.json`.
- For each query, calls the local FastAPI `/search` endpoint with `top_n=10`.
- Computes Precision@5 and Hit@5 per query and prints a summary table with overall averages.
- Accepts `--alpha` as a CLI argument to compare different weighting strategies.

---

### `tests/`

**`tests/conftest.py`**
- Provides shared fixtures for all tests:
  - An in-memory SQLite database pre-populated with 10 synthetic trial records.
  - A small BM25 index built from those records.
  - A small fixed numpy embedding matrix (e.g., 10 rows × 384 columns of deterministic values).
  - A FastAPI `TestClient` wired to the test database and test indexes.
- No test should read from `db/trials.db`, `indexes/bm25_index.pkl`, or `indexes/embeddings.npy`.

**`tests/test_bm25_retriever.py`**
- Tests that tokenisation produces lowercase tokens.
- Tests that an exact-match query ranks the matching document first.
- Tests that an empty query returns an empty list.

**`tests/test_semantic_retriever.py`**
- Tests that the embedding output has the correct shape (number of trials × 384).
- Tests that cosine similarity values are in [0, 1] after clipping.
- Tests that an identical query and document produce a similarity score near 1.0.

**`tests/test_hybrid_scorer.py`**
- Tests that `alpha=1.0` produces a ranking identical to BM25-only order.
- Tests that `alpha=0.0` produces a ranking identical to semantic-only order.
- Tests that the output contains no duplicate NCT IDs.

**`tests/test_template_summary.py`**
- Tests that a null or empty field is omitted from the output string.
- Tests that each field citation label (e.g., `[Brief Summary]`) appears in the output for a fully populated record.
- Tests that the function returns a non-empty string for a complete trial record.

**`tests/test_api_routes.py`**
- Tests that `GET /health` returns HTTP 200.
- Tests that `GET /search?q=parkinson` returns a non-empty ranked list with the expected JSON keys.
- Tests that `GET /summary/{valid_nct_id}` returns a summary string.
- Tests that `GET /summary/NCT_INVALID` returns HTTP 404.
- Tests that the `top_n` parameter is respected in the result count.

---

## 4. Required for V1 vs Optional Later

### Required for V1

Every file listed in the folder tree above is required for V1 unless explicitly marked optional below.

### Optional / Post-V1

| File or folder | Notes |
|---|---|
| `data/raw/*.json` files | Generated by `download.py`; never committed |
| `db/trials.db` | Generated by `ingest.py`; never committed |
| `indexes/bm25_index.pkl` | Generated by `build_bm25_index.py`; never committed |
| `indexes/embeddings.npy` | Generated by `build_embeddings.py`; never committed |
| `.github/workflows/` | CI/CD — not needed in V1 |
| `Dockerfile` | Containerisation — not needed in V1 |
| `app/api/schemas.py` | Pydantic models can live in `routes.py` for V1; extract to a separate file if it grows |
| `scripts/reset_db.py` | Convenience script to drop and recreate the database — useful but not required |

---

## 5. Recommended Implementation Order

Build the project in this order. Each step produces something you can immediately test or run before moving on.

**Step 1 — Project skeleton**
Create the folder structure, `requirements.txt`, `.gitignore`, and empty `__init__.py` files. Verify the virtual environment activates and all packages install without errors.

**Step 2 — Database layer**
Write `app/models.py` (dataclasses only) and `app/db.py` (connection + helper queries). Create the SQLite schema by hand or in `ingest.py`. Verify the database file is created and tables exist.

**Step 3 — Data ingestion**
Write `scripts/download.py`. Run it and confirm JSON pages appear in `data/raw/`. Write `scripts/ingest.py`. Run it and confirm rows appear in `db/trials.db`. Check for duplicate handling by running it twice.

**Step 4 — BM25 retrieval**
Write `scripts/build_bm25_index.py` and `app/retrieval/bm25_retriever.py`. Run the script, then test the retriever interactively in a Python shell with a simple query before writing the formal tests.

**Step 5 — Semantic retrieval**
Write `scripts/build_embeddings.py` and `app/retrieval/semantic_retriever.py`. Run the embedding script (this takes the longest of the four setup steps). Test the retriever in a Python shell.

**Step 6 — Hybrid scoring**
Write `app/retrieval/hybrid_scorer.py`. Test it in a Python shell by passing the outputs of the BM25 and semantic retrievers. Verify that `alpha=1.0` and `alpha=0.0` each reproduce the respective single-retriever ranking.

**Step 7 — Grounded summary**
Write `app/summary/template_summary.py`. Call it in a Python shell with a trial record fetched directly from the database. Confirm all null fields are omitted and all citation labels appear.

**Step 8 — FastAPI endpoints**
Write `app/api/routes.py` and `app/api/main.py`. Start the server with `uvicorn app.api.main:app --reload`. Test each endpoint manually in the browser at `http://localhost:8000/docs`.

**Step 9 — Streamlit UI**
Write `ui/streamlit_app.py`. Start the app with `streamlit run ui/streamlit_app.py`. Run a few queries and confirm result cards, scores, links, and summaries all appear correctly.

**Step 10 — Tests**
Write `tests/conftest.py` first, then write each test file. Run `pytest tests/` and fix failures before moving on. All tests must pass against the in-memory fixtures, not the real database.

**Step 11 — Evaluation**
Write `eval/queries.json` with 10–15 manually labelled queries. Write `eval/evaluate.py`. Run it with `alpha=1.0`, `alpha=0.0`, and `alpha=0.5` and record the results in `README.md`.

**Step 12 — README and final review**
Write the full `README.md` with setup instructions, example queries, and the evaluation results table. Run through the setup from scratch on a clean virtual environment to verify the instructions are correct.

---

## 6. Minimal Dependencies by Area

```
# Data download and parsing
requests

# Database
# sqlite3 is part of the Python standard library — no install needed

# BM25 retrieval
rank-bm25

# Semantic retrieval
sentence-transformers
numpy

# API
fastapi
uvicorn[standard]
pydantic

# UI
streamlit

# Tests
pytest
pytest-cov
httpx          # required by FastAPI TestClient

# Utilities
tqdm           # progress bars in ingestion and embedding scripts
```

Pin all versions in `requirements.txt` once the environment is confirmed working. A minimal `requirements.txt` entry looks like:

```
requests==2.32.3
rank-bm25==0.2.2
sentence-transformers==3.3.1
numpy==1.26.4
fastapi==0.115.6
uvicorn[standard]==0.32.1
pydantic==2.10.3
streamlit==1.41.1
pytest==8.3.4
pytest-cov==6.0.0
httpx==0.28.1
tqdm==4.67.1
```

> Verify and update version numbers against your actual environment before committing.

---

## 7. Startup and Run Flow

After setup, the full project runs in this order. Steps 1–4 are one-time setup. Steps 5–6 are the normal daily run.

```
# One-time setup

# 1. Install dependencies
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Download raw trial data (~1,000–3,000 trials)
python scripts/download.py

# 3. Parse and load into SQLite
python scripts/ingest.py

# 4. Build retrieval indexes
python scripts/build_bm25_index.py
python scripts/build_embeddings.py   # slowest step; ~1–3 min for 3,000 trials

# Normal run

# 5. Start the FastAPI backend (keep this terminal open)
uvicorn app.api.main:app --reload

# 6. Start the Streamlit UI in a second terminal
streamlit run ui/streamlit_app.py

# Verify
# FastAPI docs:  http://localhost:8000/docs
# Streamlit app: http://localhost:8501
```

**Run tests at any time:**
```
pytest tests/
pytest tests/ --cov=app/retrieval --cov=app/summary
```

**Run evaluation (requires the API to be running):**
```
python eval/evaluate.py --alpha 0.5
python eval/evaluate.py --alpha 1.0
```

---

## 8. Data Artefacts That Must Be Git-Ignored

These files are large, auto-generated, or locally specific. None of them should ever be committed.

Add the following to `.gitignore`:

```
# Downloaded raw data
data/raw/

# SQLite database
db/trials.db

# Retrieval indexes
indexes/bm25_index.pkl
indexes/embeddings.npy

# Python
__pycache__/
*.pyc
*.pyo
.venv/

# Environment variables (if used later)
.env

# IDE
.vscode/
.idea/
*.DS_Store
```

> Keep the empty `data/raw/`, `db/`, and `indexes/` folders tracked in Git by placing a `.gitkeep` file in each. This lets collaborators clone the repo and immediately see where the artefacts belong.

---

## 9. Common Beginner Mistakes to Avoid

**1. Running the scripts out of order.**
`ingest.py` requires the raw JSON files from `download.py`. The index scripts require a populated database. Always run: download → ingest → build indexes. If any step fails, fix it before continuing.

**2. Forgetting to separate download from parse.**
Do not call the ClinicalTrials.gov API inside `ingest.py`. Keep downloading and parsing in separate scripts. If parsing fails, you can re-run `ingest.py` without downloading again.

**3. Opening the database in multiple places.**
All database access must go through `app/db.py`. Do not open `sqlite3.connect("db/trials.db")` directly in retrieval or API files. This makes it easy to swap the test database in fixtures.

**4. Loading indexes on every request.**
Load `bm25_index.pkl` and `embeddings.npy` once at API startup, not inside the route handler functions. Loading a large numpy file on every request will make the API unacceptably slow.

**5. Letting tests touch the real database.**
Tests must use the in-memory fixtures from `conftest.py`. If a test imports and calls `app/db.py` directly with the real database path, it will fail in CI and produce non-deterministic results locally.

**6. Committing data artefacts.**
Double-check `.gitignore` before your first commit. A numpy embedding file for 3,000 trials is roughly 4–5 MB and will bloat the repository history permanently once committed.

**7. Not handling null fields in the summary generator.**
Many ClinicalTrials.gov records have null or empty `phase`, `eligibility_criteria`, or `sponsor_name` fields. If `template_summary.py` does not explicitly check for null before inserting a value, the summary will contain the string `"None"`, which is incorrect. Always check `if field` before including a sentence.

**8. Hardcoding file paths.**
Use `pathlib.Path` and define the paths to `db/trials.db`, `indexes/bm25_index.pkl`, and `indexes/embeddings.npy` in a single configuration location (a constant at the top of `app/db.py` or a small `app/config.py` file). Do not scatter path strings across files.

**9. Mixing Pydantic v1 and v2 syntax.**
`fastapi` 0.100+ uses Pydantic v2 by default. Use `model_config`, `model_fields`, and `model_dump()` rather than the Pydantic v1 equivalents (`class Config`, `__fields__`, `.dict()`). Check the FastAPI documentation for your installed version if you see validation errors.

**10. Starting the Streamlit app before the FastAPI server.**
The Streamlit app calls the FastAPI endpoints via `requests`. If the API is not running when Streamlit starts, every search will immediately show a connection error. Always start the API first.

---

## 10. Final Checklist Before Coding

Use this list to confirm the project is correctly set up before writing any application logic.

### Environment
- [ ] Python 3.10 or later is installed.
- [ ] A virtual environment is created and activated.
- [ ] `pip install -r requirements.txt` completes without errors.
- [ ] All required packages import correctly in a Python shell.

### Repository structure
- [ ] All folders exist: `data/raw/`, `db/`, `indexes/`, `scripts/`, `app/`, `ui/`, `eval/`, `tests/`.
- [ ] Each Python package folder (`app/`, `app/retrieval/`, `app/summary/`, `app/api/`) contains an `__init__.py` file.
- [ ] `.gitignore` excludes `data/raw/`, `db/trials.db`, `indexes/`, `__pycache__/`, and `.venv/`.
- [ ] A `.gitkeep` file is present in `data/raw/`, `db/`, and `indexes/` so the folders are tracked by Git.

### Configuration
- [ ] Database path, index paths, and the embedding model name are defined in one place and imported everywhere else.
- [ ] No hardcoded absolute paths exist anywhere in the codebase.

### Data
- [ ] `scripts/download.py` exists and the target API URL is set to the correct ClinicalTrials.gov v2 endpoint.
- [ ] The condition filter in `download.py` is set to the intended starting condition (e.g., Parkinson's disease).

### Understanding the pipeline
- [ ] You can explain, in plain language, the difference between what `bm25_retriever.py`, `semantic_retriever.py`, and `hybrid_scorer.py` each do.
- [ ] You understand that `all-MiniLM-L6-v2` is a general-purpose model and is not specialised for biomedical text. This is an acceptable baseline for V1.
- [ ] You understand that `template_summary.py` produces deterministic output from database fields only. It does not call any model or API.

### API scope
- [ ] You know the three V1 endpoints by name and expected behaviour: `GET /health`, `GET /search`, `GET /summary/{nct_id}`.
- [ ] You know that `GET /search` accepts `q`, `top_n`, and `alpha` as query parameters.
- [ ] You know that `GET /summary/{nct_id}` returns 404 if the NCT ID is not in the database.

### Tests
- [ ] You understand that all tests use in-memory fixtures from `conftest.py` and never touch the real database or index files.
- [ ] `pytest tests/` can be run before ingestion is complete, once the fixtures are written.

---

*This document covers V1 only. Refer to the Future V2 Extensions section of `PROJECT_SPEC.md` for planned additions.*
