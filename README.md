# Biomedical Evidence Retrieval Benchmark

[![CI](https://github.com/gabrielepecchi/biomedical-evidence-retrieval/actions/workflows/ci.yml/badge.svg)](https://github.com/gabrielepecchi/biomedical-evidence-retrieval/actions/workflows/ci.yml)

A portfolio project that benchmarks hybrid retrieval over clinical trial records — combining BM25 and semantic similarity — with a FastAPI backend and a Streamlit frontend.

---

## What This Project Does

Indexes Parkinson disease trials from [ClinicalTrials.gov](https://clinicaltrials.gov) into a local SQLite database and provides ranked search over trial records. Results are scored using a configurable hybrid formula:

```
hybrid_score = alpha × bm25_score + (1 − alpha) × semantic_score
```

A template-based summary is generated per trial on request. Retrieval quality is measured against a curated benchmark of 46 graded queries.

**Stack:** Python 3.12 · FastAPI · Streamlit · SQLite · rank-bm25 · sentence-transformers · pytest

---

## What This Project Demonstrates

- **End-to-end retrieval pipeline** — raw API ingestion → SQLite → BM25 + dense embeddings → ranked results
- **Hybrid search** with a tunable alpha slider balancing keyword and semantic signals
- **REST API and frontend** — FastAPI with `/health`, `/search`, `/summary/{nct_id}`, optional filters; Streamlit UI
- **Retrieval evaluation methodology** — Precision@5, Hit@5, Recall@10, MRR, nDCG@10 over 46 graded queries
- **Controlled experimentation** — biomedical embeddings (BioLORD) and a CrossEncoder reranker tested and found not to improve over the standard hybrid baseline on this corpus
- **Error analysis** — 15 qualitative entries covering `synonym_mismatch`, `semantic_drift`, `lexical_overmatch`, and other failure modes; multi-method candidate pooling for future label auditing
- **Conservative clinical framing** — results are not clinical decision support; relevance labels are candidate-based and not clinically validated

---

## Best Retrieval Results (V3.1 — 46-query graded benchmark)

| Method | Precision@5 | Hit@5 | Recall@10 | MRR | nDCG@10 |
|---|---:|---:|---:|---:|---:|
| BM25-only (α=1.0) | 0.8391 | 0.9783 | 0.7709 | 0.9303 | 0.7556 |
| Semantic-only (α=0.0) | 0.6652 | 1.0000 | 0.5656 | 0.8931 | 0.6268 |
| **Hybrid (α=0.5)** | **0.9913** | **1.0000** | **0.9976** | **1.0000** | **0.9453** |

> **Benchmark caveat:** Relevance labels were assigned by reviewing the top-10 results per query (candidate-based). Scores are high partly because the judge and the retriever share the same candidate pool. These results should not be treated as a definitive clinical benchmark.

---

## Screenshots

The Streamlit UI supports filtered search, ranked results with hybrid scores, and grounded per-trial summaries.

![Streamlit search interface with optional filters](assets/screenshots/search-home.png)
*Search interface with optional status, phase, and study type filters*

![Search results with hybrid scores](assets/screenshots/search-results.png)
*Ranked results with hybrid scores*

![Grounded summary view](assets/screenshots/grounded-summary.png)
*Grounded summary view*

---

## Architecture

```
ClinicalTrials.gov API
        │
   scripts/download.py       ← raw JSON pages
   scripts/ingest.py          ← SQLite (db/trials.db)
   scripts/build_bm25_index.py
   scripts/build_embeddings.py
        │
   app/retrieval/
   ├── bm25_retriever.py
   ├── semantic_retriever.py
   └── hybrid_scorer.py
        │
   app/api/  (FastAPI)  ←→  ui/streamlit_app.py
        │
   eval/
   ├── evaluate.py            ← Precision@5, Hit@5, Recall@10, MRR, nDCG@10
   ├── compare_retrievers.py  ← BioLORD comparison
   ├── compare_reranker.py    ← CrossEncoder experiment
   ├── trial_matching_lite.py ← synthetic patient cases
   └── error_analysis.json    ← qualitative failure modes
```

---

## Setup

```bash
git clone <repo-url>
cd biomedical-evidence-retrieval
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Run Order

```bash
# 1. Download raw trial data
python -m scripts.download

# 2. Parse and load into SQLite
python -m scripts.ingest

# 3. Build BM25 index
python -m scripts.build_bm25_index

# 4. Build sentence embeddings (slowest step)
python -m scripts.build_embeddings

# 5. Start FastAPI backend (keep terminal open)
python -m uvicorn app.api.main:app --reload

# 6. Start Streamlit frontend (new terminal)
python -m streamlit run ui/streamlit_app.py
```

- FastAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Streamlit app: [http://localhost:8501](http://localhost:8501)

---

## Evaluation

```bash
python -m eval.evaluate --alpha 0.5   # hybrid
python -m eval.evaluate --alpha 1.0   # BM25-only
python -m eval.evaluate --alpha 0.0   # semantic-only
```

Metrics: **Precision@5**, **Hit@5**, **Recall@10**, **MRR**, **nDCG@10** (graded 0/1/2).

> The FastAPI backend must be running before you run the evaluation script.

Run all tests:

```bash
pytest
```

---

## Example Queries

- `levodopa motor fluctuations Parkinson disease`
- `deep brain stimulation subthalamic nucleus`
- `dopamine agonist monotherapy early Parkinson`
- `alpha-synuclein immunotherapy clinical trial`
- `exercise rehabilitation gait freezing Parkinson`

Use the `alpha` slider to balance BM25 vs semantic retrieval. Expand "Filters (optional)" to narrow by Overall Status (e.g. `Recruiting`), Phase (e.g. `Phase 2`), or Study Type (e.g. `Interventional`).

---

## Reproducibility Notes

- Tested with **Python 3.12**. All dependencies pinned in `requirements.txt`.
- `data/raw/`, `db/trials.db`, and `indexes/` are git-ignored; regenerate locally via Steps 1–4 above.
- Biomedical embeddings (`indexes/biomedical_embeddings.npy`) are optional — only needed for `eval/compare_retrievers.py` and `eval/collect_unlabeled_candidates.py`. The main app and benchmark use `all-MiniLM-L6-v2` only.

---

## Experiment Results (V2.3 — V2.4)

**BioLORD biomedical embeddings** did not improve retrieval on this benchmark — likely because relevance labels were derived from general-model candidates and the corpus contains short search-text rather than full clinical prose.

**CrossEncoder reranker** (`cross-encoder/ms-marco-MiniLM-L-6-v2` over top-50 hybrid candidates) also did not improve metrics; scores dropped across all four metrics vs hybrid standard.

Both experiments are preserved as standalone scripts and are not enabled by default.

---

## Limitations

- Data is limited to Parkinson disease trials from ClinicalTrials.gov.
- `all-MiniLM-L6-v2` is a general-purpose model, not specialised for biomedical text.
- Summaries are template-based — no language generation.
- Relevance labels are candidate-based and manually assigned; the benchmark should be expanded with independently sourced judgments before use as a rigorous benchmark.
- No authentication, cloud deployment, or persistent user sessions.

---

## Future Improvements

- **Label audit:** manually review `eval/unlabeled_candidates_alpha_0_5.json` to reduce candidate-pool bias and produce more reliable benchmark scores.
- **Benchmark expansion:** add queries beyond Parkinson disease and source independent relevance judgments to validate retrieval across a broader clinical domain.
- **LLM-based summaries:** replace the template summary with a lightweight LLM call for more readable, context-aware trial descriptions.
- **Demo polish:** add pagination, result highlighting, and a shareable query URL to the Streamlit UI.
- **Cloud deployment:** containerise with Docker and deploy the FastAPI backend and Streamlit frontend to a public URL for portfolio accessibility.
