# IMPLEMENTATION_PLAN.md
# Biomedical Evidence Retrieval and Trial Matching Platform — V1

---

## 1. Purpose of This Implementation Plan

This document turns the approved V1 specification (`PROJECT_SPEC.md`) and the repository blueprint (`REPO_STRUCTURE.md`) into a concrete, step-by-step build plan for a solo developer.

The purpose is to:

- Establish a fixed build order that prevents architectural mistakes before they happen.
- Break the project into phases small enough to complete, run, and verify independently.
- Identify what must be decided or confirmed before any code is written.
- Define clear success criteria for each phase so you always know when it is safe to move on.
- Document the rules that keep the architecture clean throughout the build.
- Warn about the failure points that most commonly derail beginners on projects of this type.

This plan does not introduce any feature that is not already present in `PROJECT_SPEC.md`. Everything here is V1 scope only.

---

## 2. What Must Already Be Decided Before Coding

Before writing a single line of application code, confirm all of the following. If any item is unresolved, resolve it first. Ambiguity here becomes a bug later.

### 2.1 Environment

- Python version: **3.10 or later** is required. Confirm with `python --version`.
- Operating system: the project is designed for macOS, Linux, or Windows with WSL. All path examples use forward slashes.
- Virtual environment tool: use the standard `venv` module. Do not use Conda or Poetry unless you are already comfortable with them, as they add complexity without benefit at this scale.

### 2.2 Repository

- The repository root is named `biomedical-evidence-retrieval/`.
- All relative paths in this plan are relative to that root.
- The remote GitHub repository must be created before the first commit so that `.gitignore` is in place before any data files are generated.

### 2.3 Data source

- The data source is ClinicalTrials.gov REST API, version 2.
- The base URL is `https://clinicaltrials.gov/api/v2/studies`.
- The V1 corpus is scoped to Parkinson's disease trials.
- Target corpus size: 1,000–3,000 trials. This is intentional. Do not expand scope before V1 is complete.
- The download and parse steps are always kept in separate scripts. This decision is final for V1.

### 2.4 Database

- The database is a single SQLite file at `db/trials.db`.
- The schema follows exactly the four-table design in `PROJECT_SPEC.md` (Section 12): `trials`, `conditions`, `interventions`, `embedding_index`.
- All database access in the application goes through `app/db.py`. No other file opens the database directly.
- There is no ORM. Use the `sqlite3` standard library module only.

### 2.5 Retrieval

- BM25 library: `rank_bm25`. Tokenisation: lowercase, whitespace split. This tokenisation must be identical at index-build time and at query time.
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`. This is a general-purpose model, not biomedical-specific. That is acceptable for V1.
- Embeddings are stored as a numpy `.npy` file, not as database BLOBs. The `embedding_index` table maps NCT IDs to row positions in that file.
- Hybrid score formula: `alpha * bm25_norm + (1 - alpha) * semantic_norm`. Default `alpha = 0.5`.

### 2.6 Summary generator

- The summary is template-based only. It uses no model, no API, and no generated text.
- It draws exclusively from fields present in the `TrialRecord` dataclass.
- If a field is null or empty, the corresponding sentence is omitted. The string `"None"` must never appear in summary output.

### 2.7 API

- Three endpoints only: `GET /health`, `GET /search`, `GET /summary/{nct_id}`.
- Request and response shapes are defined as Pydantic models inside `routes.py` for V1.
- Indexes are loaded once at startup, not on every request.

### 2.8 Tests

- Tests always use in-memory fixtures from `conftest.py`.
- Tests never touch `db/trials.db`, `indexes/bm25_index.pkl`, or `indexes/embeddings.npy`.
- `pytest tests/` must be runnable before ingestion is complete, once the fixtures are written.

### 2.9 File paths

- Database path, BM25 index path, embeddings path, and the embedding model name are defined in one place only.
- For V1, define them as constants at the top of `app/db.py`, or in a dedicated `app/config.py` file. Either approach is acceptable. Choose one and use it everywhere.
- No hardcoded absolute paths anywhere in the codebase.

---

## 3. V1 Implementation Phases

The project is divided into eight sequential phases. Each phase has a single clear objective. No phase begins until the previous phase passes its validation checkpoint.

| Phase | Name | Primary files |
|---|---|---|
| 0 | Project skeleton | Root files, folder structure, `__init__.py` files |
| 1 | Database layer | `app/models.py`, `app/db.py` |
| 2 | Data pipeline | `scripts/download.py`, `scripts/ingest.py` |
| 3 | Retrieval indexes | `scripts/build_bm25_index.py`, `scripts/build_embeddings.py` |
| 4 | Retrieval pipeline | `app/retrieval/bm25_retriever.py`, `app/retrieval/semantic_retriever.py`, `app/retrieval/hybrid_scorer.py` |
| 5 | Summary generator | `app/summary/template_summary.py` |
| 6 | API | `app/api/main.py`, `app/api/routes.py` |
| 7 | UI | `ui/streamlit_app.py` |
| 8 | Tests | `tests/conftest.py`, all `test_*.py` files |
| 9 | Evaluation | `eval/queries.json`, `eval/evaluate.py` |
| 10 | Documentation | `README.md` (final version) |

> **Why this order matters.** Each phase depends on the one before it. The database layer must exist before data can be ingested. Indexes must be built before the retrieval pipeline can be tested. The retrieval pipeline must work before the API can be built on top of it. Building in any other order means testing components that have no data behind them, which produces misleading results.

---

## 4. Step-by-Step Build Order

The following sections describe each phase in detail. For every phase, the structure is: objective, files involved, expected output, and how to verify it worked.

---

### Phase 0 — Project Skeleton

**Objective:** Create the complete folder structure, configuration files, and empty package markers before writing any logic. This confirms your environment works and your repository is correctly set up.

**Files involved:**

```
biomedical-evidence-retrieval/
├── README.md                  (stub — one paragraph placeholder)
├── requirements.txt           (all dependencies, pinned versions)
├── .gitignore
├── data/
│   └── raw/
│       └── .gitkeep
├── db/
│   └── .gitkeep
├── indexes/
│   └── .gitkeep
├── scripts/                   (empty folder — scripts come later)
├── app/
│   ├── __init__.py
│   ├── retrieval/
│   │   └── __init__.py
│   ├── summary/
│   │   └── __init__.py
│   └── api/
│       └── __init__.py
├── ui/                        (empty folder)
├── eval/                      (empty folder)
└── tests/                     (empty folder)
```

**Steps:**

1. Create the GitHub repository and clone it locally.
2. Create all folders and `.gitkeep` files.
3. Write `.gitignore` (see `REPO_STRUCTURE.md` Section 8 for the complete list of patterns).
4. Write `requirements.txt` with all dependencies from `REPO_STRUCTURE.md` Section 6. Pin every version.
5. Create all `__init__.py` files (they are empty).
6. Write a stub `README.md` with just the project title.
7. Create and activate a virtual environment: `python -m venv .venv && source .venv/bin/activate`.
8. Run `pip install -r requirements.txt`.
9. Make the initial commit.

**Expected output:** A clean repository with the correct folder structure. `pip install -r requirements.txt` completes without errors. All packages import in a Python shell.

**Verification checkpoint:**

```bash
# Confirm virtual environment is active
which python   # should point to .venv/

