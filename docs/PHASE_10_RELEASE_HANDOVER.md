# RareGenXAI — Phase 10 release and handover

**Release state: CANDIDATE PREPARATION, NOT RELEASED.** Research-only rare-disease candidate ranking. No clinical diagnosis or calibrated risk. This guide accompanies the Phase 10 backup tool and release checks.

## What will be handed over

- Full Git repository history plus branch/PR review evidence. Phases 5–9 have unresolved upstream merges and acceptance.
- Official, licensed HPO source files, versioned schema-v2 SQLite knowledge, and verified locally trusted model artifacts. These are NOT in Git.
- React/Vite UI, local loopback FastAPI service, baseline and ML ranking logic and explanations.
- Historical six-method RareBench archive reanalysis and frozen future Phase 7 experiment protocol, with clearly separated source snapshots.
- Phase 8 testing scripts; Phase 9 dissertation/presentation/guide materials; Phase 10 recovery tools and release notes.

## Verification before claiming a release

Quick: `bash scripts/verify_phase10.sh --quick`. Full: `bash scripts/verify_phase10.sh --full`.

The quick mode uses synthetic fixture tests and static documentation consistency; it is **not** release approval. Full mode invokes Phase 7 real-data audit, Phase 8 official-model two-cycle local website restart, Phase 9 documentation checks, and a verified local research backup+restore. Full may refuse to run when model/source files are absent or a frozen experiment plan already exists. Never remove preregistration to fake success.

Manual owner acceptance requires real sanitized browser screenshots, API readiness and ML model status, demo in the local React workbench with public HPO example HP:0001250, rank and evidence inspection, and comparison of baseline vs trained model on the same inputs. Use the source at `docs/PHASE_09_USER_GUIDE.md`. Stop both services with Ctrl+C and do not enter identifiable clinical records.

## Safe local backup and recovery

The default backup includes ONLY these approved existing paths:
`data/raw/hp.obo`, `data/raw/phenotype.hpoa`, `data/raw/manifest.json`,
`data/local/raregen.sqlite3`, `models/raregen_ml.joblib`,
`models/raregen_ml.manifest.json`. All other data is excluded by default.
Missing files are recorded as `missing_core`; the full release gate requires
all six. Case/result files require an explicit `--include-case-results` flag and
independent human review of licensing/de-identification. Environment variables,
secrets, unknown folders and user home folders are never crawled.

Use these commands **locally** with trusted files:

```bash
python scripts/phase10_backup.py create --out ~/RareGenXAI-research-backup.zip
python scripts/phase10_backup.py verify --archive ~/RareGenXAI-research-backup.zip
python scripts/phase10_backup.py restore --archive ~/RareGenXAI-research-backup.zip --destination ~/RareGenXAI-restore-test
```

The ZIP has per-file SHA-256 fingerprints and a versioned manifest. Verification
rejects unexpected paths, symlink entries, duplicate entries, corrupt bytes and
undeclared result files. Restore requires an empty/new destination and does not
overwrite an installed project. Backups can still contain licensed research data;
keep them private in owner-controlled encrypted storage. Never publish this ZIP
or assume copied joblib data is safe to deserialize from an unknown source.

A separate source-code-history backup can be created locally using
`git bundle create ~/RareGenXAI-source.bundle --all` and later inspected with
`git bundle verify ~/RareGenXAI-source.bundle`. Git history may contain
sensitive material; inspect before sharing. Source-bundle generation is not
performed by this script.

Recovery drill: verify source ZIP, restore into empty folder, compare recorded
checksums, review trust/licensing, reprepare HPO/model dependencies, run quick
and full scripts, and inspect a real local demo. Merely restoring bytes does not
prove clinical validity or application correctness.

## Known release blockers

1. GitHub Actions has repeatedly failed before running job steps; the latest
   checks cannot be called passing.
2. Phase 7 fresh official-data, Phase 8 official Mac and Phase 9 institutional
   approval are incomplete or unverified.
3. Stacked Phase 5–9 PRs and independent Phase 4 review require resolution.
4. Earlier RareBench saved predictions lack complete original inference inputs
   and model bytes; no genuine matched-case DeepRare result exists.
5. Local-only demo has no public-facing authentication or clinical certification.
   Never bind it to a public interface.

## Release decision

After all technical and manual gates pass, maintainers can merge dependent
PRs in the correct order and deliberately create a candidate tag on the
accepted commit, e.g. `git tag -a v0.10.0-rc1 -m 'RareGenXAI research release candidate'`.
**This Phase 10 implementation deliberately does not publish a tag**, a GitHub
Release, or any private data. Academic supervisor and institution must approve
their own documents, signatures and claims.
