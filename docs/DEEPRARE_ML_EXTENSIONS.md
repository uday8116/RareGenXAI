# DeepRare-inspired ML extensions (2026)

Reference: [DeepRare](https://github.com/MAGIC-AI4Med/DeepRare), Zhao et al., *Nature* (2026). DeepRare is an LLM-driven agentic clinical reasoning system. RareGenXAI does **not** reproduce DeepRare or claim comparable results.

## Our lightweight, distinct architecture
1. **TF-IDF retriever** converts disease phenotype sets to sparse HPO-ID term vectors. A patient query receives candidates by cosine similarity.
2. **Logistic Regression reranker** learns a binary candidate match score from transparent pairwise features.
3. **Random Forest reranker** learns nonlinear relationships between the same evidence features.
4. **Traditional HPO methods** remain comparison baselines: exact overlap, ontology-MICA semantic similarity, and evidence-quality-weighted semantic similarity.
5. **Transparent evidence**: for the ML methods the app reports the exact HPO matches and TF-IDF similarity. This is supporting evidence, **not a faithful per-feature explanation of the ML probability**. For HPO semantic ranking, the app shows intrinsic phenotype-level score decomposition.

## Pairwise ML features
- TF-IDF query–disease cosine similarity.
- Fraction of confirmed phenotypes exactly matching the candidate.
- Fraction of suspected phenotypes exactly matching the candidate.
- Candidate disease phenotype coverage.
- Fraction of confirmed-absent terms occurring in the disease profile.
- Number of observed positive phenotypes, and candidate phenotype profile size.

## Training and evaluation split
The model trains on synthetic phenotype queries sampled from selected disease profiles, producing positive and negative disease candidate pairs. Whole disease IDs are separated between ML training and testing (but **all disease profiles remain in the retrieval knowledge base**). The evaluation never inserts the correct test disease into the shortlist. Retrieval can miss the diagnosis entirely, in which case rank=0 and Top-1/Top-5/MRR=0. Metrics include candidate recall. This is **disease-disjoint synthetic validation, not independent clinical validation**.

## Run
```bash
python -m src.data
python -m src.train_ml --train-diseases 200 --test-diseases 60 --queries-per-disease 2 --candidates 25
streamlit run app.py
```
Saved model: `models/raregen_ml.joblib` (load only self-produced, trusted pickle files).
Evaluation tables: `results/ml_trials.csv`, `results/ml_summary.csv`, `results/ml_metadata.json`.
Use `python -m pytest -q` to run ML and traditional tests.

## Limitations and research honesty
- There is no independently labeled patient dataset in this training run.
- Training/testing synthetic queries use the same HPO annotation knowledge base; results can be optimistic.
- A disease-disjoint split tests transfer to new disease query IDs, not generalization to unseen patients.
- TF-IDF candidate retrieval has an exact HPO term dependence and can miss related terms.
- Logistic and RF scores are uncalibrated and should not be interpreted as diagnostic probabilities.
- Suspected and absent findings are simulated; no observed patient-level confidence data.
- No controlled clinical benchmark comparison with DeepRare has been completed.
- DeepRare's source is under CC BY-NC 4.0; RareGenXAI implements distinct code and does not copy or redistribute DeepRare datasets or model weights.
- Reporting should include exact measured outcomes, not inferred or invented accuracy numbers.

## Directions for future research
Ethically obtain independent clinical cases with diagnosis and standardized phenotypes; establish case-level train/test splits; compare on the same patients and candidate universes; tune hyperparameters on a separate development set; add confidence intervals and calibrated scores where appropriate; test explanation faithfulness and demographic/generalization issues.
