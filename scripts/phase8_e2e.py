"""Phase 8: loopback-only real API/UI smoke and restart verification.

Requires official local data and installed Python/Node dependencies. Never uses
synthetic fixture results as evidence of a successful real HPO/model deployment.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:8000"
WEB = "http://127.0.0.1:5173"
DISCLAIMER = "research only; not clinical diagnosis"

def loopback_url(base: str) -> None:
    if base not in (API, WEB):
        raise ValueError("Phase 8 smoke tests must target the fixed loopback services")

def occupied(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0

def http(base: str, path: str, payload=None, expected=200):
    loopback_url(base)
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("Only relative local API paths permitted")
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(base + path, data=data, headers={
        "Accept": "application/json",
        **({"Content-Type": "application/json"} if payload is not None else {}),
    }, method="POST" if payload is not None else "GET")
    try:
        with urlopen(req, timeout=20) as resp:
            status, raw, ctype = resp.status, resp.read(2_000_000), resp.headers.get("Content-Type", "")
    except HTTPError as exc:
        status, raw, ctype = exc.code, exc.read(2_000_000), exc.headers.get("Content-Type", "")
    if status != expected:
        raise AssertionError(f"{path}: expected HTTP {expected}, got {status}: {raw[:200]!r}")
    if path == "/":
        result = raw.decode("utf-8")
        if 'id="root"' not in result or "RareGenXAI" not in result:
            raise AssertionError("Website shell missing")
        return result
    if "application/json" not in ctype:
        raise AssertionError(f"{path}: invalid content type {ctype}")
    return json.loads(raw)

def wait_for_server(proc, base, path, seconds=60):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if proc.poll() is not None:
            raise RuntimeError(f"Service exited early with code {proc.returncode}: {base}")
        try:
            http(base, path)
            return
        except (URLError, TimeoutError, AssertionError, OSError):
            time.sleep(0.25)
    raise RuntimeError(f"Service did not start: {base}")

def stop(proc):
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=10)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)

def validate_live():
    health = http(API, "/api/v1/health")
    assert health["status"] == "ok"
    ready = http(WEB, "/api/v1/ready")
    assert ready["ready"] is True and ready["disease_count"] > 0
    model = http(WEB, "/api/v1/models")
    assert "overlap" in model["methods"]
    assert model["status"] == "available", "Full Phase 8 requires a verified ML model"
    assert http(WEB, "/")
    hpos = http(WEB, "/api/v1/phenotypes/search?q=seizure&limit=10")
    assert isinstance(hpos, list) and hpos
    phenotype = next((x for x in hpos if x["hpo_id"] == "HP:0001250"), None)
    if phenotype is None:
        raise AssertionError("Official HP:0001250 seizure phenotype was not returned by HPO search")
    hpo = phenotype["hpo_id"]
    observations = [{"hpo_id": hpo, "status": "confirmed_present"}]
    rank = http(WEB, "/api/v1/rank", {"observations": observations, "method": "overlap", "top_k": 3})
    assert rank["method"] == "overlap" and rank["requested_count"] == 1
    assert isinstance(rank["results"], list) and len(rank["results"]) >= 1
    assert len(rank["results"]) <= 3
    assert len(rank["knowledge_manifest_sha256"]) == 64
    disease = rank["results"][0]["disease_id"]
    explanation = http(WEB, "/api/v1/explain", {
        "observations": observations, "method": "overlap", "disease_id": disease
    })
    assert explanation["knowledge_manifest_sha256"] == rank["knowledge_manifest_sha256"]
    assert explanation["disease_id"] == disease
    # Exercise every available ranking pipeline using identical official HPO input.
    for method in ("semantic", "tfidf", "logistic", "random_forest", "xgboost", "mlp"):
        assert method in model["methods"], f"Missing configured model: {method}"
        output = http(WEB, "/api/v1/rank", {
            "observations": observations, "method": method, "top_k": 3,
        })
        assert output["method"] == method and output["requested_count"] == 1
        assert len(output["results"]) > 0 and len(output["results"]) <= 3
        assert output["knowledge_manifest_sha256"] == rank["knowledge_manifest_sha256"]
        if method not in ("semantic",):
            assert output["model_sha256"] == model["model_sha256"]
    # Malformed, duplicate and nonclinical HPO input must not produce a ranking.
    for bad in (
        [{"hpo_id": "HP:9999999", "status": "confirmed_present"}],
        [{"hpo_id": "HP:0000118", "status": "confirmed_present"}],
        observations * 2,
        [{"hpo_id": hpo, "status": "invalid_status"}],
        observations * 21,
    ):
        http(WEB, "/api/v1/rank", {"observations": bad, "method": "overlap"}, expected=422)
    for invalid in (
        {"observations": observations, "method": "unsupported_model"},
        {"observations": observations, "method": "overlap", "top_k": 0},
        {"observations": observations, "method": "overlap", "candidates": 101},
        {"observations": [], "method": "overlap"},
    ):
        http(WEB, "/api/v1/rank", invalid, expected=422)
    print("PASS: real HPO search, read-only rank, explanation provenance, proxy, and 422 guards")
    print(f"Knowledge diseases: {ready['disease_count']}; model status: {model['status']}")
    print("Research only: no clinical accuracy or privacy certification is implied")

def round_trip(python_exe, *, restart):
    for port in (8000, 5173):
        if occupied(port):
            raise RuntimeError(f"Port {port} already in use. Stop existing local servers; will not kill them.")
    processes = []
    try:
        api = subprocess.Popen([python_exe, "-m", "uvicorn", "src.api:app",
                               "--host", "127.0.0.1", "--port", "8000", "--no-access-log"],
                               cwd=ROOT, start_new_session=True, stdout=subprocess.DEVNULL,
                               stderr=subprocess.STDOUT)
        processes.append(api)
        wait_for_server(api, API, "/api/v1/health")
        # Launch Node directly, not an npm shell that can leave an orphan Vite child.
        vite = ROOT / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
        if not vite.is_file():
            raise RuntimeError("Vite executable missing. Run: cd frontend && npm install")
        ui = subprocess.Popen(["node", str(vite), "--host", "127.0.0.1",
                               "--port", "5173", "--strictPort"],
                              cwd=ROOT / "frontend", start_new_session=True,
                              stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        processes.append(ui)
        wait_for_server(ui, WEB, "/")
        validate_live()
        print("PASS: local services started and verified" + (" after restart" if restart else ""))
    finally:
        for proc in reversed(processes):
            stop(proc)
    for port in (8000, 5173):
        if occupied(port):
            raise RuntimeError(f"Port {port} still occupied following shutdown")
    print("PASS: both service processes stopped, ports released")

def main():
    parser = argparse.ArgumentParser(description="Phase 8 real localhost integration smoke")
    parser.add_argument("--restart", action="store_true", help="Run two cold-start cycles")
    args = parser.parse_args()
    py = sys.executable
    try:
        round_trip(py, restart=False)
        if args.restart:
            round_trip(py, restart=True)
    except (AssertionError, RuntimeError, OSError, ValueError, URLError, KeyError) as exc:
        print("FAIL Phase 8 real-system acceptance:", exc, file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
