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
