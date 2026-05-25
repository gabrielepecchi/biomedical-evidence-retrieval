# Biomedical Evidence Retrieval and Trial Matching Platform

---

## 1. Project Title

**Biomedical Evidence Retrieval and Trial Matching Platform**

---

## 2. Overview

This is a local portfolio project that demonstrates end-to-end biomedical information retrieval using a curated snapshot of ClinicalTrials.gov data. A user types a plain-text biomedical query and receives a ranked list of relevant clinical trials. Retrieval combines BM25 keyword matching with dense semantic embeddings into a simple hybrid score. Each result includes structured trial metadata, a relevance score, and a direct link to the official trial page. A template-based grounded summary is generated from the stored trial fields, citing each field explicitly. The backend is a FastAPI application; the front end is a Streamlit app. V1 is scoped to a small, condition-focused trial corpus and is designed to run on a standard laptop with no external services.

---

## 3. Why This Project Exists

This project extends an existing biomedical engineering portfolio — which focuses on ML applied to biomedical signals, wearable IMU time-series, and Parkinson's disease analysis — into adjacent areas that are commonly expected in data science and clinical informatics roles: biomedical NLP, structured document retrieval, relational database design, REST API development, and basic UI engineering. Building a working retrieval pipeline with a defined evaluation protocol and clean API demonstrates these skills concretely, using a publicly available and domain-relevant dataset.

---

## 4. V1 Goals

- Download a condition-focused snapshot of ClinicalTrials.gov records and parse them into a structured SQLite database.
- Implement BM25 retrieval over concatenated trial text fields.
- Implement semantic retrieval using precomputed sentence embeddings and numpy cosine similarity.
- Combine both signals into a configurable linear hybrid score.
- Return ranked results with trial metadata, per-signal scores, and a ClinicalTrials.gov URL for each result.
- Generate a template-based grounded summary for any individual trial, citing only stored database fields.
- Expose retrieval and summary functionality through a minimal FastAPI application with auto-generated docs.
- Build a Streamlit UI that accepts a query and renders the ranked results and summaries.
- Evaluate the pipeline against a small manually curated query set using Precision@5 and Hit@5.
- Write a pytest test suite covering the retrieval and summary logic.
- Document the setup in a README that a new reader can follow in under ten minutes.

---

## 5. V1 Non-Goals

- PubMed or any data source other than ClinicalTrials.gov.
- LLM-based summarisation or any generative text.
- User accounts, authentication, or session state.
- Live API polling or real-time data ingestion.
- Production deployment, containerisation, or cloud infrastructure.
- Re-ranking models or any learned scoring component.
- FAISS or any approximate nearest-neighbour index.
- Multi-language support or full-text PDF parsing.
- GitHub Actions or automated CI/CD.
- Pagination, filtering facets, or saved queries in the UI.

---

## 6. Target User for the Demo

A biomedical engineering student, junior clinical data scientist, or technical recruiter who wants to search for relevant clinical trials using a plain-text query and see the results ranked with explanations. The demo must run locally from a clean Python environment after following the README setup steps.

---

## 7. Main User Flow

1. The user opens the Streamlit app in a browser.
2. The user types a free-text query (e.g., *"wearable gait sensor Parkinson disease"*).
3. The app sends the query to the FastAPI `/search` endpoint.
4. The backend runs BM25 and semantic retrieval, computes the hybrid score, and returns the top-N ranked trials.
5. The UI displays a ranked list of result cards. Each card shows: trial title, NCT ID, status, conditions, interventions, brief summary excerpt, hybrid score, and a link to the ClinicalTrials.gov trial page.
6. The user clicks "Show Summary" on any result card.
7. The app calls `/summary/{nct_id}`, which returns a template-based summary built from stored trial fields with inline field citations.
8. The summary renders beneath the result card.

---

## 8. Data Source Choice and Justification

**Source:** ClinicalTrials.gov — JSON export via the CTGOV REST API (v2)

**Base URL:** `https://clinicaltrials.gov/api/v2/studies`

