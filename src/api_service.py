"""Read-only, cached HPO knowledge and trusted-model service for FastAPI.

No patient data is written, logged or retained. Observations exist only for a
single API request. Cached objects contain *public* HPO disease knowledge.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import RLock

from src.db_access import DEFAULT_DB, load_ranking_inputs, open_readonly
from src.knowledge_db import validate_connection
from src.model_bundle import load_verified_bundle
from src.ranking import information_content


class ResearchService:
    def __init__(self, db_path: str | Path = DEFAULT_DB,
                 model_path: str | Path = "models/raregen_ml.joblib"):
        self.db_path = Path(db_path)
        self.model_path = Path(model_path)
        self.lock = RLock()
        self._context_key = None
        self._context = None
        self._model_key = None
        self._model = None
        self._manifest = None

    def _file_key(self, path: Path) -> tuple[int, int, int, int, int]:
        """Detect atomic file replacement even with equal size/mtime values."""
        state = path.stat()
        return (state.st_dev, state.st_ino, state.st_ctime_ns,
                state.st_mtime_ns, state.st_size)

    def context(self) -> dict:
        """Load validated schema-v2 clinical phenotype data only once per snapshot."""
        key = self._file_key(self.db_path)
        with self.lock:
            if self._context is not None and key == self._context_key:
                return self._context
            with open_readonly(self.db_path) as conn:
                validated = validate_connection(conn)
                profiles, negatives, labels, parents = load_ranking_inputs(conn, phenotypic_only=True)
            context = {
                "profiles": profiles, "negatives": negatives,
                "labels": labels, "parents": parents,
                "sources": validated["sources"],
                "counts": validated["counts"],
                "schema_version": validated["metadata"]["schema_version"],
                "ic": None,
            }
            self._context = context
            self._context_key = key
            self._model_key = None
            self._model = None
            self._manifest = None
            return context

    def information_content(self) -> dict:
        with self.lock:
            context = self.context()
            if context["ic"] is None:
                context["ic"] = information_content(context["profiles"], context["parents"])
            return context["ic"]

    def verified_model(self):
        """Load only a trusted model with exactly matching Phase 2 source data."""
        with self.lock:
            context = self.context()
            manifest_path = self.model_path.with_suffix(".manifest.json")
            key = (self._context_key, self._file_key(self.model_path), self._file_key(manifest_path))
            if self._model is not None and key == self._model_key:
                return self._model, self._manifest
            model, manifest = load_verified_bundle(
                self.model_path, expected_profiles=context["profiles"]
            )
            source = manifest.get("source", {})
            if (source.get("kind") != "hpo_sqlite_v2_aspect_P"
                    or source.get("data_sources") != context["sources"]):
                raise ValueError("Model provenance does not match this HPO database")
            self._model = model
            self._manifest = manifest
            self._model_key = key
            return model, manifest

    def model_status(self) -> dict:
        """Status is explicit: missing weights are NOT silently fabricated."""
        manifest_path = self.model_path.with_suffix(".manifest.json")
        if not self.model_path.exists() and not manifest_path.exists():
            return {"status": "missing", "methods": ["overlap", "semantic"]}
        try:
            _, manifest = self.verified_model()
        except (OSError, ValueError, KeyError, TypeError, sqlite3.DatabaseError):
            return {"status": "incompatible", "methods": ["overlap", "semantic"]}
        return {
            "status": "available",
            "methods": ["overlap", "semantic", *manifest["methods"]],
            "model_sha256": manifest["artifact_sha256"],
            "profile_sha256": manifest["profile_sha256"],
            "manifest_schema": manifest["manifest_schema"],
        }
