"""Dependency-free Phase 8 isolation and input-guard regression checks."""
import subprocess
from unittest.mock import Mock, patch
import pytest
from scripts.phase8_e2e import API, WEB, http, loopback_url, occupied, stop

def test_external_hosts_blocked():
    for address in ("https://example.com", "http://0.0.0.0:8000", "http://localhost:8000"):
        with pytest.raises(ValueError, match="loopback"):
            loopback_url(address)
    loopback_url(API)
    loopback_url(WEB)

def test_absolute_and_double_slash_path_rejected():
    for path in ("https://evil.test", "//evil.test/path", "api/v1/ready"):
        with pytest.raises(ValueError, match="relative"):
            http(API, path)

def test_occupied_socket_returns_boolean():
    assert isinstance(occupied(0), bool)

def test_stop_noop_for_exited_process():
    proc = Mock()
    proc.poll.return_value = 0
    stop(proc)
    proc.wait.assert_not_called()

def test_stop_sends_term_to_process_group():
    proc = Mock(pid=1234)
    proc.poll.return_value = None
    with patch("scripts.phase8_e2e.os.killpg") as kill:
        stop(proc)
    kill.assert_called_once()
    assert proc.wait.call_count == 1

def test_http_status_rejection_never_claims_success():
    import io
    from urllib.error import HTTPError
    exc = HTTPError(API + "/api/v1/ready", 503, "unready",
                    {"Content-Type": "application/json"}, io.BytesIO(b'{"detail":"unavailable"}'))
    with patch("scripts.phase8_e2e.urlopen", side_effect=exc):
        with pytest.raises(AssertionError, match="expected HTTP 200, got 503"):
            http(API, "/api/v1/ready")
