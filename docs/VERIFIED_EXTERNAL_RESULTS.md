# VERIFIED external patient-case benchmark — initial pilot

## Source and execution
- Dataset: RareBench public LIRICAL, MME, HMS cohorts, original published archive.
- Workflow: https://github.com/uday8116/RareGenXAI/actions/runs/43485166485
- Commit: 4e1add8bb64db7db5e815d27b89bdd3a10778580
- Status: completed successfully, including data download, conversion, training, evaluation and artifact upload.
- Source CSV SHA-256: 54aa12aaee42a7b68b6e7ad84a6b25b44142babeecc21b41061a2d165a00532a
- Sampling: first 30 rows of each cohort, then eligibility filter (at least three valid HPO IDs and exactly one diagnosis). **This is a pilot, not the full benchmark.**
- Cohort eligible counts: LIRICAL 8/30, MME 9/30, HMS 8/30, total 25/90.
- All 25 recorded disease IDs were found in the disease knowledge base (coverage 100%).

## Results (n=25 for each method)
| Method | Top-1 | Top-5 | MRR | Disease coverage |
|---|---:|---:|---:|---:|
| Logistic Regression | 36% | 52% | 0.4252 | 100% |
| Random Forest | 36% | 48% | 0.4155 | 100% |
| Exact phenotype overlap | 36% | 52% | 0.4313 | 100% |
| TF-IDF | 28% | 52% | 0.3870 | 100% |

These figures are transcribed from the successful workflow logs. Download the patient-level CSV from the workflow artifact to audit each rank and subgroup.

## Interpretation
On this small pilot, Logistic Regression and Exact Overlap tied at Top-1 and Top-5. Exact Overlap had the highest MRR. The results **do not establish** that ML outperforms the simpler baseline.

## Research limitations
- Cases are externally sourced but disease knowledge is built from HPO annotations, which may contain overlapping publications.
- Synthetic HPO disease-profile queries were used for model training. These external cases were not used to fit the models in this run.
- The 25 cases were filtered by available phenotype and diagnosis fields; findings may not generalize to excluded cases.
- Small sample, no confidence intervals, no cross-cohort or independent hospital validation.
- This run did not compare with DeepRare on matched cases.
- The raw source archive was downloaded and a SHA-256 was recorded for the derived CSV; data licensing must be reviewed before public redistribution.
- Do not call these results prospective clinical validation.

## Reproduce
```bash
python -m src.data
python -m src.train_ml --train-diseases 200 --test-diseases 60 --queries-per-disease 2
python -m src.rarebench --limit-per-subset 30
python -m src.evaluate_external --cases data/external/rarebench_cases.csv --methods tfidf logistic random_forest overlap
```
