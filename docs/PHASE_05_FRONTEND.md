# Phase 5 — React research dashboard and local website

## Goal

Deliver a professional, responsive website for RareGenXAI, connecting the Phase 2 official HPO SQLite knowledge base, Phase 3 trained models and the existing Phase 4 FastAPI backend. No AWS, Railway, external hosting, custom domain or GPU is required. Target machine: Apple M5 with 16 GB unified memory.

## Plan and actual implementation

| Step | Deliverable | Code |
| --- | --- | --- |
| 5.1 | React and Vite foundation | frontend/package.json, index.html, vite.config.js |
| 5.2 | Professional dark research design | frontend/src/styles.css, icon system, responsive sidebar |
| 5.3 | Live overview and health status | Overview, /ready, /models, /knowledge/stats |
| 5.4 | Phenotype search and evidence controls | Workbench, /phenotypes/search |
| 5.5 | Ranking with available models only | Workbench, POST /rank |
| 5.6 | Explainable results | Evidence match, score contribution and feature-input displays |
| 5.7 | Disease Explorer | /diseases/search and /diseases/{id} |
| 5.8 | Model comparison dashboard | Dynamic model status plus clearly marked historical RareBench figures |
| 5.9 | Experiments and validation | Source-linked external and synthetic evaluation plus explicit unresolved research questions |
| 5.10 | API and research documentation | Documentation route and this implementation guide |
| 5.11 | Automated tests | Vitest and React Testing Library, frontend/src/__tests__ |
| 5.12 | CI and packaging | Ubuntu and macOS Node 22 workflow, Vite build artifact |
| 5.13 | Mac handover | localhost launcher, setup and manual verification instructions |

The new frontend intentionally branches from the previously verified Phase 4 main branch. Phase 4 correctness review PR #8 is open, not merged, and its review changes have not been assumed by the new UI.

## Architecture

~~~text
Web browser http://127.0.0.1:5173
                  |
                  v
     React 18 + Vite 6 (Phase 5)
   - Overview and connection status
   - Phenotype Workbench
   - Disease Explorer
   - Model Laboratory
   - Experiments & Validation
   - Documentation
                  |
                  | same-origin /api/v1
                  v
      Vite localhost proxy
                  |
                  v
    FastAPI http://127.0.0.1:8000
                  |
           +------+-------+
           |              |
      Phase 2 SQLite   Phase 3 trusted
      ontology/HPOA    saved ML bundle
                  |
                  v
      Ranked research candidates
      Evidence contributions/features
~~~

The React application never calls a public inference host. The same-origin API client sends structured HPO IDs and evidence statuses, not patient names or hospital records. No localStorage or cookie store is used for the workbench.

## Modules

**Overview:** Shows live disease/ontology counts when connected; indicates model availability; directs users to analysis and disease browsing. Displays the historical benchmark snapshot with a source link, distinct from current local data.

**Phenotype workbench:** Autocomplete through the real HPO search API, 20 unique observation limit, evidence statuses confirmed_present, suspected_present, confirmed_absent and unknown. A present or suspected phenotype is required. Select from overlap, semantic, tfidf, logistic, random_forest, xgboost, and mlp. Supervised models are disabled if the local verified model is missing. Top-k and shortlist settings are included. Rankings show disease names, raw method scores, matched terms, expandable evidence contributions and model input features. **Scores are not probabilities.** With no matches, display an empty state instead of fabricated candidates.

**Disease explorer:** Search the official disease annotation knowledge base, inspect HPO terms, evidence reference IDs and negation flags. Show the first 200 annotations for readability; this does not alter the source.

**Model laboratory:** Shows currently available local methods and model fingerprint, plus a separate historical research comparison on 178 eligible published RareBench cases from the original GitHub run:
https://github.com/uday8116/RareGenXAI/actions/runs/44484831306

| Method | Top-1 (%) | Top-5 (%) |
| --- | ---: | ---: |
| Exact HPO overlap | 37.64 | 54.49 |
| XGBoost | 37.64 | 48.88 |
| Random Forest | 34.27 | 41.57 |
| Logistic Regression | 32.58 | 47.19 |
| TF-IDF | 29.78 | 43.26 |
| MLP | 26.40 | 32.02 |