# Confirm all packages install
pip install -r requirements.txt

# Confirm critical imports work
python -c "import fastapi, uvicorn, streamlit, rank_bm25, sentence_transformers, numpy, pytest, httpx"
# No output means success. Any ImportError must be fixed before moving on.

# Confirm folder structure
find . -type f -not -path './.git/*' -not -path './.venv/*'
# Review the list; confirm all expected files are present.

# Confirm .gitignore works
git status
# data/raw/, db/, indexes/ should NOT appear in the untracked files list.
```

---

### Phase 1 — Database Layer

**Objective:** Define the data structures and the database access layer that everything else depends on. No data is loaded yet.

**Files involved:**

- `app/models.py`
- `app/db.py`

**Steps:**

1. Write `app/models.py`:
   - Define `TrialRecord` as a Python dataclass with all fields from the `trials` table plus `conditions: list[str]` and `interventions: list[dict]`.
   - Define `SearchResult` as a Python dataclass that extends `TrialRecord` with `rank: int`, `bm25_score: float`, `semantic_score: float`, and `hybrid_score: float`.
   - Import only from the Python standard library (`dataclasses`, `typing`). No external imports.

2. Write `app/db.py`:
   - Define path constants for the database file (e.g., `DB_PATH = Path("db/trials.db")`).
   - Write `get_connection() -> sqlite3.Connection` that returns a connection with `row_factory = sqlite3.Row`.
   - Write `create_schema(conn)` that executes the `CREATE TABLE IF NOT EXISTS` statements for all four tables.
   - Write `get_trial_by_nct_id(nct_id: str) -> TrialRecord | None`.
   - Write `get_all_trials() -> list[TrialRecord]` (used by the index-building scripts).
   - Write `get_corpus_size() -> int` (used by the `/health` endpoint).
   - Each function takes a connection as input rather than opening one internally. This makes it easy to inject a test connection in fixtures.

**Expected output:** `app/models.py` and `app/db.py` exist and contain the complete definitions. A Python shell can import them without errors.

**Verification checkpoint:**

```bash
python -c "from app.models import TrialRecord, SearchResult; print('models OK')"
python -c "from app.db import get_connection, create_schema; print('db import OK')"

# Confirm schema creation works
python - <<'EOF'
import sqlite3
from app.db import create_schema
conn = sqlite3.connect(":memory:")
create_schema(conn)
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print([t[0] for t in tables])
# Expected: ['trials', 'conditions', 'interventions', 'embedding_index']
EOF
```

All four table names must appear. Any missing table means `create_schema` is incomplete.

---

### Phase 2 — Data Pipeline

**Objective:** Download the raw trial data from ClinicalTrials.gov and parse it into the SQLite database. This phase produces the corpus that all later phases depend on.

**Files involved:**

- `scripts/download.py`
- `scripts/ingest.py`

**Steps:**

1. Write `scripts/download.py`:
   - Set the target URL: `https://clinicaltrials.gov/api/v2/studies?query.cond=Parkinson+disease&pageSize=100&format=json`.
   - Use a `while True` loop that fetches a page, saves it as `data/raw/page_{n:03d}.json`, reads the `nextPageToken` from the response, and breaks when the token is absent.
   - Use `requests.get()` with a reasonable timeout (e.g., 30 seconds).
   - Print progress to the terminal as each page saves (e.g., `"Saved page_001.json — 100 records"`).
   - Do not parse records inside this script. Save raw JSON only.

2. Run `download.py` and confirm the files appear in `data/raw/`.

3. Write `scripts/ingest.py`:
   - Call `app/db.py`'s `create_schema` at the start to ensure tables exist.
   - Read every `data/raw/page_*.json` file using `glob` or `pathlib`.
   - For each trial record in each page, extract the fields defined in `PROJECT_SPEC.md` Section 12.
   - Build the `search_text` field by concatenating: title, brief summary, condition names, and intervention names — separated by spaces.
   - Insert into `trials` using `INSERT OR IGNORE INTO trials ... ON CONFLICT(nct_id) DO NOTHING` to ensure idempotency.
   - Insert conditions and interventions with the same idempotency approach.
   - Use `tqdm` to show a progress bar.
   - Print a final count: `"Ingested N trials into trials.db"`.

4. Run `ingest.py`. Run it a second time and confirm the row count does not change (idempotency check).

**Expected output:** `data/raw/` contains one JSON file per API page. `db/trials.db` contains the `trials`, `conditions`, and `interventions` tables populated with records. The `embedding_index` table exists but is empty (it is populated in Phase 3).