**V1 ingestion strategy:** Use a condition-focused query to download a manageable subset of trial records in JSON format. For V1, target trials related to Parkinson's disease and movement disorders. This keeps the corpus small, thematically coherent, and easy to inspect and debug.

**Recommended starting query:**
```
https://clinicaltrials.gov/api/v2/studies?query.cond=Parkinson+disease&pageSize=100&format=json
```

Paginate through results using the `nextPageToken` field until all pages are consumed. Save the raw JSON pages to `data/raw/` before parsing. This separation of download and parse steps makes the pipeline easier to debug and re-run.

**Why ClinicalTrials.gov:**

| Factor | Detail |
|---|---|
| Public domain | No licence restrictions on use. |
| Structured schema | Consistent JSON fields across all records. |
| Domain relevance | Directly relevant to biomedical engineering and clinical research. |
| Manageable scale | A condition-filtered subset of 1,000–5,000 trials is large enough to demonstrate retrieval and small enough to index in seconds on a laptop. |
| No real-time dependency | A static snapshot is sufficient; no live API polling required after ingestion. |

**Starting corpus size for V1:** Aim for approximately 1,000–3,000 trials. This is enough to produce meaningful retrieval results, fast enough to re-index in under a minute, and small enough to inspect manually when debugging.

---

## 9. Functional Requirements

| ID | Requirement |
|---|---|
| FR-01 | The system shall accept a plain-text query string and return a ranked list of trials. |
| FR-02 | Each result shall include: NCT ID, title, conditions, interventions, phase, status, brief summary excerpt, BM25 score, semantic score, hybrid score, and a ClinicalTrials.gov URL. |
| FR-03 | The hybrid score shall be a weighted linear combination of the normalised BM25 score and the normalised semantic cosine similarity score. |
| FR-04 | The alpha weight shall be configurable per request, defaulting to 0.5. |
| FR-05 | The system shall generate a template-based grounded summary for any stored trial using only fields present in the database. |
| FR-06 | Each field used in the summary shall be cited inline using a bracketed field label (e.g., `[Brief Summary]`). |
| FR-07 | The FastAPI application shall expose three endpoints: `GET /health`, `GET /search`, and `GET /summary/{nct_id}`, all documented via automatic OpenAPI. |
| FR-08 | The ingestion script shall be idempotent: re-running it shall not create duplicate records. |
| FR-09 | All retrieval and scoring logic shall be covered by pytest tests. |

---

## 10. Technical Architecture

```
┌──────────────────────────────────────────┐
│              Streamlit UI                │
│   query input · result cards · summaries │
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

**Technology choices:**

| Component | Technology | Reason |
|---|---|---|
| Database | SQLite via `sqlite3` | File-based, zero dependencies, sufficient for a read-heavy local corpus |
| BM25 | `rank_bm25` | Simple, no server, easy to serialise |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) | Lightweight general-purpose model; fast, small, and sufficient for a local MVP baseline — not biomedical-specific (see V2 extensions) |
| Vector search | `numpy` cosine similarity | No infrastructure; perfectly adequate for a corpus under 5,000 records |
| API | FastAPI + Uvicorn | Auto-generated docs, straightforward to implement |
| UI | Streamlit | Fast to build, good for portfolio demos |
| Tests | pytest | Standard |

---

## 11. Suggested Folder Structure

```
biomedical-evidence-retrieval/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── data/
│   └── raw/                    # Raw JSON pages downloaded from ClinicalTrials.gov API
│
├── db/
│   └── trials.db               # SQLite database (git-ignored)
│
├── indexes/
│   ├── bm25_index.pkl          # Serialised BM25 index (git-ignored)
│   └── embeddings.npy          # Precomputed trial embeddings (git-ignored)
│
├── scripts/
│   ├── download.py             # Paginate ClinicalTrials.gov API → save raw JSON to data/raw/
│   ├── ingest.py               # Parse raw JSON → populate SQLite
│   ├── build_bm25_index.py     # Build BM25 corpus from DB → save bm25_index.pkl
│   └── build_embeddings.py     # Encode trials → save embeddings.npy
│
├── app/
│   ├── db.py                   # SQLite connection and query helpers
│   ├── models.py               # Dataclasses for TrialRecord and SearchResult
│   ├── retrieval/
│   │   ├── bm25_retriever.py
│   │   ├── semantic_retriever.py
│   │   └── hybrid_scorer.py
│   ├── summary/
│   │   └── template_summary.py
│   └── api/
│       ├── main.py             # FastAPI app, startup events
│       └── routes.py           # Endpoint definitions
│
├── ui/
│   └── streamlit_app.py
│
├── eval/
│   ├── queries.json            # Manually curated query–relevance pairs
│   └── evaluate.py             # Compute Precision@5, Hit@5
│
└── tests/
    ├── conftest.py
    ├── test_bm25_retriever.py
    ├── test_semantic_retriever.py
    ├── test_hybrid_scorer.py
    ├── test_template_summary.py
    └── test_api_routes.py
