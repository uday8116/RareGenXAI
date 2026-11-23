"""Phase 5 end-to-end localhost HTTP smoke test.

Run only after both servers are running:
  python scripts/smoke_phase5.py

Checks the frontend server, same-origin Vite -> FastAPI proxy, official HPO
phenotype search, and real candidate ranking. Does NOT prove browser styling,
clinical accuracy, or medical safety. No patient information is sent.
"""
from __future__ import annotations

import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:5173"


def request(path: str, *, payload: dict | None = None) -> object:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(
        BASE + path,
        data=data,
        headers={"Accept": "application/json",
                 **({"Content-Type": "application/json"} if data else {})},
        method="POST" if data is not None else "GET",
    )
    with urlopen(req, timeout=60) as response:
        body = response.read()
        if path == "/":
            content = body.decode("utf-8")
            if "id=\"root\"" not in content or "<title>RareGenXAI" not in content:
                raise AssertionError("Frontend server did not return the RareGenXAI app shell")
            return {"html_ok": True}
        if response.status != 200 or "application/json" not in response.headers.get("Content-Type", ""):
            raise AssertionError("Unexpected status/content type for " + path)
        return json.loads(body)


def main() -> int:
    try:
        assert request("/")["html_ok"]
        ready = request("/api/v1/ready")
        assert ready["ready"], "HPO database is not ready"
        models = request("/api/v1/models")
        assert "overlap" in models["methods"]
        phenotypes = request("/api/v1/phenotypes/search?q=" + quote("seizure") + "&limit=5")
        assert phenotypes, "Official HPO phenotype search returned nothing"
        matching = next((p for p in phenotypes if p["hpo_id"] == "HP:0001250"), phenotypes[0])
        hpo_id = matching["hpo_id"]
        observation = [{"hpo_id": hpo_id, "status": "confirmed_present"}]
        methods = ["overlap", "semantic"]
        if models["status"] == "available":
            methods.extend(["tfidf", "logistic", "random_forest", "xgboost", "mlp"])
        for method in methods:
            result = request("/api/v1/rank", payload={
                "observations": observation, "method": method, "top_k": 3,
            })
            assert result["method"] == method
            assert isinstance(result["results"], list)
            assert len(result["results"]) <= 3
            assert all("disease_id" in row and "score" in row for row in result["results"])
            print("PASS", method, "ranked", len(result["results"]), "candidates")
        print("PASS frontend /, backend readiness, HPO search, and all available model methods")
        print("Database:", ready["disease_count"], "diseases; model:", models["status"])
        print("RESEARCH ONLY — rankings are NOT medical diagnoses or probabilities")
        return 0
    except (HTTPError, URLError, ValueError, KeyError, AssertionError) as exc:
        print("FAIL local Phase 5 smoke test:", exc, file=sys.stderr)
        print("Start FastAPI with bash scripts/start_api.sh and React with bash scripts/start_frontend.sh",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