**Verification checkpoint:**

```bash
# Confirm raw files exist
ls data/raw/ | head -5
ls data/raw/ | wc -l   # should be > 1

# Confirm database is populated
python - <<'EOF'
import sqlite3
conn = sqlite3.connect("db/trials.db")
n_trials = conn.execute("SELECT COUNT(*) FROM trials").fetchone()[0]
n_conditions = conn.execute("SELECT COUNT(*) FROM conditions").fetchone()[0]
n_interventions = conn.execute("SELECT COUNT(*) FROM interventions").fetchone()[0]
print(f"Trials: {n_trials}, Conditions: {n_conditions}, Interventions: {n_interventions}")
# Trials should be 1,000–3,000. Conditions and Interventions should each be larger than n_trials.
EOF

# Confirm idempotency
python scripts/ingest.py   # run a second time
python - <<'EOF'
import sqlite3
conn = sqlite3.connect("db/trials.db")
print(conn.execute("SELECT COUNT(*) FROM trials").fetchone()[0])
# Count must be the same as the first run.
EOF

# Spot-check one record
python - <<'EOF'
import sqlite3
conn = sqlite3.connect("db/trials.db")
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT * FROM trials LIMIT 1").fetchone()
print(dict(row))
# Confirm nct_id, title, brief_summary, search_text are non-empty.
EOF
```

---

### Phase 3 — Retrieval Index Building

**Objective:** Build the BM25 index and the semantic embedding matrix from the ingested corpus. These are the offline artefacts that the retrieval pipeline loads at runtime.

**Files involved:**

- `scripts/build_bm25_index.py`
- `scripts/build_embeddings.py`

**Steps:**

1. Write `scripts/build_bm25_index.py`:
   - Read the `nct_id` and `search_text` columns from all rows in `trials`.
   - Store the `nct_id` list and the tokenised corpus in the same order.
   - Build a `BM25Okapi` index from the tokenised corpus.
   - Use `pickle.dump` to save a dictionary `{"nct_ids": [...], "index": bm25_object}` to `indexes/bm25_index.pkl`.
   - Print: `"BM25 index built for N trials. Saved to indexes/bm25_index.pkl"`.

2. Write `scripts/build_embeddings.py`:
   - Read `nct_id` and `search_text` from all rows in `trials` in a stable, consistent order (e.g., ordered by `nct_id`).
   - Load `SentenceTransformer("all-MiniLM-L6-v2")`.
   - Encode all `search_text` values using `model.encode(texts, show_progress_bar=True, batch_size=64)`.
   - Save the resulting matrix with `numpy.save("indexes/embeddings.npy", matrix)`.
   - Insert a row into `embedding_index` for each NCT ID: `(nct_id, row_index)`. Use `INSERT OR REPLACE` so this is re-runnable.
   - Print: `"Embeddings built. Shape: (N, 384). Saved to indexes/embeddings.npy"`.

3. Run both scripts. The embedding script is the slowest step in the project — expect 1–3 minutes for 3,000 trials.

**Expected output:** `indexes/bm25_index.pkl` and `indexes/embeddings.npy` exist. The `embedding_index` table in `trials.db` is populated with one row per trial.

**Verification checkpoint:**

```bash
# Confirm files exist and are non-empty
ls -lh indexes/

# Confirm BM25 index loads
python - <<'EOF'
import pickle
data = pickle.load(open("indexes/bm25_index.pkl", "rb"))
print(f"BM25 NCT IDs: {len(data['nct_ids'])}")
print(f"BM25 index type: {type(data['index'])}")
# len(nct_ids) must match the trial count from Phase 2.
EOF

# Confirm embeddings load
python - <<'EOF'
import numpy as np
emb = np.load("indexes/embeddings.npy")
print(f"Embeddings shape: {emb.shape}")
# Expected: (N_trials, 384). N_trials must match the trial count.
EOF

# Confirm embedding_index table is populated
python - <<'EOF'
import sqlite3
conn = sqlite3.connect("db/trials.db")
n = conn.execute("SELECT COUNT(*) FROM embedding_index").fetchone()[0]
print(f"embedding_index rows: {n}")
# Must match the trial count.
EOF
```

---

### Phase 4 — Retrieval Pipeline

**Objective:** Build the three retrieval modules that accept a query string and return ranked candidate lists. This is the core logic of the project.

**Files involved:**

- `app/retrieval/bm25_retriever.py`
- `app/retrieval/semantic_retriever.py`
- `app/retrieval/hybrid_scorer.py`

**Steps:**

1. Write `app/retrieval/bm25_retriever.py`:
   - On module load (or lazily on first call), load `indexes/bm25_index.pkl`.
   - Implement `retrieve(query: str, top_k: int = 100) -> list[dict]`.
   - Inside `retrieve`: tokenise the query (lowercase, whitespace split); call `bm25.get_scores(tokens)`; if all scores are zero, return `[]`; normalise scores by dividing by the maximum; return the top-K as `[{"nct_id": ..., "bm25_score": ...}, ...]` sorted descending.

2. Write `app/retrieval/semantic_retriever.py`:
   - On module load (or lazily on first call), load `indexes/embeddings.npy` and read the NCT ID order from `embedding_index`.
   - Load `SentenceTransformer("all-MiniLM-L6-v2")` once.
   - Implement `retrieve(query: str, top_k: int = 100) -> list[dict]`.
   - Inside `retrieve`: encode the query to a (1, 384) vector; compute cosine similarity against all embeddings using numpy (dot product of unit-normalised vectors); clip to [0, 1]; return the top-K as `[{"nct_id": ..., "semantic_score": ...}, ...]`.