```

---

## 12. Data Model for SQLite

### Table: `trials`

| Column | Type | Description |
|---|---|---|
| `nct_id` | TEXT PRIMARY KEY | ClinicalTrials.gov identifier (e.g., NCT04123456) |
| `title` | TEXT | Official trial title |
| `brief_summary` | TEXT | Short plain-language summary |
| `overall_status` | TEXT | e.g., Recruiting, Completed, Terminated |
| `phase` | TEXT NULLABLE | e.g., Phase 1, Phase 2 |
| `study_type` | TEXT | e.g., Interventional, Observational |
| `sponsor_name` | TEXT NULLABLE | Lead sponsor |
| `start_date` | TEXT NULLABLE | ISO date string |
| `eligibility_criteria` | TEXT NULLABLE | Inclusion/exclusion text block |
| `minimum_age` | TEXT NULLABLE | e.g., 18 Years |
| `maximum_age` | TEXT NULLABLE | |
| `sex` | TEXT NULLABLE | All, Male, Female |
| `url` | TEXT | `https://clinicaltrials.gov/study/{nct_id}` |
| `search_text` | TEXT | Concatenated text used for BM25 indexing (title + brief_summary + conditions + interventions) |
| `ingested_at` | TEXT | ISO timestamp of ingestion |

### Table: `conditions`

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `nct_id` | TEXT — foreign key to `trials` | |
| `condition` | TEXT | Single condition name |

### Table: `interventions`

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | |
| `nct_id` | TEXT — foreign key to `trials` | |
| `intervention_type` | TEXT | e.g., Drug, Device, Behavioral |
| `intervention_name` | TEXT | |

### Table: `embedding_index`

| Column | Type | Description |
|---|---|---|
| `nct_id` | TEXT PRIMARY KEY — foreign key to `trials` | |
| `embedding_row` | INTEGER | Row index into `embeddings.npy` |

> **Note:** Embeddings are stored as a numpy `.npy` file on disk, not as BLOBs in SQLite. The `embedding_index` table maps each NCT ID to its row in that array. This keeps the database file small and keeps numpy operations simple.

---

## 13. Retrieval Pipeline Design

### Input

A plain-text query string (e.g., `"deep brain stimulation tremor Parkinson"`).

### Step 1 — BM25 Retrieval

1. At app startup, load the serialised BM25 index from `indexes/bm25_index.pkl`.
2. Tokenise the query the same way the corpus was tokenised at index build time (lowercase, whitespace split).
3. Score all documents with `BM25Okapi.get_scores(query_tokens)`.
4. Select the top-K candidates (default K = 100).
5. Normalise scores to [0, 1] by dividing by the maximum score in the candidate set. If all scores are zero, return an empty list.

### Step 2 — Semantic Retrieval

