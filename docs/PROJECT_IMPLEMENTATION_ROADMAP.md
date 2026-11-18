# RareGenXAI local-only implementation roadmap

**Goal:** Deliver an auditable M.Tech research prototype for *candidate disease prioritization* with an interactive interface, local API, local database, saved trained ML rerankers, explanations, reproducible evaluations and academic materials.

**Planning horizon:** 7 focused development days. This is a best-effort schedule, not a guarantee of validated clinical performance. Defer optional work if tests or data quality are at risk. All services run locally. Target hardware is Apple M5 with 16 GB unified RAM.

| Phase | Planned slot | Required output | Exit gate |
| --- | --- | --- | --- |
| **01. Audit and environment** | Day 1 | Audit, bootstrap, doctor, verification, development guide | Scripts tested, user runs local quick check |
| **02. Data and database** | Day 1–2 | Frozen HPO downloads, validated ontology/annotations, SQLite schema and migrations | Reproducible import and HPO/disease search |
| **03. Models and training** | Day 2–3 | Saved TF-IDF index and trained logistic/RF/XGBoost/MLP rerankers; GNN optional | Reloaded artifacts return deterministic rankings on fixture inputs |
| **04. HTTP API** | Day 3–4 | FastAPI endpoints for phenotype lookup, rankings, diseases, model status, benchmark metrics | OpenAPI docs and API contract/integration tests pass |
| **05. Website** | Day 4–5 | React/Vite navigation, phenotype input, disease results, locally served UI | Full synthetic-input workflow from browser |
| **06. XAI and dashboards** | Day 5–6 | Contribution plots, model comparison, cohort views, explanation limits | Charts trace to real output files, not invented accuracy |
| **07. Research experiments** | Day 6 | External cohort evaluation, paired metrics, errors/uncertainty | Reproducible scripts, per-cohort tables, provenance |
| **08. System verification** | Day 6–7 | End-to-end tests, input validation, safe defaults, startup scripts | Clean restart and demo passes on the Mac |
| **09. Documentation and viva** | Day 7 | User guide, API docs, schema, thesis draft, slides, speech and viva Q&A | Documents agree with real code and test results |
| **10. Release and handover** | Day 7 | Tagged release candidate, known limitations, final demo and backup | All core acceptance gates met or open gaps clearly disclosed |

## Project boundaries

- **Essential:** functioning local app/API, validated HPO database, exact-overlap and TF-IDF baselines, saved CPU-friendly ML models, explainable results, real evaluation, reproducible tests and documentation.
- **Optional/stretch:** enhanced GNN performance, SHAP for the trained reranker (not a universal explanation for retrieval), gene-level expansion, a full matched DeepRare run, extensive tuning.
- **Not in scope:** hospital information systems, genetic-variant interpretation, public hosting, identifiable patient data storage, clinical certification or promises of diagnostic accuracy.

## Architecture decision (target, not current state)

`React (localhost:5173) -> FastAPI (localhost:8000) -> ranking/trained model services -> SQLite HPO/disease store + versioned local research files`.

The **current** `app.py` is a Streamlit prototype. Introduce React/FastAPI progressively while retaining the known-working model code. For a one-week deadline, a polished multi-page Streamlit solution is the documented fallback if React integration threatens core evaluation quality.

## Research gates

1. Data source URLs, versions, hashes, licensing restrictions, and identifiers are recorded.
2. Retrained model artifacts include training seed, preprocessing and exact dependency versions.
3. Synthetic development/train experiments are kept distinct from external case evaluation. Evaluation subsets are fixed **before** model tuning.
4. Report candidate recall, Top-1, Top-5, MRR, cohort sizes, uncertainty where possible and errors rather than fabricated metrics.
5. DeepRare is compared only using authentic predictions on identically aligned cases; public aggregate scores are not matched-case evidence.
6. Every user-facing screen says this is a research prototype, **not for clinical diagnosis**.

## Responsibility split

- **Code work in GitHub:** source changes, tests, docs and reviewable PRs.
- **Local machine owner:** install macOS tools, run the bootstrap, store data/model artifacts locally, report errors, and approve final demonstration.
- **Academic owner/supervisor:** institution template, ethical permissions when applicable, claims and dissertation sign-off.

## Definition of done

A phase is complete only after its exact outputs exist, automated checks pass, and any required manual local checks are confirmed. A successful workflow on GitHub does **not** mean a specific user's Mac ran it successfully.
