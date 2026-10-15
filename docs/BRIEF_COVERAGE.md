# Brief coverage: EnergyMind Tunisia brief → this repository

One row per item of the challenge brief. Everything measured is **SIMULATED** on German SimBench
low-voltage grids; there is no utility data, no Tunisian data and no hardware. Ledger IDs refer to
[CLAIMS_LEDGER.md](CLAIMS_LEDGER.md). Every number below is a ledger value.

**Status words.**

| Status | Meaning |
|---|---|
| IMPLEMENTED+MEASURED | code exists and a stamped result is recorded |
| TESTED — NOT DETECTED | a detector was implemented and measured; it does not detect the item (negative result) |
| TESTED — NOT USEFUL IN SIMULATION | implemented and measured; the simulated signal carries no usable information |
| IMPLEMENTED | code exists; no measurement of the brief's criterion |
| DESIGN-ONLY | a written design exists ([PRELIMINARY_DESIGN.md](PRELIMINARY_DESIGN.md), the extended report); nothing built |
| OUT OF SCOPE | deliberately excluded, with the reason |
| NOT ADDRESSED | nothing exists |

## Goal 1: anomaly and bias detection

| Brief item | Status | Evidence | Brief metric in our metrics | Phase 2 plan for the gap |
|---|---|---|---|---|
| Genuine grid event vs. data-quality problem | IMPLEMENTED+MEASURED | `shahid/detect.py`; frozen version 1 over three evaluations: coverage 0.49–0.72, false-outage rate 0.00–0.00, missed-outage rate 0.00–0.01 (CP12-T5); never-used grids rural2 and semiurb4: missed 0.0093 and 0.0, false 0.0 and 0.0 (P2C-01) | precision/recall per cause, at stated coverage | calibration on utility data; merged-group handling (split by feeder, P2C-02) |
| Equipment faults and natural failures | IMPLEMENTED+MEASURED (as loss of supply only) | an outage verdict detects that a group lost supply; the cause of the fault is not diagnosed (CP12-T5) | outage recall 0.42–0.67 at coverage 0.49–0.72 (CP12-T5) | none planned: cause diagnosis needs protection or SCADA data |
| Degraded sensors (noise) | TESTED — NOT DETECTED (negative result) | single-meter study `shahid/cp8_single_meter.py`: at most 20% of injected faults detected (C8-01) | detection rate at 1% false alarms per check | voltage-neighbour and per-meter regression tested: not detected below gain × 0.5 (P2C-06); needs field voltage data |
| Biased readings (gain, offset) | TESTED — NOT DETECTED (negative result) | gain 0.5–1.5× and small biases on one meter: at most 20% detected (C8-01); per-meter gap regression detects gain × 0.5 in 0.3467 of cases on rural2 (P2C-06) | detection rate at measured false-alarm rate | as above |
| Corrupted readings | IMPLEMENTED+MEASURED (missing, delayed); wrong values TESTED — NOT DETECTED | missing and delayed readings form silent groups and are classified (CP12-T5); wrong values: C8-01 | comms recall 0.54–0.75 (CP12-T5) | range and consistency rules (DESIGN-ONLY, [PRELIMINARY_DESIGN.md](PRELIMINARY_DESIGN.md) 5.1) |
| Falsified readings | NOT ADDRESSED (Phase 2 design: persistent transformer-gap attribution) | protocol 06 uses gain and bias as falsification stand-ins (P2C-06); no adversarial falsification model exists | detection rate | adversarial model and per-meter attribution (DESIGN-ONLY) |
| Voltage | TESTED — NOT USEFUL IN SIMULATION | interval voltage is simulated; neighbour-voltage detection at most 0.0533 on rural2 (P2C-06); the benchmark holds upstream voltage fixed | detection rate | field voltage data |
| Current | OUT OF SCOPE | 15-min energy readings carry no waveform quantities | — | needs a different data source |
| Power quality | OUT OF SCOPE | same reason as current | — | needs a different data source |

## Goal 2: confidence scores and explainability

| Brief item | Status | Evidence | Brief metric in our metrics | Phase 2 plan for the gap |
|---|---|---|---|---|
| Confidence score | IMPLEMENTED+MEASURED | posterior P(comms), `shahid/detect.py` (`score`); reliable at the extremes (C7-05); mid range not calibrated over all silent groups, calibration error 0.494 (P2D-09) | reliability per probability bin | the console labels mid-range values as evidence strength, not accuracy; recalibration on utility data |
| Plain-language explanation | IMPLEMENTED+MEASURED (faithfulness); usefulness not measured | `shahid/explain.py`; `tests/test_explain.py` checks that every number comes from the verdict record | explanation quality: faithfulness by test; usefulness by people study | people study, protocol 07b, registered; results pending |
| Auditable decision log | IMPLEMENTED+MEASURED | SHA-256 hash chain, `shahid/explain.py` (`append_log`, `verify_log`); tamper test in `tests/test_explain.py`; operator log `ui/oplog.py` (C9-01) | chain verifies; one edit breaks it | log retention policy with the utility |
| Record of what was detected, concluded and why | IMPLEMENTED+MEASURED | `verdict_record`: evidence, probability, alternative cause, abstention reason (C9-01) | — | — |
| Interpretable approach | IMPLEMENTED+MEASURED | likelihood-ratio test on one energy balance; trained classifiers missed more outages under the same limits (CLF-02) | — | — |

