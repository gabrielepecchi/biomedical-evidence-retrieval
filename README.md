# Biomedical Evidence Retrieval and Trial Matching Platform

A portfolio project that lets you search clinical trial records using a hybrid retrieval pipeline combining BM25 and semantic similarity, with a FastAPI backend and a Streamlit frontend.

---

## Overview

This platform indexes clinical trials from [ClinicalTrials.gov](https://clinicaltrials.gov) into a local SQLite database and provides keyword-based and semantic search over trial records. Results are ranked using a configurable hybrid score. A simple template-based summary is generated for each trial on request.

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
│   └── build_embeddings.py    # Build sentence embeddings
├── app/
│   ├── db.py                  # Database access layer
│   ├── models.py              # TrialRecord and SearchResult dataclasses
│   ├── retrieval/
│   │   ├── bm25_retriever.py
│   │   ├── semantic_retriever.py
│   │   └── hybrid_scorer.py
│   ├── summary/
│   │   └── template_summary.py
│   └── api/
│       ├── main.py            # FastAPI app entry point
│       └── routes.py          # API route definitions
├── ui/
│   └── streamlit_app.py       # Streamlit frontend
├── eval/
│   ├── queries.json           # Curated evaluation queries
│   └── evaluate.py            # Evaluation script
├── tests/
│   ├── test_bm25_retriever.py
│   ├── test_semantic_retriever.py
│   ├── test_hybrid_scorer.py
│   ├── test_template_summary.py
│   ├── test_api_routes.py
│   └── test_main.py
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

## Example Queries

These queries work well against the Parkinson disease trial dataset:

- `levodopa motor fluctuations Parkinson disease`
- `deep brain stimulation subthalamic nucleus`
- `dopamine agonist monotherapy early Parkinson`
- `alpha-synuclein immunotherapy clinical trial`
- `exercise rehabilitation gait freezing Parkinson`

Use the `alpha` slider in the Streamlit UI to adjust the balance between BM25 and semantic retrieval. `alpha=1.0` is BM25-only; `alpha=0.0` is semantic-only; `alpha=0.5` is balanced.

---

## Evaluation

The evaluation script measures retrieval quality over 10 manually curated queries defined in `eval/queries.json`.

```bash
# Evaluate with default alpha=0.5
python -m eval.evaluate --alpha 0.5

# Evaluate with BM25-only
python -m eval.evaluate --alpha 1.0
```

Metrics reported per query:

- **Precision@5** — fraction of the top 5 results that are relevant
- **Hit@5** — whether at least one relevant result appears in the top 5

> The API must be running before you run the evaluation script.

---

## Limitations

- Data is limited to trials matching a single condition filter (Parkinson disease) from ClinicalTrials.gov.
- The embedding model (`all-MiniLM-L6-v2`) is a general-purpose model, not specialised for biomedical text.
- Summaries are template-based and only include fields present in the database — no language generation.
- Evaluation queries are manually curated for demonstrating the evaluation workflow; relevance judgments should be reviewed and expanded before using the metrics as a rigorous benchmark.
- No authentication, no cloud deployment, no persistent user sessions.

---

## Future Improvements

- Add PubMed as a second data source and merge results across sources.
- Replace the general embedding model with a biomedical-domain model such as `BioLORD` or `PubMedBERT`.
- Add LLM-based abstractive summaries as an optional V2 feature.
- Add FAISS for faster approximate nearest-neighbour search at scale.
- Add GitHub Actions for automated testing on push.
- Add Docker for reproducible deployment.
- Expand the evaluation query set with real relevance judgements.