3. Write `app/retrieval/hybrid_scorer.py`:
   - Implement `score(bm25_results: list[dict], semantic_results: list[dict], alpha: float = 0.5) -> list[dict]`.
   - Build a lookup dict for each input list keyed by `nct_id`.
   - Take the union of all NCT IDs from both lists.
   - For each NCT ID in the union, look up BM25 and semantic scores (defaulting to 0.0 if absent).
   - Compute `hybrid_score = alpha * bm25_score + (1 - alpha) * semantic_score`.
   - Return the list sorted by `hybrid_score` descending.
   - Each item in the list: `{"nct_id": ..., "bm25_score": ..., "semantic_score": ..., "hybrid_score": ...}`.

4. Test all three modules interactively in a Python shell before writing tests.

**Expected output:** All three modules import without errors. Interactive shell tests confirm plausible rankings for a test query like `"Parkinson disease gait wearable"`.

**Verification checkpoint:**

```bash
python - <<'EOF'
from app.retrieval.bm25_retriever import retrieve as bm25_retrieve
from app.retrieval.semantic_retriever import retrieve as semantic_retrieve
from app.retrieval.hybrid_scorer import score as hybrid_score

query = "Parkinson disease gait wearable sensor"
bm25_results = bm25_retrieve(query, top_k=20)
sem_results = semantic_retrieve(query, top_k=20)
hybrid_results = hybrid_score(bm25_results, sem_results, alpha=0.5)

print(f"BM25 top result: {bm25_results[0]}")
print(f"Semantic top result: {sem_results[0]}")
print(f"Hybrid top result: {hybrid_results[0]}")
print(f"Hybrid result count: {len(hybrid_results)}")

# Verify alpha=1.0 matches BM25 order
hybrid_bm25_only = hybrid_score(bm25_results, sem_results, alpha=1.0)
assert hybrid_bm25_only[0]["nct_id"] == bm25_results[0]["nct_id"], "alpha=1.0 must match BM25 first result"

# Verify alpha=0.0 matches semantic order
hybrid_sem_only = hybrid_score(bm25_results, sem_results, alpha=0.0)
assert hybrid_sem_only[0]["nct_id"] == sem_results[0]["nct_id"], "alpha=0.0 must match semantic first result"

# Verify no duplicate NCT IDs
nct_ids = [r["nct_id"] for r in hybrid_results]
assert len(nct_ids) == len(set(nct_ids)), "Duplicate NCT IDs found in hybrid results"

print("All checks passed.")
EOF
```

---

### Phase 5 — Summary Generator

**Objective:** Build the pure Python function that produces a grounded, template-based summary from a `TrialRecord`.

**Files involved:**

- `app/summary/template_summary.py`

**Steps:**

1. Write `app/summary/template_summary.py`:
   - Import `TrialRecord` from `app/models`.
   - Implement `generate_summary(trial: TrialRecord) -> str`.
   - Follow the template from `PROJECT_SPEC.md` Section 15 exactly.
   - For each field: if the field is `None`, an empty string, or an empty list, skip that sentence entirely.
   - For `brief_summary`: use the first sentence (split on `"."` , take index 0). If the result is shorter than 20 characters, use the full field.
   - For `eligibility_criteria`: use the first 200 characters. If truncated, append `"…"`.
   - For `conditions` and `interventions`: join list items into a comma-separated string before inserting.
   - Every inserted value must be followed immediately by the bracketed field label (e.g., `[Conditions]`).
   - The function has no side effects, makes no external calls, and returns a plain string.

2. Test the function interactively by fetching a real trial from the database and passing it to `generate_summary`.

**Expected output:** `template_summary.py` imports cleanly. A sample output string contains field citation labels, omits null fields, and contains no instance of the string `"None"`.

**Verification checkpoint:**

```bash
python - <<'EOF'
import sqlite3
from app.db import get_connection, get_trial_by_nct_id
from app.summary.template_summary import generate_summary

conn = get_connection()
# Get first trial from DB
nct_id = conn.execute("SELECT nct_id FROM trials LIMIT 1").fetchone()[0]
trial = get_trial_by_nct_id(nct_id, conn)
summary = generate_summary(trial)

print(summary)
print("---")

# Checks
assert "None" not in summary, "Summary must not contain the string 'None'"
assert len(summary) > 20, "Summary must be non-empty"
assert "[" in summary, "Summary must contain at least one field citation label"

print("Summary check passed.")
EOF
```

---

### Phase 6 — API

**Objective:** Expose the retrieval pipeline and summary generator as a FastAPI application with three documented endpoints.

**Files involved:**

- `app/api/main.py`
- `app/api/routes.py`

**Steps:**

1. Write `app/api/routes.py`:
   - Define Pydantic response models for each endpoint: `HealthResponse`, `SearchResult` (API version with all fields from `PROJECT_SPEC.md` Section 16), and `SummaryResponse`.
   - Implement `GET /health`: query `get_corpus_size()` and return `{"status": "ok", "corpus_size": N}`.
   - Implement `GET /search`: accept `q: str`, `top_n: int = 10`, `alpha: float = 0.5`. Validate `1 <= top_n <= 20` and `0.0 <= alpha <= 1.0`. Call BM25 and semantic retrievers, run the hybrid scorer, fetch full trial records from the database for the top-N results, and return the ranked list.
   - Implement `GET /summary/{nct_id}`: fetch the trial from the database. Return `HTTPException(404)` if not found. Call `generate_summary` and return the summary string and a list of fields used.

2. Write `app/api/main.py`:
   - Create the FastAPI app instance with a title and description.
   - Include the router from `routes.py`.
   - Use a `lifespan` context manager (preferred in modern FastAPI) or `@app.on_event("startup")` to pre-load the BM25 index and embedding matrix once. Store them in application state (`app.state`). Pass them into route handlers via dependency injection or a shared module-level object.

3. Start the server and test all three endpoints manually.

**Expected output:** `uvicorn app.api.main:app --reload` starts without errors. All three endpoints respond correctly when tested through the Swagger UI at `http://localhost:8000/docs`.

**Verification checkpoint:**

