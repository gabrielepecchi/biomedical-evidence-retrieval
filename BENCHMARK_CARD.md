# Benchmark Card — Biomedical Evidence Retrieval Benchmark

**Version:** V3.6  
**Last updated:** 2025

---

## Task Definition

Ranked retrieval of Parkinson disease clinical trial records in response to plain-text biomedical queries. Given a query, the system returns a ranked list of trials from a local SQLite database. Retrieval quality is measured by how well the top-ranked results match manually assigned relevance labels.

---

## Dataset Scope

- **Source:** ClinicalTrials.gov (V2 API), condition filter: Parkinson disease
- **Format:** Structured trial records stored in SQLite; retrieval operates over a concatenated `search_text` field (title, conditions, interventions, brief summary)
- **Coverage:** Single disease area (Parkinson disease); no external data sources

---

## Query Set

- **Size:** 46 queries
- **Construction:** Manually curated to cover diverse clinical topics including treatments, rehabilitation, device therapies, diagnosis, non-motor symptoms, cognitive symptoms, advanced therapies, and gait/freezing
- **Examples:** `levodopa motor fluctuations Parkinson disease`, `deep brain stimulation subthalamic nucleus`, `alpha-synuclein immunotherapy clinical trial`, `exercise rehabilitation gait freezing Parkinson`

---

## Label Methodology

Relevance judgments were assigned on a three-point scale:

| Score | Meaning |
|---|---|
| 0 | Not relevant |
| 1 | Partially relevant |
| 2 | Highly relevant |

**Important caveats:**

- Labels are **candidate-based**: each query was judged by reviewing the top-10 results returned by the hybrid retriever at alpha=0.5. Trials not appearing in those candidates were not reviewed and received no label.
- Labels were assigned by a single reviewer for portfolio purposes. They are **not independently verified** and **not clinically validated**.
- Because the judge and the retriever share the same candidate pool, benchmark scores are optimistic relative to an independently sourced evaluation set.

---

## Retrieval Methods Compared

| Method | Description |
|---|---|
| BM25-only (α=1.0) | Keyword retrieval using `BM25Okapi` over `search_text` |
| Semantic-only (α=0.0) | Dense retrieval using `all-MiniLM-L6-v2` sentence embeddings |
| **Hybrid (α=0.5)** | Linear combination: `0.5 × BM25_norm + 0.5 × semantic_norm` |
| BioLORD experiment | Standalone biomedical embedding model (`FremyCompany/BioLORD-2023`); not the default |
| Reranker experiment | CrossEncoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) over top-50 hybrid candidates; not the default |

---

## Metric Definitions

**Precision@5** — fraction of the top-5 results that are relevant (relevance ≥ 1), averaged across queries.

**Hit@5** — fraction of queries where at least one relevant result appears in the top-5.

**Recall@10** — fraction of all known relevant trials that appear in the top-10, averaged across queries.

**MRR (Mean Reciprocal Rank)** — average of the reciprocal rank of the first relevant result; measures how early the first hit appears.

**nDCG@10 (Normalised Discounted Cumulative Gain)** — graded metric that rewards placing highly relevant results (score 2) above partially relevant ones (score 1) in the top-10; accounts for rank position.

Binary metrics (Precision@5, Hit@5, Recall@10, MRR) use a relevance threshold of ≥ 1.

---

## Results (V3.1 — 46-query graded benchmark)

| Method | Precision@5 | Hit@5 | Recall@10 | MRR | nDCG@10 |
|---|---:|---:|---:|---:|---:|
| BM25-only (α=1.0) | 0.8391 | 0.9783 | 0.7709 | 0.9303 | 0.7556 |
| Semantic-only (α=0.0) | 0.6652 | 1.0000 | 0.5656 | 0.8931 | 0.6268 |
| **Hybrid (α=0.5)** | **0.9913** | **1.0000** | **0.9976** | **1.0000** | **0.9453** |

BioLORD did not improve over the standard hybrid baseline on this benchmark. The CrossEncoder reranker also did not improve metrics; scores dropped across all metrics versus the standard hybrid.

---

## What the Scores Demonstrate

- Hybrid retrieval consistently outperforms BM25-only and semantic-only across all five metrics on this corpus.
- BM25 provides strong precision on exact clinical terminology; semantic retrieval adds recall for paraphrased or synonym-heavy queries; neither alone is sufficient.
- The evaluation methodology is internally consistent and covers a clinically diverse query set within a single disease domain.
- The error analysis identifies specific failure patterns per method (see below), which is consistent with the quantitative results.

---

## What the Scores Do Not Prove

- These results should not be interpreted as a rigorous information retrieval benchmark. Labels are candidate-based: the labelling pool and the retrieval system are not independent.
- Results do not generalise beyond Parkinson disease trials or beyond this corpus snapshot.
- High scores partially reflect that the retriever and the judge share the same candidate pool — an independent evaluation set would likely yield lower numbers.
- These results do not imply clinical validity, suitability for medical decision-making, or deployment readiness.

---

## Error Analysis

15 qualitative entries in `eval/error_analysis.json` document cases where BM25-only or semantic-only underperformed hybrid. Seven failure mode categories were identified:

| Failure mode | Description |
|---|---|
| `synonym_mismatch` | Query term not present in indexed text; lexical match fails on equivalent terms or rare drug names |
| `semantic_drift` | General embedding model conflates disease-specific context with broader clinical or non-PD usage |
| `lexical_overmatch` | BM25 scores trials highly due to token overlap on anatomical or drug names without capturing treatment modality |
| `biomarker_vs_treatment_confusion` | BM25 cannot distinguish diagnostic vs. therapeutic use of the same protein name |
| `nonmotor_symptom_ambiguity` | Semantic retrieval drifts toward general psychiatric or neurological trials when PD context is underweighted |
| `field_specificity_gap` | Relevant trial uses different terminology in the indexed short text than in the full protocol |
| `candidate_pool_bias` | Dense score distribution in high-volume retrieval categories compresses rank separation for semantic-only |

In most documented cases, hybrid scoring at α=0.5 corrects the failure by combining BM25's exact token match with semantic context.

---

## Known Limitations

- Single disease domain (Parkinson disease); generalisation to other conditions is untested.
- `all-MiniLM-L6-v2` is a general-purpose sentence encoder; biomedical-specialised models were tested but did not improve results on this candidate-based corpus.
- Relevance labels cover only the trials that appeared in the top-10 candidate pool; no judgments exist for trials outside that pool.
- 46 queries is a small evaluation set; benchmark should be expanded with independently sourced judgments before use in rigorous comparison.
- Template-based summaries only; no language generation.
- No authentication, cloud deployment, or persistent sessions.
