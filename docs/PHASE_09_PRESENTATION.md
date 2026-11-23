# Phase 9 — M.Tech viva presentation (editable slide source)

**Presenter note:** Each numbered section is one slide. Build into the university PPT template; do not present archival metrics as newly run experiments.

## Slide 1 — Title
**RareGenXAI: Explainable Rare Genetic Disease Prioritization with HPO**
Subtitle: Local research prototype, retrospective RareBench evaluation.
Visual: project logo/screenshot only if captured from the real running app.
Speaker cue: “This work ranks candidate diseases from standardized phenotype terms. It is not a diagnostic tool.”

## Slide 2 — Problem and motivation
Rare diseases share symptoms; phenotype data can be incomplete or inconsistent.
Question: how do transparent ontology-based baselines compare with experimental ML pipelines?
Speaker cue: “The purpose is to prioritize research hypotheses, not to diagnose patients.”

## Slide 3 — Objectives
Official HPO knowledge; overlap/semantic/TF-IDF/ML ranking; explanation traces; local UI/API; reproducible public-case evaluation.
Speaker cue: “The focus is traceable evidence and a fair comparison.”

## Slide 4 — System architecture
React (127.0.0.1:5173) -> FastAPI (127.0.0.1:8000) -> HPO schema-v2 SQLite + trusted verified model.
Presenter visual: redraw architecture; show both local ports and no cloud database.

## Slide 5 — HPO knowledge and data provenance
Official hp.obo and phenotype.hpoa; canonical terms/aliases/parents; source SHA-256 manifests, read-only inference.
Speaker cue: “We trace which sources and model snapshot produced a result.”

## Slide 6 — Ranking methods
Exact overlap; ontology semantic; TF-IDF retrieval; logistic/RF/XGBoost/MLP rerankers.
Experimental evidence weights +1.0, +0.4, -0.6, 0.0; no probabilistic interpretation.
Speaker cue: “ML shortlists and overlap candidate universes differ.”

## Slide 7 — Explainability and safeguards
Exact/ontology-related phenotype evidence; signed baseline contributions; model input-feature values are not SHAP. Reject invalid HPO input; local-only service.
Speaker cue: “These explain ranking evidence, not medical causality.”

## Slide 8 — Evaluation protocol
RareBench cohorts LIRICAL 143, MME 11, HMS 24 = 178 eligible archived cases. Six methods and 1,068 saved outputs. Metrics Top-1/Top-5/MRR/recall and 2,000 exploratory bootstrap replicates.
Speaker cue: “Archived predictions were re-audited; original case HPO CSV/model bytes were missing from the archive.”

## Slide 9 — Archived outcome comparison (not new Phase 7 inference)
| Method | Top-1 | Top-5 | MRR |
|---|---:|---:|---:|
| Overlap | 37.64% | 54.49% | 0.453 |
| XGBoost | 36.52% | 51.69% | 0.436 |
| Logistic | 34.27% | 48.88% | 0.410 |
| Random Forest | 32.58% | 42.13% | 0.371 |
| MLP | 30.90% | 41.57% | 0.363 |
| TF-IDF | 29.78% | 43.26% | 0.361 |
Source: `docs/PHASE_07_HISTORICAL_REANALYSIS.md`.
Speaker cue: “The simple baseline came first overall. We do not claim ML beats it.”

## Slide 10 — Failure analysis and validity
Small MME cohort (n=11); HMS overlap Top-1 = 0/24. Potential annotation/literature overlap; synthetic disease training; unequal candidate universes. No real matched DeepRare predictions.
Speaker cue: “Our limitations are part of the result.”

## Slide 11 — Live demonstration (conditional)
Only after local data/model readiness and Phase 8 pass: search HP:0001250, run overlap and trained model ranking, select a candidate, inspect explanations. Use public/example HPO terms only. If not ready, label screen recordings/screenshots as historical and state live demo unavailable; never simulate a successful service.

## Slide 12 — Conclusions, next work and questions
Auditable, explainable local prototype; archived overlap strongest; full new benchmark and Mac final acceptance pending. Next: equal-candidate reranker comparison, matched DeepRare outputs, ethical prospective validation.
Speaker cue: “Thank you; I welcome questions about the design, results and limitations.”
