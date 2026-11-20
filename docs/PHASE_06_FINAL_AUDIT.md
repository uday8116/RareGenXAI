# Phase 6 — Independent completeness audit and implementation corrections

**Review date:** 2026-11-20  
**Repository:** uday8116/RareGenXAI  
**Development PR:** #10, phase-06/explainability-case-comparison  
**Dependency:** stacked on Phase 5 PR #9, which is still open. Phase 4 security review PR #8 remains separate.

## Conclusion

**The Phase 6 functionality is implemented, with additional safety, provenance and completeness fixes committed to PR #10. It is NOT yet fully accepted or merged.** Core Python and Node logic has been tested in the current environment, but GitHub Actions jobs are failing before their first step, the full React suite/build has not executed, and the actual Apple M5 browser demo remains outstanding.

This review does not certify clinical diagnosis, probability calibration, model-specific SHAP attributions, or matched-case DeepRare results.

## Scope review

| Requirement | Implemented in repository | Acceptance |
| --- | --- | --- |
| Signed exact HPO overlap contributions | src/explainability.py and POST /api/v1/explain | 7 pure Python tests pass |
| Semantic HPO relatedness and shared ancestor | Ontology IC/MICA trace | Pure Python tests pass |
| Clinical-only HPO validation | Shared rank/explain validation of descendants of HP:0000118 | Regression tests authored |
| Safe SQLite read errors | HTTP 503 on a mid-request read failure | Regression tests authored |
| Provenance-bound response | Knowledge source manifest SHA-256 + verified ML artifact SHA-256 | API/JS regression tests authored |
| Stale/incorrect explanation prevention | Candidate, method, explanation-kind, score and fingerprint checks | 13 native Node logic tests pass |
| Same-case model comparison | Sequential local /rank across 2–4 methods | JS logic tests pass; React integration pending |
| Leave-one-out sensitivity | Bounded same-method inference, retains last positive phenotype | JS logic tests pass; React integration pending |
| No fictitious ML SHAP/diagnostic probabilities | ML trace clearly labeled ontology context only | Python and JS tests pass |
| Responsive frontend | Phase 6 ExplainabilityLab React panels | Source committed; browser build pending |
| Official HPO + real saved-model proof | tests/test_phase6_integration.py | Strict full test authored; execution requires prepared data/model |
| All-in-one M5 acceptance script | scripts/verify_phase6.sh | Quick/full commands committed; full execution pending |
| CI on GitHub | .github/workflows/phase6-explainability.yml | BLOCKED before any runner steps execute |
| Final merge | PR #10 against Phase 5 branch | Intentionally pending acceptance |

## Specific defects fixed by review

