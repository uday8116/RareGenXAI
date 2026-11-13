# Full 178-case experimental HPO GNN benchmark

## Verified execution
- GitHub Actions run: https://github.com/uday8116/RareGenXAI/actions/runs/43494419924
- Workflow commit: `c917c3eb8e5361a914e8f48223368d0c0e5870b8`
- All workflow steps passed, including three PyTorch GNN tests and the full external evaluation.
- Results artifact: https://github.com/uday8116/RareGenXAI/actions/runs/43494419924/artifacts/14070394059
- RareBench eligible external cases: 178.
- GNN configuration: 100 training diseases, 200 synthetic training queries, 3 epochs, TF-IDF top-40 candidate shortlist.

## External comparison (same 178 RareBench cases)

| Method | Top-1 | Top-5 | MRR |
|---|---:|---:|---:|
| Exact phenotype overlap | **37.64%** | **54.49%** | **0.4529** |
| XGBoost | 32.58% | 47.75% | 0.3987 |
| Random Forest | 32.58% | 40.45% | 0.3759 |
| TF-IDF | 30.34% | 43.26% | 0.3662 |
| MLP | 28.65% | 44.38% | 0.3633 |
| Logistic Regression | 27.53% | 46.07% | 0.3659 |
| Experimental HPO GNN | 18.54% | 41.01% | 0.2819 |

GNN Top-1 is 19.10 percentage points below exact overlap; GNN Top-5 is 13.48 percentage points below overlap. These are descriptive comparisons, **not** paired significance tests.

## Scientific interpretation
- The GNN is implemented, trained, tested and evaluated on external cases; this does not establish superiority.
- GNN and other models use different training configurations. Treat comparisons as preliminary.
- All methods operate with a shared disease annotation knowledge base; patient cases may overlap the literature behind disease profiles.
- The GNN reranks a TF-IDF top-40 candidate shortlist; diagnoses not retrieved cannot be recovered.
- Training uses synthetic disease annotations, not clinical patient training data.
- Results are retrospective ranking metrics, not prospective clinical diagnostic accuracy.
- Next experiments: same-case paired uncertainty intervals including GNN, multiple seeds, hyperparameter tuning on disjoint validation sets, and ontology-edge ablation.
