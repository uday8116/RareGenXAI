# External patient-case evaluation protocol

## Dataset
Published RareBench public test cohorts: LIRICAL, MME, HMS.
Source: https://huggingface.co/datasets/chenxz/RareBench
Reference: Chen et al., RareBench (2024), arXiv:2402.06341.
DeepRare also used RareBench, so this is **not a benchmark independent of DeepRare**; it is an external patient-case benchmark relative to our synthetic HPO training.

## Reproduce
```bash
python -m src.data
python -m src.train_ml --train-diseases 200 --test-diseases 60 --queries-per-disease 2
python -m src.rarebench --limit-per-subset 30
python -m src.evaluate_external --cases data/external/rarebench_cases.csv --methods tfidf logistic random_forest overlap
```
The dedicated GitHub Actions workflow `External RareBench Patient Evaluation` executes these commands and uploads CSV results and a dataset provenance manifest. The downloader keeps the first 30 public test records per cohort (up to 90 raw records), then excludes cases with fewer than 3 valid HPO IDs or multiple diagnoses. It does not cherry-pick on ranking outcomes.

## Report metrics responsibly
Report per method: sample size, Top-1, Top-5, MRR, and disease-ID coverage. Unmatched disease IDs are counted as failures, not silently excluded. ML retrieval is limited to its top 40 candidates, so the rank can be absent even for a known disease. Models are not calibrated clinical predictors. The ontology methods can rank the full HPO disease universe, but they are slower.

## Important limitations
- Patient cases were curated by external groups, but disease profiles come from public HPO annotations, which can include evidence from the same literature. Annotation leakage or publication overlap cannot be ruled out.
- ML models train on synthetic queries from the HPO knowledge base; patient cases are used only for external evaluation.
- RareBench disease identifiers may differ from HPO profile IDs (for example, OMIM vs ORPHA vs ORPHANET). The audit must report coverage and identifier mapping before interpreting accuracy.
- Public patient benchmarks are not equivalent to prospective, independent hospital validation.
- This workflow does not run DeepRare itself. A matched head-to-head comparison requires DeepRare outputs for the same cases, same identifier normalization and evaluation policy.
- Cite the original dataset and review its terms before redistribution. Patient-level CSVs are generated as workflow artifacts, not committed to Git.
- The result CSV should be checked for empty subsets, valid identifiers, missing diagnoses and unexpectedly low coverage.

## Evidence standard
Do not write any numerical clinical performance result in the dissertation until the workflow succeeds and the uploaded CSV is inspected. Do not report synthetic results as patient-level results.
