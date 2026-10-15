# CP0 repository audit (2026-10-05)

Method: listed every file outside `.git`, checked git state. Nothing executable existed to run.

| Path | Classification | Note |
|------|----------------|------|
| `.vscode/settings.json` | DOCUMENTATION-ONLY (editor colours) | not project code |

- The folder was not a git repository. Initialised `main`, committed the pre-existing state as-is, created working branch `phase1`.
- No proposal, handbook, results file, code or tests exist. Nothing to quarantine; the retraction of earlier design figures is recorded in `docs/CLAIMS_LEDGER.md`.
- Tooling found: Python 3.11, 3.13, 3.14 (py launcher), uv 0.9.30, git 2.53. 24 logical CPUs, 32 GB RAM, Windows 11.
