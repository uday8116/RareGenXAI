# Phase 6 — Explainable HPO evidence and same-case model comparison

**Project:** RareGenXAI: Explainable AI-Based Rare Genetic Disorder Classification using HPO.
**Target:** Apple M5, 16 GB unified memory; local only.
**GitHub dependency:** Phase 6 is stacked on the Phase 5 development branch while Phase 5 PR #9 is still awaiting CI/build acceptance. Phase 4 security review PR #8 is also not merged. Phase 6 does **not** silently merge either open PR.

## Goal and implementation plan

Phase 6 makes the model output more understandable and scientifically cautious. It cannot transform synthetic-training ranking outputs into validated medical diagnoses.

| ID | Goal | Delivered |
| --- | --- | --- |
| 6.1 | Trace individual HPO evidence for a candidate | \`src/explainability.py\`, typed \`POST /api/v1/explain\` |
| 6.2 | Explain exact matches and ontology-related similarity | Deterministic best disease HPO term and shared most informative common ancestor |
| 6.3 | Show supporting and contradicting findings separately | Signed baseline contributions; absent HPO evidence can subtract from ranking |
| 6.4 | Verify numerical explanation consistency | Reconstructed exact-overlap/semantic scores must agree with rank scores |
| 6.5 | Handle trained ML methods scientifically | Explicit ontology context only; **no fake SHAP, weights, or probabilities** |
| 6.6 | Compare algorithms using the exact same input | Phase 6 model comparison in the Phenotype Workbench, real repeated API inference |
| 6.7 | Evaluate evidence sensitivity | One HPO observation removed and same method re-run; guarded against removing last positive |
| 6.8 | Make frontend responsive and usable | Phase 6 tabs, candidate selector, score bars, accessible comparison tables, compact mobile layout |
| 6.9 | Add backend/front end tests | 7 offline Python test functions, API tests, 9 Node logic cases, React integration tests |
| 6.10 | Add verification and handover | This guide, dedicated Phase 6 CI and local setup instructions |

## Scientific background

The Human Phenotype Ontology (HPO) organizes phenotype terms into an is-a graph. A disease may be annotated with one term, while a user's observation is a related descendant or sibling term. The ontology similarity uses the **most informative common ancestor (MICA)**:

    sim(a,b) = IC(MICA(a,b)) / max(IC(a), IC(b), 1e-9)

The information-content (IC) dictionary is estimated from the local disease-phenotype knowledge base, not from a new patient cohort. Ties among equivalent disease HPO terms and shared ancestors are resolved lexicographically to give deterministic outputs.

The overlap method gives an exact HPO match of 1 and a nonmatch of 0. The semantic method considers the most similar annotated disease HPO term, including ontology-related matches. Evidence weights match existing \`src/ranking.py\`:

| Evidence status | Quality weight | Interpretation in research rank |
| --- | ---: | --- |
| confirmed_present | +1.0 | Positive recorded HPO evidence |
| suspected_present | +0.4 | Weaker positive recorded evidence |
| confirmed_absent | −0.6 | Penalty only when the disease phenotype matches |
| unknown | 0 | Ignored |

The baseline raw ranking score is a sum of per-phenotype signed contributions divided by the total absolute weight of considered evidence. The Phase 6 endpoint reproduces its original six-decimal rounding, so the frontend can check the contributions against the API rank score. This score is **not** a probability, prevalence estimate, genetic pathogenicity score, or diagnostic confidence.

**Important knowledge limitation:** The HPO disease profile is a knowledge-base association list, not a complete set of all possible symptoms. Absence of an association is not proof of absence of a symptom.

### Trained ML methods are different

TF-IDF, Logistic Regression, Random Forest, XGBoost and MLP use the verified Phase 3 model and selected input features. Phase 6 does **not** compute classifier-specific SHAP values or gradient attributions. The new endpoint returns only HPO annotation matches for such models, labeled \`ontology_context_not_ml_attribution\`. The frontend never turns a raw classifier output into a disease likelihood.

## Architecture and endpoints

~~~text
React Phenotype Workbench (local 127.0.0.1:5173)
      |
      | Existing /api/v1/rank
      | New /api/v1/explain
      v
FastAPI on 127.0.0.1:8000
      |
      +-- Validated official Phase 2 SQLite HPO terms / aliases
      +-- Read-only disease-phenotype annotations and ancestors
      +-- Phase 3 provenance-verified model (only if requested)
      |
      v
Signed ontology contributions OR ontology context
      |
      +-- HPO evidence trace UI
      +-- Same-case model comparison (2 to 4 methods)
      +-- Leave-one-phenotype-out sensitivity
~~~

**POST /api/v1/explain** accepts the same validated \`observations\`, \`method\` and \`quality\` as \`/rank\` plus \`disease_id\`. It checks existence of the disease, active canonical HPO terms, duplicate aliases, and verified model files when an ML method is requested.

Example:

~~~bash
curl -s -X POST http://127.0.0.1:8000/api/v1/explain \
  -H 'Content-Type: application/json' \
  -d '{
    "disease_id":"MIM:1234",
    "method":"overlap",
    "observations":[
      {"hpo_id":"HP:0001250","status":"confirmed_present"},
      {"hpo_id":"HP:0001263","status":"suspected_present"}
    ]
  }'
~~~

The disease identifier above is illustrative: a real 404 is expected if that ID is not annotated in your installed official HPO knowledge snapshot. Use a \`disease_id\` from a real \`/rank\` response.

Fields returned:

- \`disease_id\`, \`disease_name\`, \`method\`, \`model_sha256\` if relevant.
- \`explanation_type\`: \`signed_ontology_contributions\` or \`ontology_context_not_ml_attribution\`.
- Per-observation \`hpo_id\`, \`status\`, \`relation\` (exact, ontology_related, none), \`best_disease_hpo_id\`, \`shared_ancestor_hpo_id\`, \`match\`, \`evidence_weight\`, \`contribution\` (baseline only).
- \`reconstructed_baseline_score\` for overlap/semantic, \`null\` for ML methods.
- A clear non-clinical disclaimer.

The service has no patient accounts, databases of submitted observations, audit-log storage, hosted inference, or telemetry of the entered HPO vector.

## Phase 6 frontend

Open **http://127.0.0.1:5173/workbench**, choose phenotypes and run research ranking as in Phase 5. The resulting **Explainability Laboratory** has three tabs.

### 1. HPO evidence trace

Choose a candidate disease from the current ranking. The frontend asks FastAPI for its actual ontology trace. Green bars represent positive contributions and amber/coral bars negative contradictions. Related ontology terms show the closest annotated HPO term and most informative common ancestor. For baseline methods, the signed component sum is checked against the returned candidate score; a mismatch is flagged rather than silently ignored.

For trained methods, only the descriptive ontology matches are shown. No model-specific feature importance is invented.

### 2. Same-case model comparison

Choose **2–4 available methods**, then explicitly run them. Every method receives the same observation set, evidence statuses, quality setting, retrieval-shortlist limit, and result cutoff. Compare each algorithm's first candidate and raw score plus the number of matching leading candidates.

The view counts **agreement, not accuracy**. A 3/4 agreement means three algorithms select the same candidate; it does **not** mean 75% correct or 75% clinical confidence. Overlap and ML rerankers can consider different candidate universes, and their raw scores do not have comparable scales.

On an Apple M5 with 16 GB, requests run **sequentially** to avoid starting many heavy model inferences in parallel. A new input invalidates old comparisons.

### 3. What-if sensitivity

Choose one evidence term to omit. The frontend makes a new local \`/rank\` request using the **same model and settings** with only that HPO observation removed. It reports the original and new leading candidates, whether leadership changed, where the original leader appears in the new top 20, and its raw same-method score change when available.

At least one present/suspected phenotype must remain; the last one cannot be removed. Unknown observations are not offered as meaningful removals. This is **not a causal deletion attribution, genotype prediction, or clinical rule-out**. Removing evidence also changes denominator and/or candidate retrieval.

### Privacy and safety

- Uses HPO IDs and evidence statuses only; no names, ages, case notes, patient identities or DNA sequences.
- Same-origin browser requests proxied to local FastAPI; no public inference provider.
- No automatic saving of entered observations. Existing Phase 5 opt-in CSV/JSON export remains available.
- API fails closed if the official HPO knowledge database or verified trained model is missing.
- Cancellation/cleanup prevents delayed requests from appearing after input changes or component navigation.

## Local Mac M5 verification

~~~bash
git fetch origin
git switch --track origin/phase-06/explainability-case-comparison
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q tests/test_explainability.py tests/test_api.py

cd frontend
npm run test:logic
npm install
npm run test
npm run build
~~~

Then, in separate terminals from the repository root:

~~~bash
bash scripts/start_api.sh
bash scripts/start_frontend.sh
python scripts/smoke_phase5.py
~~~

The smoke script checks the existing Phase 5 path. Manually check that \`/api/v1/explain\` returns actual ontology matches and that all three Phase 6 tabs work on the browser. The \`/docs\` page should now include the new endpoint.

## What was actually verified during implementation

- **7/7 Python core explanation tests passed** in a local Python 3.11+ runtime using byte-identical copies of \`src/ranking.py\`, \`src/explainability.py\`, and \`tests/test_explainability.py\`. The files' local Git blob hashes were checked against the GitHub blob SHAs. Result: 7 passed, 0.08 s.
- **9/9 JavaScript XAI tests passed** in an isolated V8 JavaScript evaluator running the exact GitHub helper and Node test case bodies with assertion equivalents.
- Phase 6 FastAPI integration tests and React component tests are **committed, not yet executed** against the real HPO service or a browser.
- Full \`npm run build\`, Vitest, end-to-end local Mac behavior, and the GitHub CI must execute successfully before acceptance.
- GitHub Actions for the prior Phase 4/5 PRs failed before runner steps began. The root cause remains unconfirmed; those failures are not passing tests, and they may affect this Phase 6 PR too.

## Completion gates

- [x] Implement real ontology evidence trace and signed rank decomposition.
- [x] Add validated local REST endpoint and read-only model provenance checks.
- [x] Implement same-case multi-model comparison and one-evidence sensitivity.
- [x] Add scientific caveats and no-fabricated-ML-attribution behavior.
- [x] Add backend and frontend test source; run targeted Python and JS core logic checks.
- [ ] Execute full FastAPI and React integration suites.
- [ ] Build and open website successfully on physical Apple M5.
- [ ] Pass CI on GitHub, or document an accepted equivalent local test outcome.
- [ ] Merge dependency Phase 5 PR #9 and then Phase 6 PR following successful verification.
- [ ] Phase 4 review PR #8 is separate; its required fixes must be reconciled before external deployment.

**Scope boundary:** This phase improves explainability of the existing research ranking engine. It does not deliver clinically validated genetic diagnosis, model-specific SHAP/Integrated Gradients, calibrated posterior probabilities, live clinical trial, or a matched DeepRare benchmark.

### Phase 6 audit note

The final helper audit added a ninth JavaScript regression test: when evidence weighting is disabled, a confirmed-absent term with zero score impact must **not** be presented as a negative score contribution. The complete **9/9** XAI helper tests were re-exercised successfully in an isolated JavaScript evaluator. Full Node/Vitest, production build, and browser validation remain pending.