1. At app startup, load the embedding matrix from `indexes/embeddings.npy` (shape: `[N_trials, 384]`) and the NCT ID order from `embedding_index`.
2. Encode the query with the same `SentenceTransformer` model used at build time (`all-MiniLM-L6-v2`). This is a lightweight general-purpose encoder chosen for speed and ease of setup. It is not specialised for biomedical text; swapping in a domain-adapted model is a planned V2 improvement.
3. Compute cosine similarity between the query embedding and all trial embeddings using vectorised numpy.
4. Select the top-K candidates (default K = 100).
5. Clip similarities to [0, 1].

### Step 3 — Candidate Merging

Take the union of the two top-K sets. For any candidate present in only one set, assign a score of 0 for the missing signal.

### Step 4 — Hybrid Scoring

See Section 14.

### Step 5 — Database Enrichment

Fetch full trial records from SQLite for the top-N results (N ≤ 20), including associated conditions and interventions. Return a ranked list of `SearchResult` objects.

---

## 14. Hybrid Scoring Approach

```
hybrid_score = alpha * bm25_norm + (1 - alpha) * semantic_norm
```

**Default:** `alpha = 0.5`

Alpha is exposed as an optional query parameter in `/search` so different weighting strategies can be compared during evaluation without changing code.

**Why this works:** BM25 rewards exact keyword matches, which matters for drug names, NCT IDs, and precise medical terms. Semantic scoring rewards conceptual similarity, which matters for paraphrased queries and synonym variation. The linear combination captures both without requiring a trained model.

**V1 limitation:** Alpha is fixed per request and is not learned from feedback.

---

## 15. Grounded Summary Approach

The summary generator is a pure Python function. It takes a `TrialRecord` object and returns a formatted string. There are no API calls, no models, and no generated text.

### Template

```
{title} [Title]

This {study_type} trial investigates {conditions} [Conditions].
The primary intervention is {interventions} [Interventions].
Status: {overall_status} [Status]. Phase: {phase} [Phase].

{brief_summary_first_sentence} [Brief Summary]

Eligibility: {eligibility_excerpt} [Eligibility Criteria]

Sponsor: {sponsor_name} [Sponsor]. Start date: {start_date} [Start Date].
```

### Rules

1. Each data value is followed by a bracketed label naming the source field (e.g., `[Brief Summary]`). This is the citation.
2. If a field is null or empty, that sentence is omitted entirely. The summary never fills in missing data.
3. `brief_summary_first_sentence` is the first sentence of `brief_summary`, split on the first full stop. If the result is shorter than 20 characters, the full `brief_summary` is used instead.
4. `eligibility_excerpt` is the first 200 characters of `eligibility_criteria`, followed by `"…"` if truncated.
5. The function signature is `generate_summary(trial: TrialRecord) -> str`. It has no side effects.

---

## 16. FastAPI Endpoints for V1

### `GET /search`

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `q` | str | required | Plain-text query |
| `top_n` | int | 10 | Max 20 |
| `alpha` | float | 0.5 | BM25 weight; must be in [0.0, 1.0] |

**Response `200 OK`:**
```json
{
  "query": "wearable gait monitoring Parkinson",
  "results": [
    {
      "rank": 1,
      "nct_id": "NCT04123456",
      "title": "...",
      "overall_status": "Completed",
      "phase": "Phase 2",
      "conditions": ["Parkinson Disease"],
      "interventions": [{"type": "Device", "name": "IMU wearable sensor"}],
      "brief_summary": "...",
      "bm25_score": 0.82,
      "semantic_score": 0.74,
      "hybrid_score": 0.78,
      "url": "https://clinicaltrials.gov/study/NCT04123456"
    }
  ]
}
```

---

### `GET /summary/{nct_id}`

Returns the template-based grounded summary for a single trial.

**Response `200 OK`:**
```json
{
  "nct_id": "NCT04123456",
  "summary": "...",
  "fields_used": ["title", "conditions", "interventions", "overall_status", "phase", "brief_summary", "eligibility_criteria", "sponsor_name", "start_date"]
}
```

**`404 Not Found`** if the NCT ID is not in the database.

---

### `GET /health`

