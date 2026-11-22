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

def test_busy_port_prevents_starting_any_process():
    from scripts.phase8_e2e import round_trip
    with patch("scripts.phase8_e2e.occupied", side_effect=[False, True]):
        with patch("scripts.phase8_e2e.subprocess.Popen") as popen:
            with pytest.raises(RuntimeError, match="Port 5173 already in use"):
                round_trip("/usr/bin/python3", restart=False)
            popen.assert_not_called()


def test_api_process_cleaned_up_when_frontend_start_fails():
    from scripts.phase8_e2e import round_trip
    api = Mock()
    with patch("scripts.phase8_e2e.occupied", return_value=False):
        with patch("scripts.phase8_e2e.subprocess.Popen", return_value=api):
            with patch("scripts.phase8_e2e.wait_for_server", side_effect=RuntimeError("API failed")):
                with patch("scripts.phase8_e2e.stop") as stop_proc:
                    with pytest.raises(RuntimeError, match="API failed"):
                        round_trip("/usr/bin/python3", restart=False)
                    stop_proc.assert_called_once_with(api)


def test_restart_flag_runs_two_separate_round_trips():
    from scripts.phase8_e2e import main
    with patch("sys.argv", ["phase8_e2e.py", "--restart"]):
        with patch("scripts.phase8_e2e.round_trip") as cycle:
            assert main() == 0
            assert cycle.call_count == 2
            assert cycle.call_args_list[0].kwargs == {"restart": False}
            assert cycle.call_args_list[1].kwargs == {"restart": True}


def test_failed_cycle_cannot_report_success():
    from scripts.phase8_e2e import main
    with patch("sys.argv", ["phase8_e2e.py", "--restart"]):
        with patch("scripts.phase8_e2e.round_trip", side_effect=RuntimeError("missing HPO")):
            assert main() == 1