1. **Nonclinical HPO terms:** Both \`/rank\` and \`/explain\` now reject the HPO root, HP:0000118 category heading, inheritance terms, and other non-descendants of clinical phenotypic abnormality HP:0000118. Source HPO alias canonicalization still works.
2. **Transient SQLite failures:** Mid-request read or database replacement errors are returned as explicit HTTP 503 without leaking stack traces or producing false results.
3. **Incorrect explanation binding:** The frontend refuses an explanation for a different disease, method, explanation kind, or verified model artifact.
4. **Mismatched score composition:** A malformed/missing contribution or a baseline score inconsistent with its ranked result now **hides** the evidence trace, rather than merely showing a warning beside untrusted bars.
5. **Model fingerprint drift:** A mixed-model comparison and one-phenotype-out rerun detect ML artifact changes and stop, instead of comparing outputs from incompatible trained bundles.
6. **HPO source provenance drift:** A deterministic SHA-256 of the validated **source manifest metadata + DB schema version + row counts** now accompanies both ranking and explanation. The UI rejects different fingerprints between related calls. This is a metadata fingerprint, **not** a hash of all database bytes and not proof of clinical validity.
7. **Database cache invalidation:** The cached knowledge/model file signature now includes device, inode, ctime, mtime and size, detecting atomic file replacement even when file mtime and size are preserved.
8. **Strict full integration:** A new test uses official clinical HPO annotations and the trained artifact, verifies 7 methods, explanation response consistency and non-fabricated ML attributions. A missing model or DB makes **full verification fail**, not skip.

## Tests actually run

### Passed

- The original seven Phase 6 Python core tests in \`tests/test_explainability.py\` were executed on byte-identical GitHub copies of \`src/ranking.py\`, \`src/explainability.py\` and the test file: **7 passed, 0 failed**.
- The complete extended \`frontend/tests/xai.logic.test.mjs\` file was executed using the actual Node.js 22 test runner with byte-identical copies of the latest GitHub XAI source and test files: **13 passed, 0 failed**.
  - Git blob SHA-1 of \`frontend/src/xai.js\`: \`70bb18b7d9c886890b6d93f0abd532cb40788da4\`.
  - Git blob SHA-1 of \`frontend/tests/xai.logic.test.mjs\`: \`5be0065ecab0076ab7a37a8dd30dd337c9f3b41e\`.
  - Checks include score-sign interpretation, missing/invalid explanations, model identity, source-fingerprint consistency, agreement honesty and safe ablation.

### Authored, not yet executed

- Additional \`tests/test_api.py\` regression tests for clinical HPO validation, 503 behavior, matching HPO manifest fingerprints and atomic cache replacement.
- \`tests/test_phase6_integration.py\` with the real official HPO knowledge base and trusted saved-model bundle for all seven methods.
- React Testing Library/Vitest tests in \`frontend/src/__tests__/App.test.jsx\`, including the real API client mock paths for all Phase 6 tabs.
- Production \`npm run build\` and manual Apple M5 browser interaction.

Do not describe the tests in this section as passed merely because the files exist.

## Exact local acceptance steps

From the repository root:

~~~bash
git fetch origin
git switch phase-06/explainability-case-comparison
git pull --ff-only origin phase-06/explainability-case-comparison
source .venv/bin/activate

# Quick API tests and dependency-free Node safeguards:
bash scripts/verify_phase6.sh --quick

# Install React test and build dependencies:
cd frontend
npm install
cd ..

# Full STRICT check: must have the official DB and verified ML weights.
bash scripts/verify_phase6.sh --full
~~~

If full verification fails due to missing official data/model, prepare the Phase 2/3 artifacts according to \`docs/PHASE_04_BACKEND.md\`, then retry. Do not create mock data to satisfy the strict test.

In separate terminals from the repo root:

~~~bash
bash scripts/start_api.sh
bash scripts/start_frontend.sh
~~~

Then:

~~~bash
python scripts/smoke_phase5.py
~~~

Open \`http://127.0.0.1:5173/workbench\` and manually verify that the HPO evidence trace, same-case model comparison and one-phenotype sensitivity all work. Also check local API disconnection/error states and invalid clinical HPO findings. Avoid identifiable patient data.

## CI blocker

Latest checked Phase 6 Actions run on the review branch: https://github.com/uday8116/RareGenXAI/actions/runs/44741322436 .

The Phase 6 workflow has both an Ubuntu Python API job and an Ubuntu Node.js job, but GitHub marks both failed **before executing any steps** (job \`steps=[]\`, runner ID 0). The same behavior affects unchanged foundation/full-project and Phase 5 workflows. The cause is not determined; possible Actions usage/billing or runner/account problems must be checked via GitHub's run Annotations and account/repo Actions settings. This is not evidence of a Python or React test failure.

**Do not merge PR #10 until integration checks pass and the stacked Phase 5 dependency is reconciled.** The Phase 5 dependency also has a package-lock reproducibility gap: commit a verified npm lockfile and use \`npm ci\` after it can be generated in an environment with registry access.

## Research limits and future work

The Phase 6 model comparison presents *agreement*, not ground-truth accuracy. Models may use different candidate universes and score scales. The what-if analysis measures model response to evidence removal, not causal phenotype influence. Trained ML output is descriptive ontology context, not genuine SHAP, attribution to weights, or calibrated risk. Independent clinical validation, full DeepRare matched-case comparison, medically reviewed explanations, and public deployment are outside this phase.

**Status: code improvements delivered; acceptance gated by real integration, React production build and physical M5 checks.**

## Audit closeout update

The review also added two explicit React interaction tests in `frontend/src/__tests__/App.test.jsx`: one verifies a mismatched candidate/method explanation is hidden, and one verifies a numerically inconsistent baseline trace is hidden. Their **test code is committed**, but they have **not executed** because the React dependencies/build are unavailable in this review environment and GitHub Actions remains blocked.

The full official-data integration test selects a true descendant of the clinical HPO root via a recursive parent query. It checks seven available ranking methods and per-method explain responses from the same source manifest, while the strict environment flag `RAREGEN_REQUIRE_PHASE6_INTEGRATION=1` prevents a missing source/model from being reported as success.

The final native **Node 22: 13/13** and core **Python pytest: 7/7** checks were rerun and passed. These are the specific verified test sets; neither result proves the full API integration or React production build succeeded.

The Phase 6 GitHub workflow now also runs `bash -n scripts/verify_phase6.sh` when an Actions runner becomes available. The latest successful code review does not bypass the mandatory Mac/browser and CI acceptance gates.

## Continuation review — additional correctness fixes (20 November 2026)

The continuation audit identified three additional gaps and committed regression tests:

1. **Database replacement within a request.** HPO canonicalization opens a separate SQLite read connection after the cached ontology context was loaded. An atomic replacement between those steps could have mixed old profile/ontology data with newly resolved HPO aliases. `ResearchService.context()` now keeps the identity of its validated DB file. Both `/rank` and `/explain` check that identity before and after canonicalization and again before returning results; a changed file causes HTTP 503. Two synthetic FastAPI tests deliberately replace the database during validation and verify rejection.
2. **Same-case comparison output limit.** Phase 6 previously enlarged the comparison request's `top_k` to at least five, making it differ from the original workbench setting. Comparison now uses the same observations, HPO statuses, quality, candidates and `top_k` for all methods. React test assertions cover the consistent settings. The sensitivity tool intentionally requests up to 20 candidates when tracing the original leader's post-ablation position; this exception is explicitly different from the method-comparison test.
3. **Strict official integration in project CI.** After the full-project workflow downloads official HPO data and builds the verified Phase 3 model, it now executes `RAREGEN_REQUIRE_PHASE6_INTEGRATION=1 python -m pytest -q tests/test_phase6_integration.py`. This cannot silently skip if data/model preparation failed, unlike early pre-data unit test collection.

Two additional React regression cases check that changed HPO-source fingerprints invalidate returned explanation evidence and terminate cross-model comparisons; these tests have been committed but **not yet executed** by Vitest.

**Verification distinctions remain unchanged:** original offline Python core tests **7/7 passed** and extended native Node 22 XAI tests **13/13 passed** before this continuation. Changes made during this continuation primarily affect Python API integration and React components; their full execution has **not yet been independently verified**. GitHub Actions remains blocked before worker steps start, and the physical M5 end-to-end review remains required.

Latest CI actions status and PR base can be checked at https://github.com/uday8116/RareGenXAI/pull/10 . Do not merge into `main` without resolving the Phase 5 dependency and passing complete integration/build verification.