The figures are historical and DO NOT update automatically when different weights/HPO releases are installed. The overlap baseline ranks a larger candidate universe than supervised top-40 methods. They are not prospective clinical accuracy or proof that XGBoost improves on the baseline.

**Documentation:** Explains local startup, architecture, API paths, privacy and research limitations.

## Installation on Apple M5 / 16 GB

Install Git, Python 3.11, Node.js 22 and npm. The system runs on a CPU; no dedicated GPU is necessary. Network is needed to install dependencies and initially download official HPO resources. The running app uses localhost and does not require internet hosting.

Terminal 1 (backend):

~~~bash
cd RareGenXAI
git switch main
git pull --ff-only origin main
source .venv/bin/activate
python -m pip install -r requirements.txt

# Prepare/check Phase 2/3 using earlier guides as necessary:
python -m src.knowledge_db verify --raw-dir data/raw
python -m src.verify_models --raw-dir data/raw

bash scripts/start_api.sh
~~~

If either verification command fails because data or weights are absent, follow docs/PHASE_04_BACKEND.md to build SQLite and retrain the Phase 3 model before launching the API.

Terminal 2 (frontend):

~~~bash
cd RareGenXAI
cd frontend
npm install
npm run dev
~~~

Open http://127.0.0.1:5173 . Vite proxies /api requests to the API on 127.0.0.1:8000. Both services deliberately bind to loopback, not 0.0.0.0.

To run tests and build:

~~~bash
cd frontend
npm run test
npm run build
npm run preview
~~~

The local preview server is at http://127.0.0.1:4173.

To use the review branch before merge:

~~~bash
git fetch origin
git switch -c phase-05/react-research-dashboard --track origin/phase-05/react-research-dashboard
cd frontend && npm install && npm run test && npm run build
~~~

## Security and user experience

- No patient identifiers, accounts, uploads, identifiable medical records, or clinical notes are requested.
- Observations stay in React component memory and are sent only in the local API request body. Nothing is persisted in browser storage.
- API unreachable: show explicit offline state and disable prediction; never fabricate inference.
- Model missing: baseline methods remain usable; disabled ML choices show a clear explanation.
- Clinical interpretation: explainable ranking is not a diagnosis; raw scores are not calibrated risk or a patient outcome.
- Interface: responsive sidebar and navigation, keyboard focus styles, semantic inputs, accessible loading and error feedback, and reduced-motion styling.
- Fonts are installed as npm packages; the browser does not fetch external hosted fonts.
- The Vite preview and dev server are development/demo tools, not a secure internet hosting configuration.
- No clinical validation, authorization, production TLS, or public-hosted deployment is part of Phase 5.

## Automated acceptance

Phase 5 workflow: .github/workflows/phase5-frontend.yml

On Ubuntu and Apple Silicon it must install Node 22 packages, run frontend React tests, build the Vite static bundle and (from Ubuntu) upload the static build artifact. Tests mock the API so they can verify UI states without patient data or an installed HPO database. Real saved-model integration is verified separately in Phase 4's FastAPI/official-data CI.

**Important CI gate:** At the time of frontend implementation, GitHub Actions on the Phase 4 review PR #8 was failing before job steps began; this could affect Phase 5 CI. Do not claim checks passed or merge unverified code if these pre-execution failures persist.

## Definition of done

- [x] React/Vite project and full responsive UI committed
- [x] Real versioned FastAPI integration and honest offline/model-missing behavior
- [x] HPO input, ranking, evidence, disease browsing, research benchmark dashboard
- [x] Browser privacy boundaries and explicit non-clinical disclaimer
- [x] Automated tests and CI workflow authored
- [ ] GitHub Actions frontend test and build actually execute successfully
- [ ] Phase 5 PR reviewed and merged into main
- [ ] Physical Apple M5 local end-to-end launch and interaction verified

Future phases: advanced explainability work, true research robustness evaluations, final integration tests, dissertation and presentation. Full trained GNN development and DeepRare replication remain separate research scope.

## Experiments and validation page

The dedicated /experiments page links to the original 178-case RareBench workflow, the documented disease-disjoint synthetic HPO training protocol, and the separate experimental GNN report. It clearly flags what is **not** established: prospective clinical validation, a matched-case DeepRare reproduction, calibrated disease probabilities, and model-specific SHAP explanations. The browser does not run these experiments; the labels and references are historical research evidence only.
