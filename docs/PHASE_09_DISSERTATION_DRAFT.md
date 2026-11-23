# M.Tech Dissertation Draft — RareGenXAI

**Working title:** Explainable AI-Based Rare Genetic Disease Prioritization Using Clinical Phenotypes and the Human Phenotype Ontology

**Status:** Technical draft for academic review, **not** a university-approved thesis or proof of prospective medical validity.

## Front matter (to be supplied and approved)

- Institution, department, registration number, student and supervisor names
- Official cover, certificates, declaration, acknowledgements, ethics statement where required
- University citation style, signature pages, submission date and approved formatting
- Real screenshots taken from a working local deployment (no real patient information)

## Abstract

Rare genetic diseases can share clinical findings and are difficult to prioritize using only a few phenotype observations. RareGenXAI is a local, explainable research prototype that uses Human Phenotype Ontology (HPO) concepts and disease–phenotype annotations to rank candidate genetic disorders. It combines exact phenotype-overlap and ontology-semantic methods with TF-IDF retrieval and experimental Logistic Regression, Random Forest, XGBoost and multilayer-perceptron rerankers trained on synthetic phenotype queries. A React website and FastAPI service display ranked candidates, source provenance and evidence traces; the HPO knowledge base uses a versioned SQLite schema. A retrospective archival reanalysis of 178 eligible published RareBench cases (LIRICAL 143, MME 11, HMS 24) reported 37.64% Top-1 and 54.49% Top-5 for exact overlap on one earlier model/data snapshot. Exact overlap led overall Top-1 in that archived snapshot. These archived outcomes are **not** fresh Phase 7 model inference or clinical validation. The study emphasizes auditable evaluation, explicit known-disease coverage, matched same-case comparisons and limitations of synthetic training and unequal retrieval universes. The prototype must not be used to diagnose patients.

**Keywords:** HPO, rare genetic disorders, explainable AI, candidate prioritization, retrospective evaluation, provenance.

## Chapter 1 — Introduction and problem statement

A rare-disease phenotype may be described by multiple clinical terms. Synonyms, hierarchical similarity, missing observations and overlapping clinical signs complicate matching against disease profiles. Existing work in semantic phenotype ranking already addresses many of these challenges. The project asks whether a transparent, locally reproducible implementation can compare simple ontology-based baselines against synthetic-query-trained rerankers using aligned public retrospective cases. The output is a ranked *research hypothesis list*, not a clinical conclusion.

**Objectives:** prepare official source-checked HPO knowledge; construct reproducible baseline/ML rankers; expose strict, read-only research APIs; provide transparent evidence traces; compare methods using identical case IDs; report metric denominators, errors, uncertainty, model/source hashes and known limitations.

## Chapter 2 — Literature and novelty positioning

HPO standardizes phenotype vocabularies and relationships. Phenomizer introduced phenotype-semantic disease prioritization, and LIRICAL applies probabilistic phenotype evidence including negative findings. DeepRare is a more recent reasoning-based system. RareGenXAI **does not invent HPO matching, explainability, negative findings or XGBoost/MLP**. Its defensible contribution is an auditable local implementation that compares several ranking pipelines, tracks source/model provenance, checks cross-method case alignment, displays constrained ontology-based explanations, and reports both failures and positive results. No statistically established clinical improvement over existing published systems is claimed.

## Chapter 3 — Data, knowledge modeling and architecture

Official HPO ontology and phenotype-to-disease annotation files are ingested with recorded source manifests. A versioned schema-v2 SQLite database stores HPO canonical terms, alternate IDs, synonyms, parent edges, disease identifiers and annotated phenotype relationships, including source-row provenance. The React frontend (local 127.0.0.1:5173) communicates through a Vite proxy with a loopback FastAPI backend (127.0.0.1:8000). This backend reads local SQLite knowledge and optionally a hash-verified trusted joblib bundle. The clinical HPO branch excludes ontology nonclinical categories and obsolete terms. The API does not intentionally persist observations.

## Chapter 4 — Ranking algorithms and interpretability

The overlap baseline matches observed HPO IDs against disease profiles. The semantic method considers shared ontology ancestry and information content. Evidence statuses are confirmed present, suspected present, confirmed absent and unknown, with experimental heuristic weights (1.0, 0.4, -0.6, 0.0). These are design choices and **not** learned/calibrated patient probabilities. TF-IDF retrieves candidate diseases; logistic, random forest, XGBoost and MLP models rerank a fixed shortlist using features derived from annotation-based synthetic queries. Baseline overlap may search a broader disease universe than ML shortlisting, so comparing entire pipelines is not the same as comparing identical rerankers. Baseline explanation panels display observed evidence, matched/ontology-related findings and signed contributions; model feature inputs are not causal SHAP attributions.

