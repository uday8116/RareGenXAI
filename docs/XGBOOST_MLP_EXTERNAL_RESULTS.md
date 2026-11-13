# Verified XGBoost and MLP external RareBench results

## Provenance
- GitHub Actions run: https://github.com/uday8116/RareGenXAI/actions/runs/43492675927
- Workflow commit: `63030a4c499d0cacf316566f2c487674a1995423`
- Source: public RareBench curated cases; 178 eligible cases (LIRICAL 143, MME 11, HMS 24).
- Derived patient-case selection SHA256: `7976df1ec8159c24b5dae8db2bd3e598547ef81421acdc901f5b095938761ddd`
- All six methods evaluated on the same cases.

## Overall performance

| Method | N | Top-1 | Top-5 | MRR |
|---|---:|---:|---:|---:|
| Exact overlap | 178 | 37.64% | 54.49% | 0.4529 |
| XGBoost | 178 | 32.58% | 47.75% | 0.3987 |
| Random Forest | 178 | 32.58% | 40.45% | 0.3759 |
| TF-IDF | 178 | 30.34% | 43.26% | 0.3662 |
| MLP | 178 | 28.65% | 44.38% | 0.3633 |
| Logistic Regression | 178 | 27.53% | 46.07% | 0.3659 |

Disease profile coverage: 177/178 (99.44%). XGBoost improves Top-5 and MRR over the other evaluated ML rerankers, but not over exact overlap. No confidence intervals or paired significance tests are reported here.

## Interpretation and limits
- XGBoost and MLP were trained on synthetic disease-profile examples, not patient-level clinical training data.
- External cases are curated retrospective cases and may overlap disease-annotation literature.
- The top-40 TF-IDF candidate retrieval stage limits reranker performance.
- Ranking scores are not calibrated clinical probabilities.
- Do not claim prospective clinical validation, superiority to DeepRare, or statistical significance.
- The graph construction module is preparatory work; no GNN training or external GNN result exists.

## Next research tasks
1. Analyze per-cohort XGBoost and MLP errors, especially HMS.
2. Add paired bootstrap confidence intervals and retrieval-recall diagnostics.
3. Compare an HPO-aware graph model under matched experimental conditions.
