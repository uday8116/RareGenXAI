# Research verification and submission checklist

## Scope
RareGenXAI is a **knowledge-based disease prioritization** research prototype, not a trained classifier or clinical diagnostic device. It uses exact phenotype overlap, normalized HPO-MICA semantic similarity, and evidence-quality-aware semantic ranking. Scores are relative rankings, not disease probabilities.

## Data provenance
Run `python -m src.data`. Official sources: `hp.obo` and `phenotype.hpoa`. The program writes `data/raw/manifest.json` with download URLs, SHA-256 hashes and file sizes. Always cite the exact downloaded version in the thesis.

## Verification commands
```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m src.data
python -m pytest -q tests/test_app_integration.py
python -m src.evaluate --trials 12 --seed 42
python -m src.evidence_experiment
python -m src.plots
streamlit run app.py
```

## Research questions
1. How does ranking accuracy change as annotated phenotypes are randomly omitted?
2. Does HPO semantic similarity improve over exact overlap on this synthetic benchmark?
3. Does evidence-quality weighting improve the ranking under realistic uncertainty or explicitly absent findings?
4. Can the ranking be explained in terms of phenotype-level contributions?

## Evaluation
- Three ranking configurations: overlap baseline; semantic baseline; weighted semantic proposal.
- Synthetic missingness levels: 0%, 20%, 40%, 60%.
- Fixed seed: 42; metrics: Top-1, Top-5, MRR.
- Controlled evidence experiment: checks known positive, suspected, absent, and unknown observations using transparent toy profiles.
- Always report sample sizes. Small synthetic tests are *smoke tests*, not reliable clinical performance estimates.
- The current generator samples only positive annotations and adds suspected labels randomly. It does **not** independently validate negative-evidence performance or provide patient-level external validation.
- Report equal results as equal; do not claim superiority or statistical significance.

## Research novelty and related work
Phenomizer (Köhler et al., 2009; doi:10.1016/j.ajhg.2009.09.003) and LIRICAL (Robinson et al., 2020; doi:10.1016/j.ajhg.2020.06.021) predate this project. Phenotype similarity and negative evidence are not inherently novel. This project tests an interpretable observation-reliability heuristic; its novelty and usefulness remain hypotheses until demonstrated against stronger baselines.

## Limitations that must appear in the dissertation
- Disease-level HPO associations are not independent, patient-level labeled cases.
- No external patient cohort has been obtained or evaluated.
- The proposed evidence weights are heuristic and uncalibrated.
- Missingness is randomly simulated and may not resemble real clinical data collection.
- No fair head-to-head comparison with the external Phenomizer or LIRICAL implementation has yet been performed.
- Disease ranking is not equivalent to a validated diagnostic classification.
- The Streamlit app must be checked locally for usability in addition to automated tests.

## Submission readiness
A final thesis needs an approved dissertation format, a verified experimental results section, accurate citations, a reproducible environment, a limitation statement, and supervisor review. Do not fabricate clinical accuracy, novelty, or significance. Use the measured GitHub Actions artifacts for all figures.
