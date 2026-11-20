# RareGenXAI React research website

This is the Phase 5 local-only React/Vite website for the Phase 4 FastAPI research backend.

Start FastAPI in Terminal 1 from the repository root:

    bash scripts/start_api.sh

Start React in Terminal 2:

    cd frontend
    npm install
    npm run dev

Open http://127.0.0.1:5173.

Five pages: Overview, Phenotype Workbench, Disease Explorer, Model Laboratory and Documentation. The application calls the real API using relative /api/v1 paths via the Vite localhost proxy. The model-comparison metrics are historical and are linked to their original GitHub benchmark.

Frontend tests and bundle build:

    npm run test
    npm run build
    npm run preview

The UI does not keep HPO observations in localStorage and does not fabricate predictions while the API is disconnected. It is a research prototype, not a diagnosis tool. See docs/PHASE_05_FRONTEND.md for the full guide.
