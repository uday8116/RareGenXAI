# Phase 9 — Demonstration speech and viva questions

**Delivery:** Plain English; adapt to real timing and university instructions. Never state that unfinished CI or local validation passed.

## Sample 5-minute speech

“Good morning. My M.Tech project is RareGenXAI, an explainable AI research prototype for prioritizing rare genetic disorders from phenotype information. Many rare disorders share similar clinical features, so ranking possible disorders from standardized HPO terms can help researchers explore disease hypotheses. This project is **not** a medical diagnosis system.

First, I prepare a knowledge base using official Human Phenotype Ontology files: terms, ontology relationships and disease–phenotype associations. Their source checksums are recorded. The data is stored in a versioned local SQLite database. The React frontend connects to a FastAPI backend on the same computer, and the backend reads disease knowledge and trusted model files.

Second, I compare simple phenotype overlap, ontology-aware semantic ranking and TF-IDF retrieval with Logistic Regression, Random Forest, XGBoost and MLP reranking models. The ML models train on synthetic queries constructed from disease knowledge, not on actual hospital patient training records. I also provide evidence traces: matching terms, ontology relationships and signed baseline contributions. Displayed model feature inputs are not causal explanations.

Third, I examine archived predictions from a previous external published-case benchmark, RareBench. There are 178 eligible cases: 143 LIRICAL, 11 MME and 24 HMS. Exact overlap achieved 37.64 percent Top-1 and 54.49 percent Top-5 accuracy in that archived snapshot. XGBoost achieved 36.52 percent Top-1. So the older results do **not** show that the ML methods outperform the simple baseline. Performance varies by cohort; for example, HMS was difficult for overlap. This is a retrospective benchmark, not proof of clinical accuracy.

For reproducibility, the later evaluation code freezes the case list, methods and dataset/model hashes before inference. It can audit per-case rankings, missing results and bootstrap uncertainty. But the latest full Phase 7 run and the Phase 8 physical Mac acceptance checks remain unverified. The archived artifact did not contain all original inference inputs, and we do not have authentic same-case DeepRare predictions. I do not claim a direct win over DeepRare.

I will now demonstrate the research workflow with a public example HPO term. If the live environment is not prepared, I will explain the screenshots rather than claim that the service is currently running. In conclusion, the main project value is a transparent local architecture and auditable evaluation. The work also demonstrates an important finding: added ML complexity did not necessarily improve the older overall ranking results. Thank you.”

## Viva questions with concise answers

1. **What is your project?** An HPO-based candidate rare-disease ranking *research prototype*, not a diagnosis system.
2. **What is HPO?** A controlled vocabulary and hierarchy of human phenotypic abnormalities.
3. **Why HPO instead of free text?** Standard identifiers reduce synonym and naming ambiguity; upstream normalization still matters.
4. **What data is stored?** Curated ontology terms and disease annotations, not individual patient records.
5. **What is Top-1?** Share of cases whose known disease is ranked first.
6. **What is Top-5?** Share whose known disease appears within the top five candidates.
7. **What is MRR?** Mean of reciprocal rank; a missing target has value zero.
8. **How many historical cases?** 178 eligible published RareBench cases across LIRICAL, MME and HMS.
9. **Which archived method led overall Top-1?** Exact overlap, 37.64%; XGBoost was 36.52% in the same saved-results snapshot.
10. **Why use ML if overlap won?** To test research hypotheses and understand relative strengths; a negative comparison is still informative.
11. **What models were implemented?** TF-IDF retrieval plus logistic, random forest, XGBoost and MLP rerankers, alongside ontology baselines.
12. **How were ML models trained?** Synthetic disease–phenotype queries from HPO annotation data, not supervised real hospital patient records.
13. **What is semantic similarity?** Compare terms through shared ontology ancestors and information content.
14. **How is absent evidence handled?** An experimental negative weight, not a calibrated likelihood or a new invention.
15. **What is explainable here?** Baseline evidence contributions and ontology links; reranker input values are not model-causal SHAP.
16. **What is the main novelty?** Integrated auditability, source/model provenance, constrained explanations and aligned experimental comparisons; no invented clinical breakthrough.
17. **Is DeepRare directly compared?** No. Authentic predictions on the same filtered cases were not available.
18. **What are the limitations?** Annotation/literature overlap, synthetic training, small cohorts, unequal candidate universes, absent prospective validation.
19. **What is disease coverage?** Whether the correct disease ID exists in the model's knowledge universe, separate from rank accuracy.
20. **Why use SHA-256?** To detect changed source/model bytes and improve reproducibility; SHA-256 alone does not authenticate origin.
21. **Why SQLite?** Simple local versioned read-only knowledge storage and reproducible lookup.
22. **Why FastAPI and React?** Clear typed local API and accessible research frontend with separated concerns.
23. **How do you prevent invalid HPO inputs?** Pydantic validation, canonical IDs, duplicate/nonclinical/obsolete checks and 422 errors.
24. **Has the latest full system passed?** Not yet verified; previous CI attempts failed before steps, and physical Mac tests remain outstanding.
25. **What is the next experiment?** Freeze a fresh source/model snapshot, run full RareBench protocol, inspect errors and compare equal candidate universes.

## Examiner demonstration checklist

- Show `GET /api/v1/ready` and `GET /api/v1/models`, not only liveness.
- Use public/example phenotype ID `HP:0001250`; do not enter real personal health data.
- Show candidate ranking and ontology evidence trace without calling it a diagnosis.
- Show the historical report's source and describe model results accurately.
- If a model/API is missing, explain the failure transparently rather than fabricate output.
