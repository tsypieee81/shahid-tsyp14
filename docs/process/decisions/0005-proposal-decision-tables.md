# 0005: Records behind the proposal's decision tables (Sections IV-C and IV-D)

Written 2026-10-13. The proposal's Tables "Engineering decisions" and "Considered and not pursued"
cite no ledger IDs; this file names the record behind every row. A row whose record was missing was
dropped or trimmed, as listed at the end.

## Engineering decisions (Section IV-C)

| Row | Record |
|---|---|
| Diagnose silent groups, not per-meter anomaly scores | Proposal Section VI-A ("rules based on the silence pattern are near chance"); leak audit C7-06, `docs/process/findings/07_heldout.md` |
| Simulate on benchmark networks with AC power flow | `docs/process/decisions/0001-grid-and-diversity.md`; balance closes to at most 6e-8 MW, C1-05 |
| Per-customer variation | `docs/process/findings/01_simbench_reality.md` ("exact by construction"), C1-06; diversity range CP10-T7 |
| Meter on the low-voltage side | `docs/process/findings/01_simbench_reality.md` (metering point); line losses C1-04, C3-04; balance noise against forecast error, `docs/process/findings/05_detectors.md` |
| Anchored own-history forecast | `docs/process/findings/04_expected_load.md` (median, mean, ratio, transfer, anchored; anchored best in every cell), C4-01, C4-05; gradient boosting C4-06; `docs/process/decisions/0002-expected-load-estimator.md` |
| Student-t likelihoods | C5-01 (skew 0.71, excess kurtosis 1.58), `docs/process/findings/05_detectors.md` |
| Safety-first selection rule | C5-03 (419 of 1 051 fault-free silent groups called outages), C5-04 (missed-outage rate 0.366), `docs/process/decisions/0003-detector-and-thresholds.md`; files `results/cp5_compare_v1_unconstrained.json`, `results/cp5_compare_v2_fa_budget_only.json` |
| Thresholds frozen, held-out run once, third grid | `docs/eval_protocol.md`, `docs/process/checkpoints/CP7.md`, CP11-T2f; leak audit C7-06 |
| Human approves dispatch; provisional closure | CP10-T0 (rule R3 closed real outages), proposal Section V-C |
| Template explanations | `tests/test_explain.py` |
| Claims ledger and number check | `docs/CLAIMS_LEDGER.md`, `shahid/check_numbers.py`, CHK-01 |

## Considered and not pursued (Section IV-D)

| Row | Record |
|---|---|
| Per-meter anomaly detector (Isolation Forest) | CP10-T6, CP11-T1c |
| Supervised classifier | CLF-01 to CLF-12, `docs/studies/classifier_comparison/README.md` |
| Deep learning | project scope fence; the small neural network in CLF-02, CLF-06 |
| Reshaping profiles to look Tunisian | project scope fence; `docs/LIMITATIONS.md` item 4 |
| Planned cuts from the schedule | Proposal Section I-B (press reference [5]); coordinator in Section V-D |
| Last-gasp messages | project rules ("optional, default off, headline results never depend on them"); `docs/process/AUDIT.md` ("never exercised in any experiment"); `docs/ASSUMPTIONS.md` A-NOBACKFILL |
| Meter-count gate as the registered method | `docs/process/decisions/0004-v11-resolution-gate.md`, CP12-T2a |
| Language-model explanations | project scope fence; `tests/test_explain.py` |
| Dashboard, streaming, cloud | project scope fence |
| Hardware in Phase 1 | project scope fence; proposal Section II-B |
| Storage scenarios | `docs/process/decisions/0001-grid-and-diversity.md`, `docs/process/findings/01_simbench_reality.md` ("not physical behaviour over a time series"), `docs/ASSUMPTIONS.md` A-STORAGE |

## Dropped or trimmed for lack of a record

- "autoencoder" removed from the anomaly-detector row: no autoencoder was ever built or tested.
- Last-gasp row: "unknown whether the deployed meters send them" removed; no record states it.
  Replaced by the recorded reasons (project rule; off in every experiment).
- Hardware row: "safety and time" removed; no record gives those reasons. Replaced by the recorded
  scope decision.
- Meter-location row: "about 0.2% of load" not printed, because the proposal does not state it
  (C1-04, C3-04 hold the values).
- Diagnose row: "crew or ticket" became "a crew or no crew" (the proposal's wording, Section I-B).
