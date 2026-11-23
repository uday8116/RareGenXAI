"""Static Phase 9 consistency checks; no data downloads or medical validation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

FILES = (
    "PHASE_09_USER_GUIDE.md",
    "PHASE_09_API_AND_SCHEMA.md",
    "PHASE_09_DISSERTATION_DRAFT.md",
    "PHASE_09_PRESENTATION.md",
    "PHASE_09_SPEECH_AND_VIVA.md",
    "PHASE_09_PLAN_AND_ACCEPTANCE.md",
    "PHASE_09_EVIDENCE_LEDGER.md",
)

def test_all_documentation_exists_and_has_substance():
    for name in FILES:
        content = (DOCS / name).read_text(encoding="utf-8")
        assert len(content) > 700, name
        assert "RareGenXAI" in content or "Phase 9" in content, name

def test_api_routes_in_document_match_implemented_routes():
    source = (ROOT / "src/api.py").read_text(encoding="utf-8")
    reference = (DOCS / "PHASE_09_API_AND_SCHEMA.md").read_text(encoding="utf-8")
    for path in ("/health", "/ready", "/knowledge/stats", "/phenotypes/search",
                 "/diseases/search", "/models", "/rank", "/explain"):
        assert f'API_PREFIX + "{path}"' in source, path
        assert "/api/v1" + path in reference, path

def test_schema_names_match_versioned_sql():
    schema = (ROOT / "src/db_schema.py").read_text(encoding="utf-8")
    reference = (DOCS / "PHASE_09_API_AND_SCHEMA.md").read_text(encoding="utf-8")
    for table in ("schema_migrations", "data_sources", "db_metadata", "hpo_terms",
                  "hpo_aliases", "hpo_synonyms", "hpo_parents", "diseases",
                  "disease_phenotypes", "hpoa_source_rows"):
        assert table in schema and table in reference, table

def test_archived_metrics_are_same_snapshot_not_new_inference():
    history = (DOCS / "PHASE_07_HISTORICAL_REANALYSIS.md").read_text(encoding="utf-8")
    dissertation = (DOCS / "PHASE_09_DISSERTATION_DRAFT.md").read_text(encoding="utf-8")
    slides = (DOCS / "PHASE_09_PRESENTATION.md").read_text(encoding="utf-8")
    speech = (DOCS / "PHASE_09_SPEECH_AND_VIVA.md").read_text(encoding="utf-8")
    for metric in ("37.64%", "54.49%", "36.52%"):
        assert metric in history and metric in dissertation and metric in slides, metric
    assert "37.64" in speech and "54.49" in speech
    for content in (dissertation, slides, speech):
        assert "DeepRare" in content
        assert "not" in content.lower()
        assert "archiv" in content.lower()
    assert "178" in history and "178" in dissertation and "178" in slides

def test_presentation_has_twelve_slides():
    deck = (DOCS / "PHASE_09_PRESENTATION.md").read_text(encoding="utf-8")
    for index in range(1, 13):
        assert f"Slide {index} —" in deck

def test_phase9_acceptance_never_claims_latest_ci_pass():
    guide = (DOCS / "PHASE_09_PLAN_AND_ACCEPTANCE.md").read_text(encoding="utf-8")
    assert "not verified passing" in guide
    assert "Supervisor" in guide


def test_legacy_report_and_draft_marked_historical():
    old = (DOCS / "FINAL_PROJECT_REPORT.md").read_text(encoding="utf-8")
    draft = (DOCS / "REPORT_DRAFT.md").read_text(encoding="utf-8")
    ledger = (DOCS / "PHASE_09_EVIDENCE_LEDGER.md").read_text(encoding="utf-8")
    for content in (old, draft):
        assert "PHASE_09_EVIDENCE_LEDGER.md" in content
    for value in ("27.53%", "30.34%", "34.27%", "29.78%"):
        assert value in ledger, value
    assert "different" in ledger.lower()


def test_all_submission_documents_use_one_archive():
    ledger = (DOCS / "PHASE_09_EVIDENCE_LEDGER.md").read_text(encoding="utf-8")
    report = (DOCS / "PHASE_09_DISSERTATION_DRAFT.md").read_text(encoding="utf-8")
    slides = (DOCS / "PHASE_09_PRESENTATION.md").read_text(encoding="utf-8")
    speech = (DOCS / "PHASE_09_SPEECH_AND_VIVA.md").read_text(encoding="utf-8")
    for content in (report, slides, speech):
        assert "178" in content
        assert "37.64" in content
        assert "54.49" in content
        assert "DeepRare" in content
    assert "44467435510" in ledger
    assert "not verified" in ledger.lower()
