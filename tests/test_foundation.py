"""Dependency-free regression tests for Phase 1 environment diagnostics."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.doctor import inspect_project


def make_hpo_fixture(root: Path) -> None:
    raw = root / "data/raw"
    processed = root / "data/processed"
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)
    sources = {
        "hp.obo": b"format-version: 1.2\n\n[Term]\nid: HP:0000001\nname: Example\n",
        "phenotype.hpoa": (
            b"database_id\tdisease_name\tqualifier\thpo_id\n"
            b"OMIM:1\tExample disorder\t\tHP:0000001\n"
        ),
    }
    manifest = {}
    for name, contents in sources.items():
        (raw / name).write_bytes(contents)
        manifest[name] = {
            "url": "https://example.invalid/" + name,
            "sha256": hashlib.sha256(contents).hexdigest(),
            "bytes": len(contents),
        }
    (raw / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (processed / "profiles.json").write_text(json.dumps({
        "profiles": {"OMIM:1": ["HP:0000001"]},
        "negatives": {},
        "labels": {"OMIM:1": "Example disorder"},
    }), encoding="utf-8")


class FoundationDoctorTests(unittest.TestCase):
    def check(self, root, name, **options):
        report = inspect_project(root, minimal=True, python_version=(3, 11), **options)
        return report, next(c for c in report["checks"] if c["name"] == name)

    def test_missing_optional_artifacts_are_warnings(self):
        with tempfile.TemporaryDirectory() as directory:
            report, data = self.check(Path(directory), "hpo_data")
            _, model = self.check(Path(directory), "trained_model")
            self.assertTrue(report["ok"])
            self.assertEqual(data["status"], "warning")
            self.assertEqual(model["status"], "warning")

    def test_missing_required_data_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            report, data = self.check(Path(directory), "hpo_data", require_data=True)
            self.assertFalse(report["ok"])
            self.assertEqual(data["status"], "error")

    def test_incomplete_manifest_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_hpo_fixture(root)
            path = root / "data/raw/manifest.json"
            path.write_text(json.dumps({"hp.obo": {}}), encoding="utf-8")
            report, data = self.check(root, "hpo_data", require_data=True)
            self.assertFalse(report["ok"])
            self.assertIn("manifest.json missing metadata", data["detail"])

    def test_valid_data_verified_by_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_hpo_fixture(root)
            report, data = self.check(root, "hpo_data", require_data=True)
            self.assertTrue(report["ok"])
            self.assertEqual(data["status"], "ok")

    def test_corrupted_download_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_hpo_fixture(root)
            path = root / "data/raw/hp.obo"
            contents = path.read_bytes()
            path.write_bytes(contents.replace(b"Example", b"Tampered"))
            report, data = self.check(root, "hpo_data", require_data=True)
            self.assertFalse(report["ok"])
            self.assertIn("SHA-256 mismatch", data["detail"])

    def test_wrong_annotation_schema_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_hpo_fixture(root)
            path = root / "data/raw/phenotype.hpoa"
            changed = b"database_id\tphenotype\nOMIM:1\tHP:0000001\n"
            path.write_bytes(changed)
            manifest_path = root / "data/raw/manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["phenotype.hpoa"]["sha256"] = hashlib.sha256(changed).hexdigest()
            manifest["phenotype.hpoa"]["bytes"] = len(changed)
            manifest_path.write_text(json.dumps(manifest))
            report, data = self.check(root, "hpo_data", require_data=True)
            self.assertFalse(report["ok"])
            self.assertIn("missing required table columns", data["detail"])

    def test_invalid_profiles_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_hpo_fixture(root)
            (root / "data/processed/profiles.json").write_text(
                json.dumps({"profiles": {"OMIM:1": ["INVALID"]}, "labels": {}}))
            report, data = self.check(root, "hpo_data", require_data=True)
            self.assertFalse(report["ok"])
            self.assertIn("invalid HPO ID", data["detail"])

    def test_required_model_file_is_not_claimed_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, model = self.check(root, "trained_model", require_model=True)
            self.assertFalse(report["ok"])
            self.assertEqual(model["status"], "error")
            target = root / "models/raregen_ml.joblib"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"placeholder")
            report, model = self.check(root, "trained_model", require_model=True)
            self.assertTrue(report["ok"])
            self.assertIn("not loaded, verified or trusted", model["detail"])

    def test_unsupported_python_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            report = inspect_project(Path(directory), minimal=True, python_version=(3, 10))
            self.assertFalse(report["ok"])
            self.assertEqual(next(c["status"] for c in report["checks"]
                                  if c["name"] == "python"), "error")

    def test_rosetta_python_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("scripts.doctor.platform.system", return_value="Darwin"), patch(
                "scripts.doctor.platform.machine", return_value="x86_64"
            ):
                report = inspect_project(Path(directory), minimal=True, python_version=(3, 11))
            self.assertFalse(report["ok"])
            self.assertIn("Rosetta", next(c["detail"] for c in report["checks"]
                                        if c["name"] == "platform"))


if __name__ == "__main__":
    unittest.main()
