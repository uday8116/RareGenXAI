# Phase 8 — End-to-end system verification and safe local restart

**Status: implementation delivered; full Mac acceptance not verified.**
Phase 8 follows `docs/PROJECT_IMPLEMENTATION_ROADMAP.md`. It remains stacked
on Phase 7, whose latest official-data benchmark and GitHub runner checks are outstanding.

## Deliverables

- `scripts/phase8_e2e.py`: starts real loopback FastAPI and Vite services; waits for
  health, checks readiness, searches real official HPO terms through the frontend
  proxy, ranks with overlap, checks real explanation/disease/source consistency,
  tests 422 responses for invalid, nonclinical and duplicate HPO observations.
  It shuts down both process groups, checks released ports, then optionally repeats
  the cold-start cycle. It refuses to interfere with occupied ports.
- `tests/test_phase8_e2e.py`: dependency-free guard tests; external hosts and
  arbitrary URL paths are rejected, process termination is checked, and an
  unready API cannot count as success.
- `scripts/verify_phase8.sh`: quick offline tests vs strict full real-data
  model verification, React tests/build, live proxy smoke and double restart.
- `.github/workflows/phase8-system.yml`: offline Python guards + Node tests/build.
  GitHub runners must actually execute to claim a pass.

## Run on your M5 Mac

From the Phase 8 branch, after preparing the official HPO SQLite source database,
the verified model bundle, a Python virtualenv with `requirements.txt`, Node 22,
and `frontend/node_modules`:

```bash
bash scripts/verify_phase8.sh --quick
bash scripts/verify_phase8.sh --full
```

The **full** command requires ports 8000 and 5173 to be free and *real*
versioned local HPO/model files; it starts and stops the services itself.
No synthetic or missing-data fallback is a passing real-system result.

## Scope and safety

- All requests are sent only to 127.0.0.1 on fixed ports.
- A local Vite proxy is tested; this does NOT prove hosted website security.
- Invalid input is rejected by the actual API; test cases use public HPO terms,
  never identifiable patient observations.
- No assertions of clinical accuracy, calibration, treatment or patient safety.
- No background services are intentionally left running.
- A successful automated smoke does not establish visual accessibility or Mac
  hardware approval; the owner must inspect the browser workflow.

## Acceptance gate

- [x] Automated system/restart harness implemented.
- [x] Offline tests and CI recipe committed.
- [ ] Offline tests passed on latest committed bytes.
- [ ] Strict full official-data check passed on latest committed bytes.
- [ ] Two real service cold starts and clean shutdowns verified.
- [ ] Browser demo and accessibility inspected on owner's Mac.
- [ ] Stacked Phase 5–7 prerequisites resolved and merge approved.

**Do not mark Phase 8 fully accepted before the unchecked gates pass.**
