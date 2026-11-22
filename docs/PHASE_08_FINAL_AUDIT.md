# Phase 8 — Independent correctness and acceptance review

Review date: 2026-11-22. Branch: `phase-08/system-verification`; PR #12.

## Code review findings and remediations

| Finding | Remediation | Evidence |
| --- | --- | --- |
| Vite launched via npm could outlive its wrapper | Launch installed Vite JavaScript directly in its own process group; check ports after stop | `scripts/phase8_e2e.py` |
| HPO search fallback could test arbitrary, nonclinical term | Require canonical HP:0001250 in actual official search results | `scripts/phase8_e2e.py` |
| Limited live invalid-request coverage | Exercise unknown/nonclinical/duplicate HPO, invalid status, >20 terms, unknown method, wrong limits, empty observations; require HTTP 422 | `scripts/phase8_e2e.py` |
| Insufficient failure-path regression tests | Add tests for occupied port, cleanup after failed API start, two restarts, and nonzero exit | `tests/test_phase8_e2e.py` |
| Full system check omitted earlier integration/audit protections | Include Phase 7 audit tampering tests in quick verification and Phase 6 real integration in full | `scripts/verify_phase8.sh` |
| Startup diagnostics suppressed | Preserve bounded FastAPI/Vite local temporary log excerpts on startup failure; close temp files during teardown | `scripts/phase8_e2e.py` |

## Verification evidence (do not confuse code review with executed tests)

- Source and regression tests are committed on the Phase 8 PR.
- GitHub Actions run [44994580836](https://github.com/uday8116/RareGenXAI/actions/runs/44994580836) failed with **zero reported job steps**, for both `offline-system-guards` and `frontend-build`; no test-pass evidence exists from that run.
- Later edits also require a fresh run; none of these review changes alone proves that the pipeline has passed.
- The official on-device HPO database, verified trained model and real two-cycle cold restart are not accessible from this GitHub-only review.
- The inherited Phase 5/6/7 dependency PRs remain unmerged/unaccepted. Do not merge or claim whole-project acceptance yet.

## Strict definition of done

- [x] Phase 8 verification harness, scripts and CI configuration implemented.
- [x] Review-identified correctness gaps fixed and additional tests authored.
- [ ] Latest committed regression suite executed successfully in a working runner.
- [ ] Latest official HPO/model integration tests executed successfully.
- [ ] Real frontend proxy and all method checks pass twice with clean shutdown.
- [ ] Browser interaction and accessibility manually checked on the owner's M5.
- [ ] Stacked upstream acceptance and PR merge requirements resolved.

## Run after preparing the official local artifacts

```bash
git checkout phase-08/system-verification
bash scripts/verify_phase8.sh --quick
bash scripts/verify_phase8.sh --full
```

Use `docs/PHASE_08_SYSTEM_VERIFICATION.md` for prerequisites and scope. No diagnostic ranking is suitable for clinical use.
