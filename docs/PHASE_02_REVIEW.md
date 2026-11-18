# Phase 2 acceptance review: completeness and integrity

**Reviewed baseline:** `main` at `6da081d`. **Scope:** official HPO terminology and disease-phenotype SQLite knowledge, not patient diagnosis or ML training.

## Findings fixed

| Finding | Resolution | Test/evidence |
| --- | --- | --- |
| Two official HPOA fields (`modifier`, `biocuration`) were dropped | Schema v2 includes both and retains all raw source annotation rows | Modifier-specific fixture test |
| `src.data.load_annotations()` filtered malformed HPO IDs before Phase 2 validation | New strict, streaming importer reads all 12 raw fields and rejects malformed/unmapped IDs | Negative input tests |
| Deduplicated compact associations made source annotation count irrecoverable | Added `hpoa_source_rows` table with row numbers and original/canonical IDs | Source-row accounting invariant |
| Ranking input included inheritance and clinical-course annotations as symptoms | Default to aspect `P`, with explicit all-aspect option for previous experiments | Inheritance fixture and official profile parity |
| `verify` only checked DB structural integrity | Full `integrity_check`, FK and row-accounting checks; source SHA match when `--raw-dir` is provided | Official CI + corrupted input tests |
| Exact synonyms and aliases could rank below partial names | SQL-ranked exact HPO ID, alias, name, synonym then prefix and substring | Search regression tests |
| `with connect_readonly()` did not guarantee closing SQLite connection | Added `open_readonly()` managed context and use explicit closing in CLI | Connection cleanup regression test |

## Required acceptance gates

- [x] Schema v2 and migration path implemented.
- [x] Strict, loss-aware HPOA input validation.
- [x] All 12 fields accounted for, compact annotations and every source annotation preserved.
- [x] Read-only HPO term and disease queries and ranking adapter.
- [x] Unit tests with malformed source data, aliases, negative qualifiers and failed rebuild.
- [x] Official download and SQLite import verified on GitHub runners (see workflows).
- [ ] User's actual Apple M5 machine performs `build --replace`, `verify --raw-dir data/raw`, and example searches.

**Important:** passing GitHub macOS CI verifies an Apple Silicon runner, not this user's physical Mac. Never call the local installation complete until tested there.

## Reproducibility limits

Official HPO download URLs are mutable; save each source file alongside the recorded source manifest for a reproducible snapshot. The importer records exact SHA-256 values and source byte lengths but does not independently establish clinical correctness. Formal validation of an ML model and independent patient cohorts belongs in later phases. No identifiable patient data is loaded or stored.

## Local review commands

```bash
git switch main
git pull --ff-only origin main
source .venv/bin/activate
python -m src.data
python -m src.knowledge_db build --replace
python -m src.knowledge_db verify --raw-dir data/raw
python -m pytest -q tests/test_knowledge_db.py tests/test_db_integration.py
python -m src.knowledge_db search-hpo "seizure"
python -m src.knowledge_db search-disease "Marfan"
```

Back up `data/local/raregen.sqlite3` before intentionally rebuilding. Generated databases and raw HPO files are ignored by Git; do not commit them.