```bash
# Terminal 1 — start the server
uvicorn app.api.main:app --reload

# Terminal 2 — test each endpoint
curl -s http://localhost:8000/health | python -m json.tool
# Expected: {"status": "ok", "corpus_size": N}

curl -s "http://localhost:8000/search?q=Parkinson+gait&top_n=5&alpha=0.5" | python -m json.tool
# Expected: {"query": "...", "results": [...]} with 5 results.
# Each result must have: rank, nct_id, title, overall_status, phase, conditions,
# interventions, brief_summary, bm25_score, semantic_score, hybrid_score, url.

# Get a valid NCT ID from the previous response, then:
curl -s "http://localhost:8000/summary/NCT_ID_HERE" | python -m json.tool
# Expected: {"nct_id": "...", "summary": "...", "fields_used": [...]}
# summary must contain at least one "[" citation label.

curl -s "http://localhost:8000/summary/NCT_INVALID_ID"
# Expected: HTTP 404 response.

# Confirm Swagger UI loads
# Open http://localhost:8000/docs in a browser.
# All three endpoints must appear. Each must show its parameters and example responses.
```

---

### Phase 7 — UI

**Objective:** Build the single-page Streamlit front end that connects to the running FastAPI backend.

**Files involved:**

- `ui/streamlit_app.py`

**Steps:**

1. Write `ui/streamlit_app.py`:
   - Set the page title and a brief project description at the top.
   - Add a `st.text_input` for the query and a Search button.
   - Add a `st.slider` for alpha (0.0 to 1.0, default 0.5, labelled `"BM25 ↔ Semantic weight"`).
   - Add a `st.selectbox` for result count (options: 5, 10, 20; default 10).
   - On search: call `http://localhost:8000/search` using the `requests` library. Handle connection errors with `st.error(...)`.
   - Show a warning if the query is empty.
   - Show a message if no results are returned.
   - For each result, render a `st.expander` labelled with rank, NCT ID, and title. Inside the expander, show all result card fields from `PROJECT_SPEC.md` Section 17.
   - Inside each expander, add a `st.button("Show Grounded Summary")`. When clicked, call `/summary/{nct_id}` and render the summary text inside the expander.
   - Each result card must include a working ClinicalTrials.gov URL rendered as a clickable link.

2. Start Streamlit while the FastAPI server is already running.

**Expected output:** `streamlit run ui/streamlit_app.py` opens in the browser without errors. A test query returns result cards with all expected fields. The summary button works. The ClinicalTrials.gov link opens the correct page.

**Verification checkpoint:**

```
Manual test — in the browser at http://localhost:8501:

1. Enter the query "deep brain stimulation tremor" and click Search.
   - Confirm: result cards appear with rank, NCT ID, title, status, phase, conditions,
     interventions, scores, and a URL link.
   - Confirm: the URL link points to https://clinicaltrials.gov/study/<NCT_ID>.

2. Click "Show Grounded Summary" on the first result.
   - Confirm: a summary appears below the card content.
   - Confirm: the summary contains at least one "[" citation label.
   - Confirm: the summary does not contain the word "None".

3. Clear the query and click Search.
   - Confirm: a warning message appears (not a crash).

4. Stop the FastAPI server, then click Search.
   - Confirm: an error message appears (not a crash or blank page).

5. Change alpha to 1.0 and run the same query.
   - Confirm: results appear (different ranking is expected and acceptable).
```

---

### Phase 8 — Tests

**Objective:** Write the complete pytest suite. All tests must pass against the in-memory fixtures and must be independent of the real database and index files.

**Files involved:**

- `tests/conftest.py`
- `tests/test_bm25_retriever.py`
- `tests/test_semantic_retriever.py`
- `tests/test_hybrid_scorer.py`
- `tests/test_template_summary.py`
- `tests/test_api_routes.py`

**Steps:**

1. Write `tests/conftest.py` first:
   - Define `test_trials`: a list of 10 synthetic `TrialRecord` objects with controlled content. Include at least one trial with the word "Parkinson" in the title and at least one with null fields (`phase`, `eligibility_criteria`, etc.).
   - Define `test_bm25_index`: build a `BM25Okapi` index from the `search_text` fields of `test_trials`.
   - Define `test_embedding_matrix`: a numpy array of shape `(10, 384)` with deterministic values (e.g., `numpy.random.default_rng(42).random((10, 384))`).
   - Define `test_db`: an in-memory SQLite connection with the schema created and the `test_trials` inserted.
   - Define `test_client`: a FastAPI `TestClient` that uses the test database, test BM25 index, and test embedding matrix. This requires the API to accept injected dependencies, which is why `app/db.py` uses a function-based connection pattern.

2. Write `tests/test_bm25_retriever.py`, `tests/test_semantic_retriever.py`, and `tests/test_hybrid_scorer.py` according to the cases defined in `PROJECT_SPEC.md` Section 19.

3. Write `tests/test_template_summary.py` using the null-field trial from `test_trials`.

4. Write `tests/test_api_routes.py` using `test_client`. Do not start a real server. Use `TestClient` from `httpx`.

5. Run `pytest tests/` and fix all failures before proceeding to Phase 9.

**Expected output:** All tests pass. `pytest tests/` exits with zero failures and zero errors.

**Verification checkpoint:**

```bash
pytest tests/ -v
# Every test must show PASSED.
# No test must show ERROR or FAILED.

pytest tests/ --cov=app/retrieval --cov=app/summary --cov-report=term-missing
# Coverage for retrieval and summary modules should be close to 100%.
# Review any uncovered lines and decide if they need a test.
```

---

### Phase 9 — Evaluation

**Objective:** Measure retrieval quality against a small manually curated query set and record the results.

**Files involved:**

- `eval/queries.json`
- `eval/evaluate.py`

**Steps:**

