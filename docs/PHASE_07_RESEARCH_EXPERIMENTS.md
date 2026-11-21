# Phase 7 — Reproducible External Research Experiments

**Project:** RareGenXAI M.Tech candidate-disease ranking prototype  
**Scope:** Retrospective, published RareBench cases; NOT clinical diagnosis.  
**Hardware:** Local Apple M5/16 GB or verified GitHub Action.

## Goals and delivered implementation

| Requirement | Implementation | Evidence |
| --- | --- | --- |
| External case selection and source integrity | `src.rarebench`, pre-evaluation source hashes | Dataset/case SHA-256 checks |
| Freeze case list, model, methods and retrieval limits before observing results | `src.phase7_experiments freeze` | Refuses to overwrite existing plan |
| Exact same cases across methods and cohorts | `audit` | Complete case × method matrix checks |
| Top-1, Top-5, MRR and candidate-list recall | Independent audit of raw ranks | No invented/missing results |
| Disease-universe coverage and error reasons | Cohort table and error breakdown | Full denominator, no cherry-picking |
| Per-cohort confidence intervals | Seeded case-level percentile bootstrap | Reproducible 95% exploratory intervals |
| Fair matched-case comparisons | Paired differences versus overlap | Identical case IDs, fixed cohort membership |
| Dataset/model and output provenance | Frozen JSON plan and audit JSON | SHA-256 of cases/model/outputs |
| Reproducible full evaluation | `scripts/verify_phase7.sh`, GitHub CI | Real-run acceptance pending |
| Automated code correctness | `tests/test_phase7_experiments.py` | **22/22 tests passed locally** |

## Data provenance and scientific scope

