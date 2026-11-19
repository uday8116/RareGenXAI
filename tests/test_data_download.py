"""Network interruption regression tests; never contact the real HPO servers."""
import hashlib
import json
from pathlib import Path

import pytest
import requests

import src.data as data


class Response:
    def __init__(self, *, fail=False):
        self.fail = fail

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def raise_for_status(self):
        if self.fail:
            raise requests.ConnectionError("test-only interrupted transfer")

    def iter_content(self, size):
        yield b"A" * 2000
        yield b"B" * 2000


def test_interrupted_source_download_retries_and_leaves_no_partial_files(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "RAW", tmp_path)
    monkeypatch.setattr(data, "URLS", {"hp.obo": "https://example.invalid/hp.obo"})
    calls = []
    def get(*args, **kwargs):
        calls.append(args)
        return Response(fail=len(calls) < 3)
    monkeypatch.setattr(data.requests, "get", get)
    monkeypatch.setattr(data.time, "sleep", lambda _: None)
    manifest = data.download(force=True)
    path = tmp_path / "hp.obo"
    assert len(calls) == 3
    assert manifest["hp.obo"]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert json.loads((tmp_path / "manifest.json").read_text()) == manifest
    assert not list(tmp_path.glob("*.partial"))
    assert not list(tmp_path.glob(".*.partial"))


def test_failed_force_download_does_not_destroy_previous_good_file(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "RAW", tmp_path)
    monkeypatch.setattr(data, "URLS", {"hp.obo": "https://example.invalid/hp.obo"})
    path = tmp_path / "hp.obo"
    original = b"trusted-original" * 300
    path.write_bytes(original)
    def fail(*args, **kwargs):
        raise requests.ConnectionError("offline")
    monkeypatch.setattr(data.requests, "get", fail)
    monkeypatch.setattr(data.time, "sleep", lambda _: None)
    with pytest.raises(RuntimeError, match="four attempts"):
        data.download(force=True)
    assert path.read_bytes() == original
    assert not list(tmp_path.glob(".*.partial"))
