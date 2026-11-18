"""Dependency-free tests for the Phase 1 environment doctor."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.doctor import inspect_project


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

    def test_incomplete_manifest_fails_required_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ("data/raw/hp.obo", "data/raw/phenotype.hpoa",
                             "data/processed/profiles.json"):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("example", encoding="utf-8")
            manifest = root / "data/raw/manifest.json"
            manifest.write_text(json.dumps({"hp.obo": {}}), encoding="utf-8")
            report, data = self.check(root, "hpo_data", require_data=True)
            self.assertFalse(report["ok"])
            self.assertIn("missing HPO entries", data["detail"])

    def test_present_data_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ("data/raw/hp.obo", "data/raw/phenotype.hpoa",
                             "data/processed/profiles.json"):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("example", encoding="utf-8")
            (root / "data/raw/manifest.json").write_text(
                json.dumps({"hp.obo": {}, "phenotype.hpoa": {}}), encoding="utf-8"
            )
            report, data = self.check(root, "hpo_data", require_data=True)
            self.assertTrue(report["ok"])
            self.assertEqual(data["status"], "ok")

    def test_required_model_is_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, model = self.check(root, "trained_model", require_model=True)
            self.assertFalse(report["ok"])
            self.assertEqual(model["status"], "error")
            target = root / "models/raregen_ml.joblib"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"placeholder")
            report, model = self.check(root, "trained_model", require_model=True)
            self.assertTrue(report["ok"])
            self.assertEqual(model["status"], "ok")

    def test_unsupported_python_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            report = inspect_project(Path(directory), minimal=True, python_version=(3, 10))
            self.assertFalse(report["ok"])
            self.assertEqual(next(c["status"] for c in report["checks"]
                                  if c["name"] == "python"), "error")


if __name__ == "__main__":
    unittest.main()