1. Write `eval/queries.json`:
   - Write 10–15 query objects following the schema in `PROJECT_SPEC.md` Section 18.
   - For each query, open `https://clinicaltrials.gov/search?cond=...` and manually review the first page of results.
   - Assign 2–5 relevant NCT IDs per query.
   - Cover a range of topics within the Parkinson's disease corpus (e.g., motor symptoms, cognitive symptoms, wearables, drug interventions, surgical interventions).
   - Record the date of labelling in a comment or in the README.

2. Write `eval/evaluate.py`:
   - Accept `--alpha` as a required CLI argument.
   - Load `eval/queries.json`.
   - For each query, call `http://localhost:8000/search?q=...&top_n=10&alpha={alpha}` using `requests`.
   - Extract the top-5 NCT IDs from the response.
   - Compute Precision@5: fraction of top-5 results in the relevant set.
   - Compute Hit@5: 1 if any of the top-5 are in the relevant set, else 0.
   - Print a per-query table with: query ID, query text, Precision@5, Hit@5.
   - Print overall averages at the bottom.

3. Run the evaluation with three alpha values and record the results.

**Expected output:** `python eval/evaluate.py --alpha 0.5` prints a readable results table. The results are recorded in the README.

**Verification checkpoint:**

```bash
# Ensure the FastAPI server is running first.
python eval/evaluate.py --alpha 1.0   # BM25 only
python eval/evaluate.py --alpha 0.0   # Semantic only
python eval/evaluate.py --alpha 0.5   # Hybrid

# Confirm all three runs print a table with:
# - One row per query
# - Numeric Precision@5 and Hit@5 values
# - Overall average row at the bottom

# Note the results. The hybrid (alpha=0.5) should generally perform
# at least as well as either signal alone.
# Record all three result tables in README.md.
```

---

### Phase 10 — Documentation

**Objective:** Write the final `README.md` that allows a new reader to set up and run the project from scratch in under ten minutes.

**Files involved:**

- `README.md`

**Steps:**

1. Write the README with these sections, in this order:
   - What the project does (two to three sentences).
   - Architecture diagram (text art from `PROJECT_SPEC.md` Section 10 is sufficient).
   - Requirements (Python version, operating system).
   - Setup instructions: clone, create virtual environment, install dependencies.
   - Run order: `download.py` → `ingest.py` → `build_bm25_index.py` → `build_embeddings.py` → `uvicorn` → `streamlit run`.
   - Example queries to try in the UI.
   - Evaluation results table comparing `alpha=1.0`, `alpha=0.0`, and `alpha=0.5` for Precision@5 and Hit@5.
   - Design notes: why ClinicalTrials.gov was chosen, why the summary is template-based, what V2 improvements are planned.

2. Test the README by following its instructions on a fresh virtual environment (or ask someone else to try).

**Verification checkpoint:**

```
Starting from a fresh environment (no .venv, no db/, no indexes/):
Follow the README from the "Setup" section to the "Start the UI" section.
The project must be running in the browser before the ten-minute mark.
If any step fails or is unclear, fix the README before declaring V1 complete.
```

---

## 5. What Each Phase Should Produce

| Phase | Deliverable |
|---|---|
| 0 | Clean repository skeleton. Virtual environment installs without errors. |
| 1 | `models.py` and `db.py` import cleanly. In-memory schema creation works. |
| 2 | `data/raw/` contains raw JSON pages. `db/trials.db` contains 1,000–3,000 trial rows. Idempotency confirmed. |
| 3 | `indexes/bm25_index.pkl` loads with the correct number of NCT IDs. `indexes/embeddings.npy` has shape `(N, 384)`. |
| 4 | All three retrieval modules work in an interactive shell. `alpha=1.0` matches BM25 order. `alpha=0.0` matches semantic order. No duplicate NCT IDs. |
| 5 | `generate_summary` returns a non-empty string with citation labels. No `"None"` values in output. Null fields are omitted. |
| 6 | FastAPI starts. All three endpoints return correct responses. `/docs` loads and shows all endpoints. `404` works for unknown NCT IDs. |
| 7 | Streamlit app opens. Query returns result cards. Summary button works. URLs are valid. Error states are handled gracefully. |
| 8 | `pytest tests/` passes with zero failures. Tests are independent of real data files. |
| 9 | Evaluation script prints a results table. Precision@5 and Hit@5 are recorded for three alpha values. |
| 10 | README guides a new reader from clone to running UI in under ten minutes. |

---

## 6. Validation Checkpoint After Each Phase

This is a consolidated reference. Each phase has only one gate: either pass all checks and move on, or stay and fix before proceeding.

| Phase | Gate condition |
|---|---|
| 0 | `pip install -r requirements.txt` succeeds. All critical packages import. `git status` does not show `data/`, `db/`, or `indexes/`. |
| 1 | All four tables created from `create_schema` on an in-memory connection. `TrialRecord` and `SearchResult` instantiate without errors. |
| 2 | Trial count is 1,000–3,000. Second run of `ingest.py` produces the same count. At least one spot-checked record has a non-empty `search_text`. |
| 3 | BM25 index NCT ID count matches trial count. Embeddings shape second dimension is exactly 384. `embedding_index` row count matches trial count. |
| 4 | Interactive shell: BM25, semantic, and hybrid retrievers each return results for a test query. `alpha=1.0` and `alpha=0.0` assertions pass. No duplicate NCT IDs. |
| 5 | Sample summary contains `"["`. Does not contain `"None"`. Null fields absent from output. |
| 6 | All three `curl` tests pass. `/docs` shows all endpoints. `404` confirmed for unknown NCT ID. |
| 7 | All five manual browser checks pass. No unhandled exceptions in the terminal. |
| 8 | `pytest tests/ -v` shows all tests as PASSED. Zero FAILED, zero ERROR. |
| 9 | Evaluation script prints a complete table for three alpha values. |
| 10 | README followed on a fresh environment produces a running app. |

---

## 7. Suggested First Files to Create

Create these files in this exact order on day one. Each one is a prerequisite for the next.