Published [RareBench](https://huggingface.co/datasets/chenxz/RareBench) test cohorts: LIRICAL, MME and HMS. The downloader retains public source order without selecting cases by model result; it excludes records with fewer than three HPO terms or multiple diagnoses. Do not redistribute material without reviewing dataset terms.

An earlier **verified historical** GitHub workflow [run 43485509434](https://github.com/uday8116/RareGenXAI/actions/runs/43485509434) evaluated 178 eligible RareBench cases (143 LIRICAL, 11 MME, 24 HMS). That run is a **different earlier code/model/HPO snapshot** and is NOT a newly executed Phase 7 run. Changing HPO PURLs may change downloaded annotation contents.

These are retrospective published records, NOT independent prospective hospital patients. Disease HPO associations can overlap the same literature used to curate RareBench cases. We cannot guarantee absence of publication/annotation leakage. The models train on **synthetic disease-HPO queries**, not supervised clinical patient training examples.

No authentic same-case DeepRare predictions have been obtained; the new pre-registration tool rejects `DeepRare_external` until the source and case alignment can be established. Do not substitute published aggregate DeepRare percentages. See [matched DeepRare protocol](DEEPRARE_MATCHED_COMPARISON.md).

## Run it locally on your Mac

Check out `phase-07/reproducible-external-evaluation`, activate the Python virtual environment, then run:

~~~bash
bash scripts/verify_phase7.sh --quick
~~~

This runs the synthetic-fixture auditor tests. It **does not evaluate any patient cases**.

If the required official sources and model are not yet prepared, consult Phases 2–3. To prepare a new snapshot, after backing up any existing local database and model artifacts:

~~~bash
python -m src.data
python -m src.knowledge_db build --replace
python -m src.knowledge_db verify --raw-dir data/raw
python -m src.train_ml --seed 42 --train-diseases 600 --test-diseases 120 --queries-per-disease 2 --candidates 40
python -m src.verify_models --raw-dir data/raw
python -m src.rarebench --limit-per-subset 100000
~~~

The source links can change, so new results must cite the new source and model hashes.

To run the **real**, full Phase 7 experiment:

~~~bash
bash scripts/verify_phase7.sh --full
~~~

This fails if official HPO, real RareBench, source manifests, or the verified model are missing. It also **refuses to overwrite** `results/phase7_plan.json`, because the protocol is frozen before rankings are observed. Archive a previous plan and outputs before starting a new experiment.

### Equivalent manual procedure

~~~bash
# Freeze the input case IDs, published source, verified model and methods.
python -m src.phase7_experiments freeze \
  --cases data/external/rarebench_cases.csv \
  --dataset-manifest data/external/rarebench_manifest.json \
  --model-manifest models/raregen_ml.manifest.json \
  --model models/raregen_ml.joblib \
  --methods tfidf logistic random_forest xgboost mlp overlap \
  --retrieval-k 40 --seed 42 --out results/phase7_plan.json

# Inference over the frozen public cases (no selection by outcomes).
python -m src.evaluate_external \
  --cases data/external/rarebench_cases.csv \
  --model models/raregen_ml.joblib \
  --methods tfidf logistic random_forest xgboost mlp overlap \
  --retrieval-k 40 --out results/external_case_results.csv

# Independent metrics audit, cohort CIs and paired comparison.
python -m src.phase7_experiments audit \
  --cases data/external/rarebench_cases.csv \
  --dataset-manifest data/external/rarebench_manifest.json \
  --model-manifest models/raregen_ml.manifest.json \
  --model models/raregen_ml.joblib \
  --plan results/phase7_plan.json \
  --results results/external_case_results.csv \
  --legacy-summary results/external_cohort_summary.csv \
  --replicates 2000 --out-dir results
~~~

The workflow creates the protocol **before** running inference, but it is not independently timestamped or cryptographically signed by an external registrar. The evaluator records its actual `retrieval_k`, allowing the auditor to reject changed candidate limits.

## Generated outputs — only after a real successful run

| File | Meaning |
| --- | --- |
| `results/phase7_plan.json` | Frozen case IDs/order, cohort counts, model and dataset hashes, method configuration |
| `results/external_case_results.csv` | Observed model/overlap rankings for the public cases |
| `results/external_cohort_summary.csv` | Original evaluator's per-cohort aggregates |
| `results/phase7_case_audit.csv` | Verified individual case/method scores with error category |
| `results/phase7_cohort_metrics.csv` | Top-1/Top-5/MRR/list-recall/coverage per cohort with 95% exploratory intervals |
| `results/phase7_paired_effects.csv` | Same-case paired delta versus exact overlap with bootstrap interval |
| `results/phase7_error_analysis.csv` | Per-cohort counts and percentages of error reasons |
| `results/phase7_provenance.json` | Dataset/model/case/plan hashes and output file SHA-256 values |
| `results/phase7_synthetic_training_overlap.csv` | Cohort counts where recorded disease IDs occur in synthetic model training/heldout groups or outside the known disease universe |

Case and model files are excluded from Git by `.gitignore`; GitHub Actions would publish them as an inspection artifact, not commit them.

## Evaluation method and limitations

For true rank r: **Top-1** = 1 if r=1 else 0; **Top-5** = 1 if 1≤r≤5; **MRR** = 1/r when present or 0 if absent; **candidate-list recall** = 1 if the true disease is anywhere in the returned ranked list; **disease coverage** = 1 if the ground-truth disease ID is in the knowledge base's disease universe. Missing ranks count as failures, never removed from the denominator.

**Important fairness limitation:** ML methods rank the top 40 TF-IDF retrieval candidates, while the overlap baseline searches the entire HPO disease universe. Candidate-list recall therefore does **not** compare identical candidate universes, and raw ML scores are not calibrated diagnostic probabilities. The comparison is a measured difference in the full ranking *pipelines*, not an isolated reranker-only improvement.

The auditor rejects malformed/duplicate/missing case×method rows, wrong rank/Top-K/MRR flags, inconsistent disease coverage, cohort/diagnosis changes, tampered input/model hashes, changes to pre-registered retrieval limit, and disagreement with the evaluator's original summary. Every selected case contributes equally within its specified cohort, including cases with unmapped disease IDs.

For each cohort and method, **2,000 seeded case-resampling bootstrap replicates** produce exploratory percentile 95% intervals for Top-1, Top-5, MRR, observed candidate-list recall and disease-ID coverage. The matched-method comparison resamples **the same case IDs** and reports the signed difference from overlap. Small MME/HMS samples, repeated diagnoses and publication overlap limit inference; no statistical-significance or clinical-superiority claim is made.

Five mutually exclusive case outcome categories: `top1_hit`, `rank_2_to_5`, `rank_beyond_top5`, `truth_not_in_returned_ranked_list`, and `truth_outside_model_disease_universe`. The latter flags an ID-coverage limitation, not a known biological absence. Missing rank does not by itself prove retrieval failure.

## Checks, CI, and acceptance

**Passed:** 22 synthetic-fixture test cases in `tests/test_phase7_experiments.py` executed with Python/pytest. The tested `src/phase7_experiments.py` and test file bytes were checked against their GitHub blob hashes.

**Configured:** `.github/workflows/phase7-research.yml` runs these offline checks quickly. The updated `.github/workflows/external.yml` downloads official HPO/RareBench data, trains and verifies models, freezes the protocol **before** inference, runs the six planned methods, strictly audits complete paired results, and uploads all provenance/metrics files. The costly workflow runs on main or can be manually dispatched.

**Not yet verified:** A fresh complete official dataset/model/178-case evaluation on this Phase 7 code, actual uncertainty numbers for the new snapshot, and the owner's physical Mac run. Previous repository Actions attempts failed before any runner steps executed, so source code in CI is NOT proof those real experiments ran.

### Definition of done

- [x] Paired, preregistered, source-hashed experiment system implemented.
- [x] Complete case alignment, error breakdown, metric recomputation and bootstrap implemented.
- [x] Synthetic-fixture tests executed: 22/22 pass.
- [x] Strict workflow and reproducible Mac command committed.
- [ ] Official external-case training/evaluation job succeeds on new commit and publishes artifacts.
- [ ] Generated metrics, source hashes and paired error results are independently inspected.
- [ ] Phase 5/6 dependent PRs and full M5 acceptance checks are resolved before merge.

**Status: Research evaluation infrastructure implemented and tested; new actual retrospective cohort execution and final merge remain pending.** No new accuracy numbers or matched DeepRare outcomes are invented.

## Frozen plan tamper-proofing audit

The final review added two additional regression tests: a frozen plan with modified cohort counts fails against the real source case list, and duplicated methods in a hand-edited plan are rejected before calculating metrics. All **22/22** synthetic fixture/audit tests passed locally using byte-identical source and tests from the GitHub branch. This result does not verify actual RareBench model accuracy or imply any DeepRare predictions.

**Git fingerprints used for the local test:**

- `src/phase7_experiments.py`: `0fb2cd06377a79a0c55f218ad9c49121d02f0522`
- `tests/test_phase7_experiments.py`: `f5f04423eb0bb46c4ef7bd2933327166d0c0fe27`

The pre-evaluation plan is a workflow-controlled frozen file; without an external timestamp or signature it should not be described as independently cryptographically pre-registered.

### Disease-ID overlap with synthetic training

The auditor now checks the Phase 3 model manifest's `train_disease_ids` and `heldout_disease_ids` and reports the overlap of **ground-truth disease identifiers** with these groups for each RareBench cohort. The categories are: `synthetic_training_disease`, `synthetic_heldout_disease`, `other_model_disease_or_unrecorded_split`, and `outside_model_disease_universe`. It flags contradictory training/heldout sets. This is important for interpreting performance on diseases that were used to synthesize fitting examples.

**This is not patient-record leakage detection:** a disease identifier in training does not mean the RareBench patient's observations were seen by the supervised model. Conversely, a heldout disease identifier does not guarantee freedom from published HPO annotation leakage. The source data and training design must still be discussed in the thesis.

### Verified review update

The expanded Phase 7 pure-Python test suite includes 22 cases, including synthetic training/heldout membership reporting, ambiguous plan rejection, official-source hash tampering and paired metric integrity. **22/22 passed in local pytest** using GitHub-byte-identical auditor and test files. No new patient ranking metric was measured by those tests.