## Goal 3: human-AI escalation and governance

| Brief item | Status | Evidence | Brief metric in our metrics | Phase 2 plan for the gap |
|---|---|---|---|---|
| Thresholds for automatic action | IMPLEMENTED+MEASURED | `configs/escalation.yaml`; the only automatic action annotates data and opens a ticket; the first automatic rule closed real outages and was made provisional (CP10-T0) | outages closed without a human | the R3 re-check and the meter-count gate are evaluated in study code (P2C-04) and are not executed by `explain.escalate`: wire them into the runtime path |
| Situations requiring human approval | IMPLEMENTED+MEASURED | rules R1, R2, R4, R5; every crew dispatch needs a person; human items per transformer-day 9.7992 under version 1 on rural2 (P2C-04) | human items per transformer-day | the escalating gate lowers this to 4.1516 on rural2 (P2C-04) once wired |
| Operator interface | IMPLEMENTED (preview) | `ui/` Streamlit console replaying simulated days: three queues, evidence card, audit view; headless render tests in `tests/test_ui_panels.py`; no operator has used it | — | operator trials |
| Over-trust and under-trust | IMPLEMENTED (devices); effect not measured | `ui/panels/trust.py`: alternative cause with every verdict, audit sample of automatic closures, fast-approval flag, track record per verdict class | override rate, approval time (not measured) | operator trials with the registered measures |

## Goal 4: shared learning across nodes

| Brief item | Status | Evidence | Brief metric in our metrics | Phase 2 plan for the gap |
|---|---|---|---|---|
| What is shared, what stays local, and why | DESIGN-ONLY (table); proof of concept IMPLEMENTED+MEASURED | design: extended report "Collective defence" and [PRELIMINARY_DESIGN.md](PRELIMINARY_DESIGN.md) 5.4; proof of concept `shahid/p8_shared.py`: sharing noise-shape parameters brought a negligible gain (P2D-10) | interval coverage and fault-free false outages at a new node | share frozen thresholds and anonymous failure signatures (DESIGN-ONLY) |
| Single-node prototype | IMPLEMENTED+MEASURED | one transformer, one detector fitted on its own fault-free history (C7-01, CP11-T2f) | — | — |

## Evaluation named by the brief

| Brief item | Status | Evidence | Our metric |
|---|---|---|---|
| Precision and recall | IMPLEMENTED+MEASURED | held-out urban6: outage recall 0.670, comms recall 0.755 at coverage 0.723 (C7-01) | recall per cause, with coverage; precision on labelled episodes is not field precision |
| False-positive rate | IMPLEMENTED+MEASURED | false-outage rate 0.0 on both never-used grids (P2C-01); fault-free 0.0004 and 0.0006 per meter-day (P2C-01) | false-outage rate; fault-free false outages per meter-day |
| Explanation quality | IMPLEMENTED+MEASURED (faithfulness); usefulness pending | `tests/test_explain.py`; protocol 07b registered | faithfulness test; people study |
| Latency | IMPLEMENTED+MEASURED | median decision latency 2 intervals after silence (C7-01); 30, 60 and 105 min at 15, 30 and 60 min readings (CAD-2) | intervals from silence to verdict |

## Phase 1 deliverables

| Deliverable | Status | Evidence |
|---|---|---|
| Proposal: scope, objectives, data and anomaly plan, design per goal | IMPLEMENTED | `proposal/` LaTeX source and its PDF build |
| Repository with dataset and code | IMPLEMENTED+MEASURED | `dataset/`, `shahid/`, `tests/`; fresh-clone reproduction 177 of 178 result files identical (CP11-REPRO2) |
| Dataset regenerable | IMPLEMENTED+MEASURED | one command per folder, `dataset/README.md`; fault-model check AU-05 |
| Anomaly generation documented | IMPLEMENTED | [anomaly_generation.md](anomaly_generation.md); single-meter fault classes in `shahid/cp8_single_meter.py` |
| README with quickstart, licence | IMPLEMENTED | `README.md`, `LICENSE` (MIT), `dataset/LICENSE.md` (ODbL 1.0) |
