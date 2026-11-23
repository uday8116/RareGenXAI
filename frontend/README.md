# RareGenXAI React research website

This is the Phase 5 local-only React/Vite website for the Phase 4 FastAPI research backend.

Start FastAPI in Terminal 1 from the repository root:

    bash scripts/start_api.sh

Start React in Terminal 2:

    cd frontend
    npm install
    npm run dev

Open http://127.0.0.1:5173.

Six pages: Overview, Phenotype Workbench, Disease Explorer, Model Laboratory, Experiments & Validation, and Documentation. The application calls the real API using relative /api/v1 paths via the Vite localhost proxy. The model-comparison metrics are historical and are linked to their original GitHub benchmark.

Frontend tests and bundle build:

    npm run test
    npm run build
    npm run preview

The UI does not keep HPO observations in localStorage and does not fabricate predictions while the API is disconnected. It is a research prototype, not a diagnosis tool. See docs/PHASE_05_FRONTEND.md for the full guide.

## Phase 5 correctness review

Ranking requests are cancelled when observations or method settings change, preventing delayed results from being mistaken for a new analysis. Use Arrow Up/Down and Enter to select active HPO search results. Ranking result exports are **opt-in**, written locally as CSV/JSON, and may contain matched HPO evidence. These exported files are the only intended local copy; observations are otherwise kept in memory.

Test and build:

    npm install
    npm run test
    npm run build

Run the API and frontend separately, then use `python scripts/smoke_phase5.py` from the repository root to exercise the localhost proxy and actual HPO/ranking API calls.

Current technical limitations and the blocked CI acceptance are recorded in [Phase 5 review](../docs/PHASE_05_FINAL_AUDIT.md). A reproducible npm lockfile and successful browser build must be obtained before final Phase 5 acceptance.

### Offline logic tests with Node only

Before installing any frontend packages, use:

```bash
npm run test:logic
```

This uses Node 22's built-in test runner and verifies actual local API transport and safe CSV/JSON exports without fetching npm dependencies. It is **not** a React rendering or Vite build test. After obtaining the required npm packages, still run `npm run test` and `npm run build`.

## Phase 6 Explainability Laboratory

After running candidate disease prioritization at /workbench, the Phase 6 panel offers three tabs:

1. **HPO evidence trace:** signed overlap/semantic score contributions, exact/ontology-related matched terms, shared HPO ancestors, and score consistency checks.
2. **Same-case comparison:** real local inference for two to four available methods with exactly the same observations. Algorithm agreement is not accuracy; raw scores are not comparable across methods.
3. **What-if sensitivity:** remove one HPO term without removing the last present/suspected observation, rerun the same model, and compare the ranking. This is not causal attribution.

For trained ML methods the evidence trace is explicitly **ontology context only**, never fake SHAP or calibrated probability. The frontend calls `POST /api/v1/explain` through the local Vite proxy.

Additional dependency-free tests: `npm run test:logic` (includes xai.logic.test.mjs). React UI tests and build still require `npm install && npm run test && npm run build`.

See [Phase 6 guide](../docs/PHASE_06_EXPLAINABILITY.md).

### Phase 6 additional safety checks

The frontend now rejects an explanation if its disease ID, ranking method, model SHA-256 or HPO knowledge manifest fingerprint is inconsistent. Baseline score mismatches hide the explanation rather than presenting unverified bars. Model comparison and what-if tests similarly reject mixing changed model/database snapshots.

The complete native Node XAI suite has 13 tests. Run `npm run test:logic` for Node safeguards and `npm run test && npm run build` after installing dependencies. For strict full backend/frontend verification on a prepared M5, run `bash scripts/verify_phase6.sh --full` from the repository root.

See [Phase 6 Final Audit](../docs/PHASE_06_FINAL_AUDIT.md).
