"""Phase 10: no clinical data needed; temporary synthetic byte fixtures only."""
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from scripts.phase10_backup import (
    CORE_FILES, MANIFEST, SCHEMA, create, restore, safe_member, verify,
)


def fixture_tree(tmp_path):
    root = tmp_path / "repo"
    (root / "data" / "raw").mkdir(parents=True)
    (root / "models").mkdir()
    (root / "data" / "raw" / "manifest.json").write_text(
        '{"note":"synthetic test only"}', encoding="utf-8"
    )
    (root / "models" / "raregen_ml.manifest.json").write_text(
        '{"synthetic":true}', encoding="utf-8"
    )
    return root


def test_backup_verify_and_restore_round_trip(tmp_path):
    root = fixture_tree(tmp_path)
    archive = tmp_path / "backup.zip"
    created = create(root, archive)
    assert archive.exists()
    assert created["schema"] == SCHEMA
    assert created["case_results_opt_in"] is False
    assert created["missing_core"]
    assert verify(archive) == created
    dest = tmp_path / "restored"
    restored = restore(archive, dest)
    assert restored == created
    for name in created["files"]:
        assert (dest / name).read_bytes() == (root / name).read_bytes()


def test_backup_refuses_to_overwrite_existing_archive(tmp_path):
    root = fixture_tree(tmp_path)
    archive = tmp_path / "backup.zip"
    archive.write_bytes(b"precious previous backup")
    with pytest.raises(FileExistsError):
        create(root, archive)
    assert archive.read_bytes() == b"precious previous backup"


def test_backup_excludes_sensitive_or_unspecified_paths(tmp_path):
    root = fixture_tree(tmp_path)
    (root / ".env").write_text("TOKEN=SECRET")
    (root / "data" / "raw" / "patient.csv").write_text("private")
    archive = tmp_path / "backup.zip"
    create(root, archive)
    with zipfile.ZipFile(archive) as z:
        assert ".env" not in z.namelist()
        assert "data/raw/patient.csv" not in z.namelist()


def test_opt_in_required_for_external_cases(tmp_path):
    root = fixture_tree(tmp_path)
    (root / "data" / "external").mkdir(parents=True)
    case = root / "data" / "external" / "rarebench_cases.csv"
    case.write_text("case_id\nsynthetic-case")
    default = tmp_path / "default.zip"
    create(root, default)
    assert "data/external/rarebench_cases.csv" not in verify(default)["files"]
    optin = tmp_path / "optin.zip"
    create(root, optin, include_cases=True)
    assert "data/external/rarebench_cases.csv" in verify(optin)["files"]


def test_backup_refuses_symbolic_link_in_allowlisted_source(tmp_path):
    root = fixture_tree(tmp_path)
    source = tmp_path / "outside.txt"
    source.write_text("outside")
    (root / "models" / "raregen_ml.joblib").symlink_to(source)
    with pytest.raises(ValueError, match="symlink"):
        create(root, tmp_path / "backup.zip")


def test_backup_fails_if_no_approved_local_files(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    with pytest.raises(ValueError, match="No approved"):
        create(root, tmp_path / "backup.zip")


def test_verification_detects_byte_tampering(tmp_path):
    root = fixture_tree(tmp_path)
    archive = tmp_path / "backup.zip"
    create(root, archive)
    changed = tmp_path / "tampered.zip"
    with zipfile.ZipFile(archive) as src, zipfile.ZipFile(changed, "w") as out:
        for name in src.namelist():
            data = src.read(name)
            if name == "data/raw/manifest.json":
                data += b"\nchanged"
            out.writestr(name, data)
    with pytest.raises(ValueError, match="size mismatch|SHA-256 mismatch"):
        verify(changed)


def test_verification_rejects_path_traversal_and_unknown_names(tmp_path):
    assert safe_member("models/raregen_ml.joblib")
    for name in ("../../evil.txt", "/tmp/a", "notes.txt",
                 "data/raw/../raw/manifest.json", r"data\raw\hp.obo"):
        with pytest.raises(ValueError):
            safe_member(name)


def test_verification_rejects_extra_zip_members(tmp_path):
    root = fixture_tree(tmp_path)
    src = tmp_path / "safe.zip"
    create(root, src)
    bad = tmp_path / "extra.zip"
    with zipfile.ZipFile(src) as original, zipfile.ZipFile(bad, "w") as modified:
        for entry in original.namelist():
            modified.writestr(entry, original.read(entry))
        modified.writestr("../evil.txt", b"x")
    with pytest.raises(ValueError, match="Unapproved"):
        verify(bad)


def test_verification_rejects_duplicate_members(tmp_path):
    root = fixture_tree(tmp_path)
    src = tmp_path / "safe.zip"
    create(root, src)
    bad = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(src) as original, zipfile.ZipFile(bad, "w") as modified:
        for entry in original.namelist():
            modified.writestr(entry, original.read(entry))
        modified.writestr("data/raw/manifest.json", b"extra")
    with pytest.raises(ValueError, match="duplicate"):
        verify(bad)


def test_restore_refuses_nonempty_or_symlink_destination(tmp_path):
    root = fixture_tree(tmp_path)
    archive = tmp_path / "backup.zip"
    create(root, archive)
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "keep.txt").write_text("keep")
    with pytest.raises(FileExistsError, match="new or empty"):
        restore(archive, occupied)
    assert (occupied / "keep.txt").read_text() == "keep"
    link = tmp_path / "symlink"
    link.symlink_to(occupied)
    with pytest.raises(FileExistsError):
        restore(archive, link)


def test_restore_rechecks_integrity_before_making_destination(tmp_path):
    root = fixture_tree(tmp_path)
    archive = tmp_path / "backup.zip"
    create(root, archive)
    broken = tmp_path / "broken.zip"
    with zipfile.ZipFile(archive) as z, zipfile.ZipFile(broken, "w") as out:
        for name in z.namelist():
            out.writestr(name, z.read(name) + (b"x" if name != MANIFEST else b""))
    target = tmp_path / "not-created"
    with pytest.raises(ValueError):
        restore(broken, target)
    assert not target.exists()


def test_manifest_cannot_claim_private_opt_in_without_flag(tmp_path):
    root = fixture_tree(tmp_path)
    source = tmp_path / "safe.zip"
    create(root, source)
    broken = tmp_path / "bad-manifest.zip"
    with zipfile.ZipFile(source) as z, zipfile.ZipFile(broken, "w") as out:
        for name in z.namelist():
            if name == MANIFEST:
                m = json.loads(z.read(name))
                m["case_results_opt_in"] = "yes"
                out.writestr(name, json.dumps(m))
            else:
                out.writestr(name, z.read(name))
    with pytest.raises(ValueError, match="opt-in"):
        verify(broken)
