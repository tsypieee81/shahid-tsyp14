# Reproduce

Each stage is a Python entry point that writes a stamped JSON (commit, config hash, date) under `results/`.

| Stage | Command | Rough time, ESTIMATE (4 workers) |
|-------|---------|------|
| SimBench facts | `python -m shahid.cp1_facts`, `python -m shahid.cp1_diversity` | 10 min |
| Generator checks and fault-free dataset | `python -m shahid.cp3_checks` | 5 min |
| Expected-load study | `python -m shahid.cp4_expected_load` | 15 min |
| Gap analysis, detector comparison | `python -m shahid.cp5_gap`, `python -m shahid.cp5_compare` | 10 min (cp5_compare measured 518 s, AU-08) |
| Detectability and robustness | `python -m shahid.cp6_sweep`, `python -m shahid.cp6_summary` | 2–3 h |
| Held-out evaluation, leak audit | `python -m shahid.cp7_heldout`, `python -m shahid.leak_audit` | 17 min (measured 906 + 88 s, AU-08) |
| Single-meter faults | `python -m shahid.cp8_single_meter` | 5 min |
| Decision-log demo (G2/G3) | `python -m shahid.explain` | 1 min |
| Figures | `python -m shahid.figures` | 1 min |
| Everything, in order | `python -m shahid.reproduce` | several hours |
| Quick reproducibility check (fresh clone) | `python -m shahid.verify_repro` | 10 min |
| Headline reproducibility check (fresh clone) | `python -m shahid.verify_repro --long` | 30 min (measured, AU-08) |
| Audit analysis | `python -m shahid.audit`, `python -m shahid.audit_faults` | 2 min |
| Separated policy components, small-group uncertainty, break-even | `python -m shahid.cp12` | 1 min |
| Classifier comparison (post-hoc study; needs `requirements-dev.txt`) | `python -m shahid.classifier_study features`, then `python -m shahid.classifier_study run` | 10 min, then 2 min (2 workers) |
| Number integrity (documents vs ledger vs result files) | `python -m shahid.check_numbers` | 1 min |
| Check an external document, e.g. the proposal | `python -m shahid.check_numbers --doc proposal.docx [--ledger extra.md] [--results a.json]` | seconds |

Times are an ESTIMATE from watching runs on one laptop, not measured benchmarks, except where a ledger row
is cited. The environment variable `SHAHID_WORKERS` caps parallelism (default 4).

## What has been verified in a fresh clone

| Stage | Fresh-clone status | Evidence |
|-------|--------------------|----------|
| test suite at that commit, cp1_diversity, cp3_checks, cp5_gap, decision-log demo, fault-free dataset tables | identical | `results/repro_check.json` (C9-02) |
| cp5_compare + detector_params, CP6 nominal cell, cp7_heldout, leak_audit | identical | `results/repro_check_long.json` (AU-08) |
| every stage, end to end (`--all`), main working copy with its existing environment | 163 of 178 files identical; all 15 differences non-scientific and explained (fixed since) | `results/repro_check_all.json`, ledger CP11-REPRO |
| every stage in a fresh clone (`--all`, own venv from `requirements.lock`, same laptop) | 177 of 178 files identical; the one difference, `cp10.json`, only lacked rows for families added later | `results/repro_check_fresh_clone.json`, ledger CP11-REPRO2 |
| Linux | test suite passes in GitHub Actions (ubuntu-latest and windows-latest, Python 3.11); the full reproduction (`--all`) was not run on Linux | private-repo CI run |

All verified runs were on Windows 11 with Python 3.11.7; macOS is NOT RUN. Commit hashes in the ledger,
result stamps and documents refer to this repository's history.
