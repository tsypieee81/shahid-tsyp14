# CP0 — Repository audit and integrity quarantine

## Implemented
- Git repo, branch `phase1`; project integrity rules; `docs/ASSUMPTIONS.md`, `docs/REUSE.md`, `docs/CLAIMS_LEDGER.md`, `docs/process/PROGRESS.md`; `docs/process/findings/00_repo_audit.md`.

## Measured
- No numeric results. File count outside `.git` before work: 1.

## Failed or surprising
- The repository was empty: no earlier proposal, results or code. No banners needed.

## Assumptions remaining
- H-core, P1–P7 all untested.

## Decision and recommendation
- Proceed to CP1 using a project-local venv built with uv.