Returns `{"status": "ok", "corpus_size": N}`. Useful for verifying the app started correctly.

---

All three endpoints are documented automatically at `/docs` (Swagger UI) and `/redoc`.

---

## 17. Streamlit UI Scope for V1

The UI is a single page. It does not need to be polished — it needs to be functional and readable.

| Component | Description |
|---|---|
| Header | Project title and a one-line description |
| Query input | `st.text_input` for the query and a Search button |
| Alpha slider | `st.slider` from 0.0 to 1.0, default 0.5, labelled "BM25 ↔ Semantic weight" |
| Result count | `st.selectbox` with options 5, 10, 20 |
| Results list | One `st.expander` per result, labelled with rank, NCT ID, and title |
| Result card | Status, phase, conditions, interventions, brief summary excerpt, score display, and a ClinicalTrials.gov link |
| Summary panel | "Show Grounded Summary" button inside each expander; renders the template summary with field labels |
| Status messages | Warning for empty query; message for no results; error for API failure |

---

## 18. Evaluation Plan

### Goal

Verify that the hybrid retrieval pipeline returns relevant trials in the top-5 positions for a small set of representative queries.

### Query Set

Manually write **10–15 test queries** covering the ingested trial corpus. For a Parkinson's disease corpus, example queries include:

- `"wearable gait sensor Parkinson disease"`
- `"deep brain stimulation tremor"`
- `"dopamine agonist motor fluctuations"`
- `"physical therapy balance fall prevention Parkinson"`
- `"cognitive impairment Lewy body dementia"`

For each query, manually review the first page of ClinicalTrials.gov search results and record 3–5 NCT IDs that are clearly relevant. Store all queries and relevance labels in `eval/queries.json`:

```json
[
  {
    "query_id": "Q01",
    "query": "wearable gait sensor Parkinson disease",
    "relevant_nct_ids": ["NCT04123456", "NCT03987654"]
  }
]
```

### Metrics

| Metric | Definition |
|---|---|
| **Precision@5** | Fraction of the top-5 returned results that are labelled relevant, averaged over all queries |
| **Hit@5** | 1 if at least one relevant trial appears in the top 5, else 0; averaged over all queries |

MRR and Precision@10 can be added later as optional extensions once the pipeline is stable.

### Evaluation Script (`eval/evaluate.py`)

1. Load `eval/queries.json`.
2. For each query, call `/search?q=...&top_n=10`.
3. Compute Precision@5 and Hit@5.
4. Print a per-query table and overall averages.
5. Accept `--alpha` as a CLI argument so BM25-only, semantic-only, and hybrid results can be compared side by side.

### Reporting

Include a small results table in the `README.md` comparing at least two alpha values (e.g., `alpha=1.0` and `alpha=0.5`). This concretely shows what the hybrid scorer contributes.

---

## 19. Testing Plan

All tests live in `tests/` and are run with `pytest`.

### Unit Tests

| File | What is tested |
|---|---|
| `test_bm25_retriever.py` | Correct tokenisation; an exact-match query ranks its document first; empty query returns an empty list |
| `test_semantic_retriever.py` | Embedding output shape is correct; cosine similarity is in [0, 1] after clipping; identical query and document score near 1.0 |
| `test_hybrid_scorer.py` | `alpha=1.0` ranking matches BM25-only order; `alpha=0.0` ranking matches semantic-only order; no duplicate NCT IDs in output |
| `test_template_summary.py` | Null fields are omitted from output; field labels appear in output; function returns a non-empty string for a complete trial record |

### Integration Tests

| File | What is tested |
|---|---|
| `test_api_routes.py` | `/health` returns 200; `/search` with a valid query returns a non-empty list; `/summary` with a valid NCT ID returns a summary string; `/summary` with an unknown NCT ID returns 404; `top_n` parameter is respected |

### Test Fixtures (`conftest.py`)