1. `.gitignore` — protects the repository from unwanted commits before anything is generated.
2. `requirements.txt` — locks the dependency versions before the environment is created.
3. All `__init__.py` files — makes the package structure importable immediately.
4. `app/models.py` — defines the shared data types that every other module references.
5. `app/db.py` — establishes the database access pattern before any data exists.

Everything else depends on at least one of these five files being in place.

---

## 8. Dependencies Needed Before the First Coding Step

Complete all of the following before writing any application code.

### Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Verify the critical packages

```bash
python -c "
import rank_bm25
import sentence_transformers
import numpy
import fastapi
import uvicorn
import streamlit
import pytest
import httpx
print('All dependencies available.')
"
```

### Create the folder structure

```bash
mkdir -p data/raw db indexes scripts app/retrieval app/summary app/api ui eval tests
touch data/raw/.gitkeep db/.gitkeep indexes/.gitkeep
touch app/__init__.py app/retrieval/__init__.py app/summary/__init__.py app/api/__init__.py
```

### Confirm network access to ClinicalTrials.gov

```bash
python -c "
import requests
r = requests.get('https://clinicaltrials.gov/api/v2/studies?query.cond=Parkinson+disease&pageSize=1&format=json', timeout=10)
print(f'Status: {r.status_code}')
print(f'Keys: {list(r.json().keys())}')
"
# Expected: Status: 200 and Keys list containing 'studies' and 'nextPageToken'
```

If this call fails, do not proceed to Phase 2. Diagnose the network issue first.

---

## 9. Rules to Keep the Architecture Clean During Implementation

Follow these rules throughout the build. They are not optional. Deviating from them creates problems that are expensive to fix later.

**Rule 1 — Database access is centralised.**
Only `app/db.py` opens SQLite connections. No other file calls `sqlite3.connect()` directly. This is what makes the test fixtures work.

**Rule 2 — Indexes are loaded once.**
BM25 index and embedding matrix are loaded at API startup, stored in application state, and passed to route handlers. They are never loaded inside a route handler or inside a retrieval function that gets called per-request.

**Rule 3 — Scripts only run pipelines; modules only provide functions.**
Scripts in `scripts/` run end-to-end operations (download, ingest, build). Modules in `app/` expose functions that other code can call and test. No business logic lives in scripts. No side effects (file reads, database connections) happen at module import time in `app/`.

**Rule 4 — The summary generator has no side effects.**
`generate_summary` takes a `TrialRecord` and returns a string. It opens no files, makes no network calls, and accesses no globals. This makes it trivially testable.

**Rule 5 — Tests are isolated.**
Every test file imports only from `app/`. No test opens `db/trials.db`, reads from `indexes/`, or calls the real API over HTTP. All database and index access goes through fixtures defined in `conftest.py`.

**Rule 6 — Tokenisation is consistent.**
The tokenisation applied to the corpus at BM25 index build time (lowercase, whitespace split) must be identical to the tokenisation applied to queries at retrieval time. Any divergence silently degrades retrieval quality without producing an error.

**Rule 7 — Data files are never committed.**
`data/raw/`, `db/trials.db`, `indexes/bm25_index.pkl`, and `indexes/embeddings.npy` must never appear in the git history. Check `.gitignore` before every commit.

**Rule 8 — Null fields are handled explicitly.**
Every code path that reads a potentially null field from the database or from a `TrialRecord` must check for `None` and empty string before using the value. The string `"None"` must never appear in any output visible to the user.

**Rule 9 — Paths are defined once.**
All file paths (database, indexes, model name) are defined in one place (top of `app/db.py` or `app/config.py`) and imported everywhere. No path string is duplicated across files.

**Rule 10 — Stay within V1 scope.**
If a new idea arises during implementation, record it in a `V2_IDEAS.md` file and keep building V1. Do not add features, new endpoints, or new data sources. Scope creep on a solo portfolio project is the most common reason it never gets finished.

---

## 10. Common Failure Points During Implementation

These are the problems most likely to occur at each phase. Knowing them in advance prevents most of them.

**Phase 0 — Wrong Python version or missing dependencies**
`sentence-transformers` requires Python 3.8+. Some features used in the API require Python 3.10+. If `pip install` fails, check the Python version first. If a package has a dependency conflict, install packages one by one to identify the conflict.

**Phase 1 — Circular imports**
`app/models.py` must not import from `app/db.py`. `app/db.py` may import from `app/models.py`. If you accidentally import in the wrong direction, Python will raise an `ImportError` with a confusing message. Draw the import dependency graph before writing the files: `models` → no imports; `db` → `models`; `retrieval` → `db`, `models`; `summary` → `models`; `api` → `retrieval`, `summary`, `db`, `models`.

**Phase 2 — ClinicalTrials.gov API pagination error**
The `nextPageToken` key is absent on the last page, not present with a null value. Use `response.get("nextPageToken")` and break when the result is falsy. If you check for `== None` instead, the loop may behave unpredictably.

**Phase 2 — Missing or unexpected JSON fields during ingestion**
The ClinicalTrials.gov API returns deeply nested JSON. Field access like `record["protocolSection"]["descriptionModule"]["briefSummary"]` will raise a `KeyError` if any intermediate key is absent. Use `.get()` at every level: `record.get("protocolSection", {}).get("descriptionModule", {}).get("briefSummary")`.

**Phase 3 — Embedding script runs out of memory**
Encoding 3,000 trials at once may exhaust RAM on some machines. Use `batch_size=64` in `model.encode()`. If it still fails, lower the batch size to 32 or 16.

**Phase 3 — NCT ID order is inconsistent between runs**
If `get_all_trials()` in `app/db.py` does not specify `ORDER BY nct_id`, SQLite may return rows in different orders on different runs. The embedding row index stored in `embedding_index` will then point to the wrong trial. Always use `ORDER BY nct_id` when reading trials for index building.

**Phase 4 — BM25 returns zero scores for all queries**
This usually means the tokenisation at query time does not match the tokenisation at index build time. Confirm that both paths use lowercase whitespace split. A common mistake is applying additional preprocessing (e.g., punctuation removal or stemming) in one place but not the other.

