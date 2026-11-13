# VERIFIED full RareBench patient-case benchmark

## Execution and provenance
- GitHub Actions run: https://github.com/uday8116/RareGenXAI/actions/runs/43485509434
- Run conclusion: **success**, verified from GitHub workflow and logs.
- Commit: 527135707718079e75a0cc448626d002eca6b37a
- Public RareBench LIRICAL, MME and HMS original cohorts; all rows inspected.
- Eligibility: at least three valid HPO terms and exactly one diagnosis; no selection by model accuracy.
- Eligible total **178**: LIRICAL **143**, MME **11**, HMS **24**.
- Disease-ID coverage: **177/178 = 99.44%**.
- Derived case CSV SHA-256: `7976df1ec8159c24b5dae8db2bd3e598547ef81421acdc901f5b095938761ddd`.
- Patient-level results and cohort summary: download `external-patient-benchmark` artifact from the linked GitHub run.

## Overall metrics (178 cases)
| Method | Top-1 | Top-5 | MRR |
|---|---:|---:|---:|
| Exact overlap | 37.64% | 54.49% | 0.4529 |
| Random Forest | 32.58% | 40.45% | 0.3759 |
| TF-IDF | 30.34% | 43.26% | 0.3662 |
| Logistic Regression | 27.53% | 46.07% | 0.3659 |

## Cohort-specific Top-1 / Top-5 / MRR
| Cohort | N | Method | Top-1 | Top-5 | MRR |
|---|---:|---|---:|---:|---:|
| LIRICAL | 143 | Exact overlap | 41.26% | 59.44% | 0.4939 |
| LIRICAL | 143 | Random Forest | 35.66% | 44.06% | 0.4094 |
| LIRICAL | 143 | TF-IDF | 32.87% | 46.15% | 0.3935 |
| LIRICAL | 143 | Logistic Regression | 28.67% | 47.55% | 0.3808 |
| MME | 11 | Exact overlap | 72.73% | 90.91% | 0.8032 |
| MME | 11 | Random Forest | 63.64% | 81.82% | 0.7321 |
| MME | 11 | TF-IDF | 54.55% | 81.82% | 0.6732 |
| MME | 11 | Logistic Regression | 63.64% | 81.82% | 0.7197 |
| HMS | 24 | Exact overlap | 0.00% | 8.33% | 0.0480 |
| HMS | 24 | Random Forest | 0.00% | 0.00% | 0.0132 |
| HMS | 24 | TF-IDF | 4.17% | 8.33% | 0.0627 |
| HMS | 24 | Logistic Regression | 4.17% | 20.83% | 0.1148 |

## Interpretation
Exact overlap led on overall Top-1, Top-5, and MRR. ML reranking did not beat this baseline in the full external benchmark. HMS performance was notably weak across all methods and deserves error analysis. Cohort sizes differ substantially; overall results are dominated by LIRICAL.

## Limitations
These are retrospectively curated external cases, **not prospective hospital validation**. The ranking knowledge base uses public HPO disease annotations that may overlap published cases. No DeepRare predictions were run on the same cases. The ML models were trained on synthetic HPO-derived observations. Dataset eligibility filtering excluded cases with fewer than three HPO terms or ambiguous/multiple diagnosis fields. No confidence intervals or statistical significance testing were conducted. The run did not include the ontology-semantic baseline because of compute cost.

## Reproduction
```bash
python -m src.data
python -m src.train_ml --train-diseases 200 --test-diseases 60 --queries-per-disease 2
python -m src.rarebench --limit-per-subset 100000
python -m src.evaluate_external --cases data/external/rarebench_cases.csv --methods tfidf logistic random_forest overlap
```