- A small in-memory SQLite database with 10 synthetic trial records.
- A tiny BM25 index built from those records.
- A small fixed-size numpy embedding matrix for deterministic semantic tests.
- A FastAPI `TestClient` pointed at the test database and indexes.

Tests should not touch `trials.db`, `bm25_index.pkl`, or `embeddings.npy` in the working directory.

---

## 20. Risks and Simplifications

| Item | Notes |
|---|---|
| BM25 index in memory | Acceptable for a corpus under 5,000 records; re-examine if corpus grows significantly |
| Numpy cosine similarity | Fast and sufficient at this corpus size; FAISS is a future option, not a V1 requirement |
| Manual relevance labels are approximate | Label based on ClinicalTrials.gov search result pages; document the labelling date and query used |
| Template summaries feel mechanical | This is intentional; it is a feature of the grounding constraint, not a shortcoming. Frame it that way in the README |
| SQLite is single-writer | Not an issue; V1 is read-only after ingestion |
| ClinicalTrials.gov API schema may change | Pin the API version (`v2`) in the download script; record the download date in the README |
| `search_text` field loses structure | BM25 cannot distinguish a term in the title from one in the eligibility text; acceptable trade-off for V1 simplicity |
| Embedding model choice is general-purpose | `all-MiniLM-L6-v2` is not biomedical-specific; a domain-adapted model (e.g., `BioLORD-2023`) is a straightforward V2 swap |

---

## 21. Future V2 Extensions

- **Full trial detail endpoint:** Add a `GET /trial/{nct_id}` endpoint returning the complete structured record for a single trial. Not needed in V1 because `/summary/{nct_id}` already retrieves the same data internally.
- **PubMed integration:** Add a second corpus of PubMed abstracts and support cross-corpus retrieval.
- **Domain-adapted embeddings:** Swap `all-MiniLM-L6-v2` for a biomedical sentence encoder such as `BioLORD-2023` or `PubMedBERT`.
- **LLM-based summarisation:** Replace the template summariser with a local open-source model (e.g., via `ollama`) while keeping the grounding constraint.
- **Cross-encoder re-ranking:** Add a cross-encoder as a third retrieval stage after the initial hybrid ranking.
- **Filter facets:** Add status, phase, and date-range filters to both the API and the UI.
- **FAISS index:** Replace numpy cosine search with a FAISS IVF index if the corpus grows beyond 20,000 records.
- **GitHub Actions CI:** Automated `pytest` run on every push.
- **Expanded evaluation set:** Grow to 50+ queries with documented labelling methodology.

---

## 22. Definition of Done for V1

V1 is complete when all of the following are true:

- [ ] `scripts/download.py` successfully paginates the ClinicalTrials.gov API and saves raw JSON to `data/raw/`.
- [ ] `scripts/ingest.py` parses the raw data and populates `trials.db` without errors. Re-running it does not create duplicates.
- [ ] `scripts/build_bm25_index.py` and `scripts/build_embeddings.py` complete without errors and produce loadable artefacts in `indexes/`.
- [ ] `uvicorn app.api.main:app` starts without errors. `GET /health` returns `{"status": "ok"}`.
- [ ] `GET /search?q=parkinson+gait` returns a non-empty ranked list with the expected JSON structure.
- [ ] `GET /summary/{valid_nct_id}` returns a non-empty string containing at least one field citation label (e.g., `[Brief Summary]`).
- [ ] `streamlit run ui/streamlit_app.py` opens in a browser and returns results for a test query without errors.
- [ ] Every result card includes a working ClinicalTrials.gov URL.
- [ ] No summary output contains any text that is not derived directly from a stored trial field.
- [ ] `pytest tests/` passes with zero failures.
- [ ] `eval/evaluate.py` runs without errors and prints Precision@5 and Hit@5 for the curated query set.
- [ ] The evaluation results table (BM25-only vs hybrid) is included in `README.md`.
- [ ] The README covers: what the project does, how to set it up, how to run each script in order, and how to start the app and the UI.
- [ ] The repository is public on GitHub with a clean commit history and no database files, index files, or raw data committed.