**Phase 5 — "None" appears in the summary output**
This happens when a field is checked with `if field is not None` but the field is an empty string `""`, or when a conditions list is `[]` and `.join([])` produces an empty string that is then inserted. Use `if field` (which is falsy for both `None` and `""` and `[]`) rather than `if field is not None`.

**Phase 6 — Indexes not loaded before first request**
If the BM25 index and embeddings are loaded inside the route handler (rather than at startup), the first few requests will be slow and there will be no error — just silent latency. More seriously, if the loading fails inside the handler, the API will return a 500 error with no clear cause. Always load at startup and verify by checking `/health` immediately after startup.

**Phase 6 — Pydantic version mismatch**
FastAPI 0.100+ uses Pydantic v2. If you write Pydantic models using v1 syntax (e.g., `class Config: orm_mode = True` or `.dict()`), you will see deprecation warnings or validation errors. Use `model_config = ConfigDict(...)` and `.model_dump()` for all Pydantic v2 models.

**Phase 7 — Streamlit re-runs on every widget interaction**
Streamlit re-executes the entire script every time a widget is interacted with (including when the summary button is clicked). This means each click re-calls `/search`. Prevent this by storing search results in `st.session_state`. Only call `/search` when the search button is clicked, not on every re-run.

**Phase 8 — Tests fail because they use real files**
The most common test failure is a `FileNotFoundError` for `indexes/bm25_index.pkl` or `db/trials.db`. This means the retrieval module is loading its real path at import time. Fix this by making the index loading lazy (on first call) and passing in a test instance via a fixture or module-level override in `conftest.py`.

**Phase 9 — Evaluation script hangs**
If `eval/evaluate.py` is run before the FastAPI server is started, `requests.get()` will time out or raise a `ConnectionRefusedError`. Add a 5-second timeout to each request and a clear error message: `"Cannot connect to API. Is the server running?"`.

---

## 11. What Not to Build Yet

The following items are explicitly outside V1 scope. Do not start on any of these until all V1 phases are complete and validated.

| Item | Why it is deferred |
|---|---|
| PubMed integration or any second data source | Doubles the ingestion complexity before the pipeline is validated |
| LLM-based summarisation | Requires model hosting, adds latency, and is a qualitative change in output type |
| FAISS or other ANN index | Not needed for a corpus under 5,000 records |
| Cross-encoder re-ranking | A third retrieval stage should only be added after the two-stage pipeline is evaluated |
| User accounts or session state | Not required for a local portfolio demo |
| Pagination, filtering facets, or saved queries in the UI | The UI spec is complete without these |
| GitHub Actions CI | Requires the tests to be complete and stable first |
| Docker containerisation | Not needed for local-only operation |
| Live API polling | The static snapshot approach is explicit in the spec |
| `GET /trial/{nct_id}` detail endpoint | Explicitly listed as a V2 addition in `PROJECT_SPEC.md` |
| Multi-language support or PDF parsing | Not mentioned in V1 scope |
| Domain-adapted embeddings (e.g., BioLORD-2023) | A V2 model swap; the current model is adequate for V1 |
| `scripts/reset_db.py` | Useful but optional; re-running `ingest.py` is sufficient |
| `app/api/schemas.py` | Pydantic models can remain in `routes.py` for V1 |

---

## 12. Definition of Readiness for the First Code Generation Step

Before writing the first file in Phase 1, confirm every item below. This list is the go/no-go gate for starting the build.

### Environment confirmed

- [ ] Python 3.10 or later is installed and accessible as `python` or `python3`.
- [ ] A virtual environment has been created and is activated.
- [ ] `pip install -r requirements.txt` completes without errors on the first attempt, or all conflicts have been resolved.
- [ ] All critical packages import without errors in a Python shell (fastapi, uvicorn, streamlit, rank_bm25, sentence_transformers, numpy, pytest, httpx).

### Repository confirmed

- [ ] The GitHub repository exists, is cloned locally, and the initial commit has been pushed.
- [ ] `.gitignore` is in place and covers `data/raw/`, `db/`, `indexes/`, `__pycache__/`, and `.venv/`.
- [ ] All folders (`scripts/`, `app/`, `app/retrieval/`, `app/summary/`, `app/api/`, `ui/`, `eval/`, `tests/`, `data/raw/`, `db/`, `indexes/`) exist.
- [ ] `.gitkeep` files are present in `data/raw/`, `db/`, and `indexes/`.
- [ ] All `__init__.py` files exist in `app/`, `app/retrieval/`, `app/summary/`, and `app/api/`.

### Spec understood

- [ ] You can name the four database tables and describe the purpose of each.
- [ ] You can explain the difference between `bm25_retriever.py`, `semantic_retriever.py`, and `hybrid_scorer.py` in plain language.
- [ ] You know what `alpha = 1.0` and `alpha = 0.0` each mean for the hybrid score.
- [ ] You know that `generate_summary` must never produce the string `"None"` and must omit sentences for null fields.
- [ ] You know the three V1 API endpoint names, their parameters, and their expected response shapes.
- [ ] You know that tests use in-memory fixtures and never touch real database or index files.

### Data access confirmed

- [ ] A test `requests.get()` to the ClinicalTrials.gov API returns HTTP 200 with a `"studies"` key in the response body.

### Import dependency graph confirmed

- [ ] You have verified the correct import direction: `models` (no imports from app) ← `db` ← `retrieval` and `summary` ← `api`.
- [ ] You understand that no module-level side effects (file reads, network calls, database connections) should occur in `app/` modules at import time.

When every checkbox above is ticked, Phase 1 coding can begin.

---

*This document covers V1 only. It is aligned with `PROJECT_SPEC.md` and `REPO_STRUCTURE.md` as of the date this plan was written. Any change to the spec must be reflected here before coding continues.*