## Chapter 5 — Evaluation design and research integrity

Public RareBench subsets (LIRICAL, MME, HMS) were filtered to eligible records with unambiguous diagnoses and sufficient HPO input. The earlier archived evaluation contains 178 cases: 143, 11 and 24 respectively, with 1,068 saved case-method results for six methods. For each method and case, the rank of the target disease contributes Top-1 (rank 1), Top-5 (rank <= 5), mean reciprocal rank (1/rank or zero if absent) and observed list recall. Denominators include nonmatched cases. The historical reanalysis independently checked saved matrix alignment and summary integrity, then computed exploratory case-resampling intervals with a fixed seed. However, the archive lacks original phenotype input CSV and model bytes, so original inference cannot be independently reproduced from that ZIP. A **new** Phase 7 experiment pre-freezes case IDs/order, chosen methods, source and model hashes and TF-IDF shortlist size, then rechecks raw predictions and output provenance. This new full run has **not** been verified as passing on the latest branch.

## Chapter 6 — Results (archived snapshot only)

| Method | Top-1 (178 cases) | Top-5 | MRR |
|---|---:|---:|---:|
| Exact overlap | **37.64%** | **54.49%** | **0.453** |
| XGBoost | 36.52% | 51.69% | 0.436 |
| Logistic Regression | 34.27% | 48.88% | 0.410 |
| Random Forest | 32.58% | 42.13% | 0.371 |
| MLP | 30.90% | 41.57% | 0.363 |
| TF-IDF | 29.78% | 43.26% | 0.361 |

**Source:** `docs/PHASE_07_HISTORICAL_REANALYSIS.md`, saved predictions from GitHub Actions run 44467435510; historical reanalysis, **not new inference**. Disease-ID knowledge coverage is approximately 99.44% in the archive. The cohorts differ substantially: HMS Top-1 under the overlap baseline was 0%, while MME overlap Top-1 was 72.73%; small cohorts make percentages unstable. The chosen ML pipelines did not improve on overall exact overlap in this snapshot. Report exploratory intervals only with their case-resampling limitations; do not claim a clinical hypothesis test or universal model superiority.

## Chapter 7 — Verification and threats to validity

Phase 8 introduced local API/frontend startup, proxy, strict invalid-input tests, model-provenance consistency and repeated cold-restart acceptance. The scripts and tests are present, but latest GitHub Actions jobs previously failed before starting test steps; a physical Mac end-to-end run is still needed. Other threats include synthetic disease-annotation training; possible shared literature between public RareBench descriptions and HPO curation; small and dependent cohorts; missing original archived input/model bytes; different retrieval candidate universes; disease-ID mapping; and no genuine same-case DeepRare outputs. No prospective hospital validation or ethics-approved clinical trial has been performed.

## Chapter 8 — Conclusion and future work

RareGenXAI demonstrates explainable local phenotype-based rare-disease prioritization with a source-auditable HPO knowledge base and multiple ranking methods. The most interpretable baseline performed best overall on the archived evaluation. Future work should evaluate new public snapshots with the frozen protocol, investigate cohort-specific errors, isolate reranking from shortlist retrieval, quantify explanation faithfulness and uncertainty, obtain authentic DeepRare output for identical cases, and pursue prospective evaluation only after approvals and clinical oversight.

## References (verify university formatting)

1. Köhler et al. (2009). Phenomizer. *American Journal of Human Genetics*. https://doi.org/10.1016/j.ajhg.2009.09.003
2. Robinson et al. (2020). LIRICAL. *American Journal of Human Genetics*. https://doi.org/10.1016/j.ajhg.2020.06.021
3. Human Phenotype Ontology. https://hpo.jax.org/
4. RareBench dataset. https://huggingface.co/datasets/chenxz/RareBench
5. DeepRare paper, published research context. https://www.nature.com/articles/s41586-025-10097-9
6. Saved evaluation run and independently checked prediction archive: https://github.com/uday8116/RareGenXAI/actions/runs/44467435510

## Mandatory prior-to-submission verification

Replace all university-specific placeholders; add ethics and plagiarism declarations as required; capture real screenshots; regenerate metrics from any *new* Phase 7 run rather than silently replacing this older snapshot; rerun real Phase 8 acceptance; and obtain supervisor confirmation of novelty, citations and claims.
