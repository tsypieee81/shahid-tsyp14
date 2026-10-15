# Results

Every file here was produced by code in `shahid/` and is stamped inside with its commit, config hash
and command. All of it is SIMULATED. Every reported number has a row in
[docs/CLAIMS_LEDGER.md](../docs/CLAIMS_LEDGER.md) (ID prefix below). The tables that collect them are
generated into [docs/RESULTS.md](../docs/RESULTS.md) by `python -m shahid.make_docs`.

## Proposal section to file

| Proposal section | Result files | Ledger IDs | Figure |
|---|---|---|---|
| 4.2 Why not a trained classifier (supervised comparison, post-hoc) | `studies/classifier_comparison/summary.json`, `test_predictions.parquet` | CLF- | `studies/classifier_comparison/*.png` |
| 4.2 Gradient-boosting forecaster test | `cp4_expected_load.json` | C4- | `figs/cp4_expected_load.png` |
| 6.1 Held-out grid, evaluated once | `cp7_heldout.json`, `cp12.json` (headline ranges) | C7-, CP12- | `figs/cp7_reliability.png` |
| 6.2 Feeder-level events, Isolation Forest, cost of safety | `cp11_eval.json`, `iforest.json`, `cp12.json` | CP11-, CP12-, CP10- | `figs/pack_2_feeder_outcomes.png`, `figs/pack_3_risk_coverage.png` |
| 6.3 Is the result a leak? | `leak_audit.json` | C7- | — |
| 6.4 Resolution limit | `cp10.json`, `cp12.json` | CP10-, CP12- | `figs/pack_1_snr_detectability.png`, `figs/cp10_boundary_axes.png` |
| 6.5 Where it weakens or fails | `cp6/*.json`, `cp6_summary.json` | C6- | `figs/cp6_robustness.png`, `figs/cp6_detectability.png` |
| 6.6 Operator load and false verdicts | `cp10.json`, `cp11_eval.json`, `cp12.json` | CP10-, CP11-, CP12- | `figs/pack_4_operator_load.png`, `figs/cp12_recheck_tradeoff.png` |
| 6.7 The learned consumption model | `cp4_expected_load.json`, `cp5_gap.json` | C4-, C5- | `figs/cp5_gap.png` |
| 6.8 Single-meter faults (negative result) | `cp8_single_meter.json` | C8- | — |
| 6.9 Sensitivity to the reporting interval (post-hoc) | `studies/reporting_interval/*.json` | CAD- | `studies/reporting_interval/cadence_summary.png` |
| 9 Repository and reproducibility | `repro_check*.json`, `repro_summary.json`, `demo_summary.json`, `decision_log_demo.jsonl` | C9-, CP11-, DEMO- | `figs/pack_5_example_day.png` |
| Number checker limits | `checker_limits.json` | CHK- | — |

## Phase 2 protocols (registered in `docs/process/protocols/`)

| Folder | Protocol | Result files | Ledger IDs |
|---|---|---|---|
| `p1/` | 01 size-dependent prior and gate rows; 04 prior after the split | `p1_dev.json`, `p1_params.json`, `p15_dev.json`, `p15_params.json` | P2D-01 to P2D-03 |
| `p2/` | 02 evidence version 2 (development); 05 joint confirmatory batch on rural2 and semiurb4 | `v2_select.json`, `v2_dev.json`, `v2_params.json`, `confirm.json` (`cache/` not tracked) | P2D-06, P2D-07, P2C-01 to P2C-06 |
| `p3/` | 06 single-meter faults for meters that still report | `p3_dev.json` | P2D-08 |
| `p5/` | 03 split silent groups by feeder | `p5_dev.json` | P2D-04, P2D-05 |
| `p7/` | 07a reliability of P(comms); 07b people-study item pool | `reliability.json`, `people_key.json` | P2D-09 |
| `p8/` | 08 shared learning between simulated nodes | `shared.json` | P2D-10 |

## Studies, demo and diagnostics

| Folder | Content | Ledger IDs |
|---|---|---|
| `tunisia/` | Tunisia study summary outputs, copied from branch `tunisia-study` commit 1cbf994 (`docs/tunisia/README.md`) | TN- |
| `studies/reporting_interval/` | reporting-interval study (15/30/60 min), copied from branch `cadence-study` commit 6853c6e | CAD- |
| `studies/classifier_comparison/` | supervised-classifier comparison | CLF- |
| `demo/` | seven replayed console scenarios (`python -m shahid.demo_day`, `python -m shahid.demo_eval`) | — |
| `business/` | business-case model: operator workload, avoided false outage verdicts, compute timing, storage, cost formulas (`python -m shahid.business_model`) | BUS- |
| `diagnostics/` | post-hoc diagnostic of net-exporting silent groups (`python -m shahid.diag_export`) | EXP- |

## Other files

- `records/`: per-episode verdicts of every method, the input to the tables above. The per-group
  files (`*__groups.parquet`) are not tracked; `python -m shahid.records` rebuilds them.
- `studies/classifier_comparison/features/`: not tracked; `python -m shahid.classifier_study features`
  rebuilds it.
- `cp1_*.json` to `cp5_*.json`, `audit*.json`, `smoke.json`, `detector_params.json`: development
  stages, described in `docs/process/`. `detector_params.json` holds the frozen parameters.
- `check_numbers_before.txt`, `check_numbers_after.txt`: number-checker output from an earlier
  documentation pass (ledger CP11-).

Figures and tables contain information from the SimBench database, made available under the ODbL 1.0.
