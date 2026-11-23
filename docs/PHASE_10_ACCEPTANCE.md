> **Updated handover status — 2026-11-23:** Phases 1–10 are integrated into `main` at source merge commit `ad53ece83beedadf3bf4cd31d511cfdafb61795e`. The owner explicitly requested **no testing** for this handover. Consequently, no tests were executed as part of this release preparation, and none of the historical CI/benchmark/local Mac acceptance gates should be marked passed. Earlier stacked PRs #10–#13 were closed as superseded after their commits were integrated via PR #14. Academic approval, local database/model preparation, and backup creation require the owner. Read [the no-testing handover](RELEASE_HANDOVER_NO_TESTING.md) before distributing this source snapshot.

# Phase 10 — Release gate, ownership and evidence matrix

**Roadmap:** tagged release candidate, limitations, demonstration and backup.
**Current status:** release tooling and materials authored; no release tag
or complete system acceptance is asserted.

## Implementation scope

- [x] Phase 10 branch based on Phase 9.
- [x] Allowlisted local research backup, SHA-256 verification, safe restore.
- [x] Regression coverage for integrity, traversal, symlink, opt-in and overwrite.
- [x] Quick/full release verification script.
- [x] Local demo, recovery, handover and proposed release notes.
- [x] GitHub Actions offline release-tool checks configured.

## Final acceptance (strict)

- [ ] Latest Phase 10 quick regression tests executed and passed.
- [ ] Phase 7 full official frozen experiment passed with audited source hashes.
- [ ] Phase 8 real-Mac two-cycle system test passed on official HPO/model.
- [ ] Phase 9 documentation CI passed and supervisor approved format and claims.
- [ ] All six core artifact files backed up, hashed and safely restored.
- [ ] User inspected real browser workflow, sanitized screenshots and artifacts.
- [ ] GitHub Actions runner issue resolved and CI steps actually passed.
- [x] Source changes from Phase 4–10 integrated into main via PRs #8, #9, and #14 (stacked #10–#13 superseded); this is **not acceptance evidence**.
- [ ] Explicit maintainer tag authorization and a reviewed commit SHA.

No unchecked gate may be represented as completed. A passing offline suite
does not substitute for research, hardware, academic or security acceptance.

## Commands

```bash
bash scripts/verify_phase10.sh --quick
bash scripts/verify_phase10.sh --full
```

The quick mode runs synthetic offline backup tests and Phase 9 document tests.
The full mode adds Phase 7 frozen RareBench inference audit, Phase 8 official
model/UI restart integration, and a verified six-core-file backup+restore. A
stale or pre-existing Phase 7 frozen plan must be handled according to its
preregistration rules; never overwrite evidence to force a green result.

## Evidence ledger (fill after real execution)

| Gate | Evidence | Current state |
| --- | --- | --- |
| Phase 10 CI | Success URL, attempt, head SHA and test logs | Not verified |
| Phase 7 source/model | Audited case/method matrix and SHA-256 manifests | Pending |
| Phase 8 local Mac | Two full cold starts, browser screenshots | Pending |
| Phase 9 academic | Institution template and supervisor approval | Pending |
| Backup | Private location and SHA-256 verified manifest | Pending |
| Restore | Independent empty folder, matching source checksums | Pending |
| Release tag | Approved specific commit and signed-off release notes | Not created |

Owner must preserve real run logs and screenshots privately. Release maintainers
must check code review, GitHub runner state and provenance before merge/tag.
University supervisor must independently approve academic claims and forms.
See `docs/PHASE_10_RELEASE_HANDOVER.md` for all procedures.
