# RareGenXAI — final project report (research prototype)

## Abstract
RareGenXAI is an explainable rare genetic disorder prioritization prototype using clinical phenotypes expressed as Human Phenotype Ontology (HPO) identifiers. The pipeline constructs disease–phenotype profiles from official HPO annotations and ranks candidate disorders with exact phenotype overlap, semantic similarity, TF-IDF retrieval and experimental Logistic Regression and Random Forest rerankers. The Streamlit interface shows ranked candidates and evidence-based explanations. Evaluation on all 178 eligible cases from three public RareBench cohorts found that the simple exact-overlap baseline outperformed the tested ML approaches overall. These findings support a transparent phenotype-driven decision-support research prototype, not a clinically validated diagnostic device.

## Objectives and scope
1. Ingest and normalize public HPO ontology and disease annotations.
2. Implement interpretable disease ranking and compare conventional and ML baselines.
3. Provide an interactive application and reproducible testing workflow.
4. Assess generalization on externally sourced patient cases and report limitations without overstating results.

## Architecture
**Input:** HPO phenotype IDs with optional evidence-quality labels.

**Knowledge preparation:** Download official `hp.obo` and `phenotype.hpoa`; parse ontology and build disease phenotype profiles; record SHA-256 provenance.

**Ranking:** Exact overlap, ontology-aware semantic similarity, TF-IDF, Logistic Regression and Random Forest. The ML approaches are trained on synthetic phenotype queries derived from disease profiles, not hospital records.

**Explanations:** Per-phenotype contributions for candidate ranking, with illustrative evidence weights. Scores are not disease probabilities.

**Interface:** Streamlit app (`app.py`) for phenotype input, ranking, and result exploration.

**Reproducibility:** GitHub Actions automated tests, model training, benchmark evaluation and artifact upload.

## Dataset and methodology
External evaluation uses the public RareBench LIRICAL, MME and HMS cohorts. The full available source cohorts were examined; cases were eligible when they contained at least three valid HPO identifiers and one unambiguous disease label. Eligible cases: LIRICAL 143, MME 11, HMS 24; **178 in total**. Ground-truth disease was represented using the source identifier. The evaluation records Top-1, Top-5, mean reciprocal rank (MRR), and whether the true disease is covered by the knowledge base. The benchmark was retrospective and externally sourced; overlap with HPO annotation literature cannot be excluded.

**Verified GitHub run:** https://github.com/uday8116/RareGenXAI/actions/runs/43485509434

## Overall external patient results
| Method | Top-1 | Top-5 | MRR |
|---|---:|---:|---:|
| Exact phenotype overlap | **37.64%** | **54.49%** | **0.4529** |
| Random Forest | 32.58% | 40.45% | 0.3759 |
| TF-IDF | 30.34% | 43.26% | 0.3662 |
| Logistic Regression | 27.53% | 46.07% | 0.3659 |

Disease coverage was 177/178 (99.44%).

## Cohort-specific results
| Cohort | N | Method | Top-1 | Top-5 | MRR |
|---|---:|---|---:|---:|---:|
| LIRICAL | 143 | Overlap | 41.26% | 59.44% | 0.4939 |
| LIRICAL | 143 | Random Forest | 35.66% | 44.06% | 0.4094 |
| LIRICAL | 143 | TF-IDF | 32.87% | 46.15% | 0.3935 |
| LIRICAL | 143 | Logistic Regression | 28.67% | 47.55% | 0.3808 |
| MME | 11 | Overlap | 72.73% | 90.91% | 0.8032 |
| MME | 11 | Random Forest | 63.64% | 81.82% | 0.7321 |
| MME | 11 | TF-IDF | 54.55% | 81.82% | 0.6732 |
| MME | 11 | Logistic Regression | 63.64% | 81.82% | 0.7197 |
| HMS | 24 | Overlap | 0.00% | 8.33% | 0.0480 |
| HMS | 24 | Random Forest | 0.00% | 0.00% | 0.0132 |
| HMS | 24 | TF-IDF | 4.17% | 8.33% | 0.0627 |
| HMS | 24 | Logistic Regression | 4.17% | 20.83% | 0.1148 |

## Discussion
The transparent exact-overlap baseline achieved the best overall Top-1, Top-5 and MRR. Thus, the experiment does **not** show that adding ML improves disease ranking. Performance varies markedly by cohort: HMS was particularly challenging. The combined result is strongly influenced by LIRICAL, which accounts for 143/178 cases. Differences in phenotype representation, case complexity and annotation coverage may contribute, but were not isolated experimentally. A larger matched-case analysis is needed before making causal explanations.

## Relation to DeepRare
DeepRare is a published rare-disease reasoning approach, but its published RareBench cohort-level figures cannot be treated as a head-to-head comparison with these filtered 178 cases. A matched comparison requires DeepRare predictions for the identical case IDs, input modalities, and disease identifier normalization. These predictions are **not available in this project**. The evaluator supports an optional genuine DeepRare predictions CSV; see `docs/DEEPRARE_MATCHED_COMPARISON.md`. Do not claim RareGenXAI beats DeepRare.

## Limitations and ethics
- External published cases do not imply prospective clinical validation or patient independence from all annotation literature.
- Synthetic training and curated patient-case testing are not equivalent to real-world deployment.
- No DeepRare matched-case comparison, statistical significance test, uncertainty calibration or clinical utility study was performed.
- Case filtering excludes records without adequate structured HPO features or a single diagnosis.
- The semantic method and evidence-quality variant were implemented but not included in this CPU-friendly external benchmark run.
- Predictions are candidate rankings, not diagnoses or calibrated probabilities.
- The interface must not collect identifiable patient data for a public demo.

## Conclusion
RareGenXAI meets its prototype goals: ontology-based disease ranking, explainable evidence contributions, an interactive app, reproducible model baselines and an independently sourced retrospective patient benchmark. The best-performing evaluated approach was exact phenotype overlap. Further work should investigate HMS failures, test alternative training strategies, evaluate ontology-semantic methods on the same cases, and obtain matched DeepRare predictions and ethically governed prospective clinical data.

## References and evidence
- Human Phenotype Ontology: https://hpo.jax.org/
- HPO ontology and annotations: https://github.com/obophenotype/human-phenotype-ontology
- DeepRare: https://www.nature.com/articles/s41586-025-10097-9
- RareBench: https://huggingface.co/datasets/chenxz/RareBench
- Reproducible benchmark: https://github.com/uday8116/RareGenXAI/actions/runs/43485509434
- Exact per-cohort results: `docs/VERIFIED_EXTERNAL_RESULTS.md`
- Deployment instructions: `docs/WEB_DEPLOYMENT.md`

## Submission notes
This is the technical content for a final report, **not** an institution-approved dissertation layout. Add student details, supervisor approval, university cover page, declaration, certificates, bibliography formatting, screenshots and any mandatory chapter structure according to the university template. A public deployment URL has not been verified.
