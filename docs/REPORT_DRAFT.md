> **Superseded early working draft:** This was written before the later six-method archived evaluation and React/FastAPI research implementation. For current Phase 9 academic material use [PHASE_09_DISSERTATION_DRAFT.md](PHASE_09_DISSERTATION_DRAFT.md) and [PHASE_09_EVIDENCE_LEDGER.md](PHASE_09_EVIDENCE_LEDGER.md). Do not present the old "results pending" or Streamlit-only scope as the latest project status.

# M.Tech Project Report — Working Draft

**Title:** Explainable AI-Based Classification of Rare Genetic Disorders Using Clinical Phenotypes and Human Phenotype Ontology

## Abstract (draft)
This project implements a transparent, phenotype-based rare-disease prioritization prototype using the Human Phenotype Ontology (HPO) and disease–phenotype annotations. It compares exact overlap, ontology-aware semantic similarity, and a proposed evidence-quality-aware ranking heuristic. Clinical findings can be marked as confirmed present, suspected present, confirmed absent, or unknown. The system displays per-phenotype contributions to each candidate's score. A controlled synthetic evaluation examines ranking robustness under missing observations. Synthetic queries derived from the annotation knowledge base do not establish real-world clinical accuracy. Independent validation is required before any clinical use.

## 1. Introduction
Rare genetic disorders often share clinical findings. HPO provides a standardized vocabulary and relationships between phenotype concepts. A prioritization system can assist research by ranking diseases according to recorded phenotypes, but a ranked candidate is not a diagnosis.

## 2. Problem statement
A simple symptom-matching system does not distinguish reliable findings from uncertain observations. This project tests whether a transparent reliability-weighting heuristic affects ranking performance under simulated incomplete clinical descriptions.

## 3. Objectives
- Parse official HPO ontology and disease–phenotype associations.
- Implement exact-overlap and semantic-similarity baselines.
- Implement and explain a reliability-aware ranking heuristic.
- Evaluate reproducibly on controlled synthetic queries.
- Build a usable local Streamlit research demonstration.

## 4. Literature context
Phenomizer (Köhler et al., 2009) introduced semantic phenotype-based diagnosis prioritization. LIRICAL (Robinson et al., 2020) provides likelihood-ratio-based phenotype interpretation and includes negative findings. Therefore neither HPO matching nor use of absent phenotypes alone is claimed as novel.

## 5. Proposed method
Disease profiles are sets of annotated HPO terms. The ontology gives ancestor relationships. Information content is computed from the proportion of disease profiles annotated with each phenotype or its descendants. Semantic matching uses a normalized most-informative-common-ancestor score. The experimental evidence weights are +1.0 for confirmed present, +0.4 for suspected present, -0.6 for confirmed absent, and 0 for unknown. The disease score is the sum of weighted similarities divided by the sum of absolute nonzero weights. This is a ranking heuristic, not a likelihood or probability.

## 6. Evaluation protocol
Controlled queries are sampled from HPO annotations. Missingness is simulated at 0%, 20%, 40%, and 60%, with a fixed random seed. Metrics are Top-1, Top-5, and mean reciprocal rank (MRR). Record the number of queries, source checksums, hardware, and execution time.

## 7. Results
**Pending reproducible benchmark execution.** Import exact figures from `results/synthetic_summary.csv`. Do not add unmeasured numbers. Plots are generated with `python -m src.plots`.

## 8. Limitations
The synthetic benchmark is not independent clinical validation; simulated evidence quality is not real patient confidence. The method's novelty and clinical utility are unproven. No evidence of improvement should be claimed without a fair controlled comparison and independent testing.

## 9. Conclusion (draft)
A transparent, HPO-based rare-disease ranking prototype was developed. Whether evidence-quality weighting provides a measurable benefit remains an empirical question. Future work includes independent clinical case evaluation, calibration, weight sensitivity analysis, and comparison with established tools.

## References
1. Köhler et al. (2009), Phenomizer, *American Journal of Human Genetics*. https://doi.org/10.1016/j.ajhg.2009.09.003
2. Robinson et al. (2020), LIRICAL, *American Journal of Human Genetics*. https://doi.org/10.1016/j.ajhg.2020.06.021
3. Human Phenotype Ontology: https://hpo.jax.org/
