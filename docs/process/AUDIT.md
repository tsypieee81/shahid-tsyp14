# Scientific audit before the Phase 1 freeze (2026-10-07)

Scope: everything in branch `phase1` up to commit e870a97. Every number below is read from a result
file named next to it. Ledger IDs AU-01 to AU-08 are in `docs/CLAIMS_LEDGER.md`. New audit code:
`shahid/audit.py` (read-only analysis of existing results), `shahid/audit_faults.py` (fault-model
and conservation check), and `shahid/verify_repro.py --long` (fresh-clone re-run of the headline
stages).

## 1. Current state (verified by running, not by reading docs)

| Component | Status | Implemented? | Executed? | Evidence file | Main limitation |
|-----------|--------|:---:|:---:|---------------|-----------------|
| SimBench loading, AC power flow, truth balance | IMPLEMENTED + MEASURED | yes | yes | results/cp1_simbench_facts.json, tests/test_balance.py | German benchmark profiles |
| Customer diversity model (knob d) | IMPLEMENTED + MEASURED | yes | yes | results/cp1_diversity.json | uncalibrated against real households |
| Physical outage (open line, re-solve) | IMPLEMENTED + MEASURED | yes | yes | results/cp3_checks.json, results/audit_faults.json | no fuse dynamics, balanced 3-phase only |
| Comms failure, concentrator failure, loss, delay, backlog | IMPLEMENTED + MEASURED | yes | yes | results/audit_faults.json, results/cp3_checks.json | parameters are assumptions |
| Real load change (hard negative) | IMPLEMENTED + MEASURED | yes | yes | results/audit_faults.json, results/cp6/hn_comms_with_load_change.json | — |
| Unmetered energy (constant / load-shaped) | IMPLEMENTED + MEASURED | yes | yes | results/cp3_checks.json, results/audit.json | added after the power flow (≤ 1.8% error, C3-02) |
| Meter and transformer-meter error | IMPLEMENTED + MEASURED | yes | yes | results/cp6/meter_noise_*.json, tmeter_gain_*.json | not from any standard |
| Last-gasp messages, outage backfill | IMPLEMENTED + NOT YET MEASURED | yes | no (default off) | shahid/observe.py | never exercised in any experiment |
| Interval voltage column | IMPLEMENTED + NOT YET MEASURED | yes | emitted, never used | shahid/scenario.py | detector ignores it |
| Data contract and no-leak test | IMPLEMENTED + MEASURED | yes | yes | tests/test_no_leak.py (mutation-checked) | — |
| Expected-load estimators (5) + gradient-boosting test | IMPLEMENTED + MEASURED | yes | yes | results/cp4_expected_load.json | ratio estimator fails on PV networks |
| Gap (balance) noise model | IMPLEMENTED + MEASURED | yes | yes | results/cp5_gap.json | load-shaped unmetered energy breaks it |
| Detectors share, ztest, lr, bayes | IMPLEMENTED + MEASURED | yes | yes | results/cp5_compare.json, cp6/, cp7_heldout.json | small groups undecidable |
| Baselines naive, step, count, structure | IMPLEMENTED + MEASURED | yes | yes | same | — |
| Detectability and robustness sweep (30 cells) | IMPLEMENTED + MEASURED | yes | yes | results/cp6/*.json, results/audit.json | 2 seeds per cell |
| Held-out evaluation | IMPLEMENTED + MEASURED | yes | yes (once) | results/cp7_heldout.json | one held-out grid only |
| Leak audit | IMPLEMENTED + MEASURED | yes | yes | results/leak_audit.json | — |
| Single-meter faults (CP8) | IMPLEMENTED + MEASURED | yes | yes | results/cp8_single_meter.json | stuck-meter result is a simulator artefact |
| G2 record, template explanation, hash-chained log | IMPLEMENTED + MEASURED | yes | yes | tests/test_explain.py, results/decision_log_demo.jsonl | — |
| G3 escalation table | IMPLEMENTED + NOT YET MEASURED | yes | demo only | configs/escalation.yaml | policy never evaluated or operator-validated; rule R3 is unsafe (see LIMITATIONS item 16 and CP10 Task 0 in docs/process/checkpoints/CP10.md) |
| G4 knowledge sharing | PROPOSED | no | no | docs/PRELIMINARY_DESIGN.md Section 5.4 (the earlier note docs/G4_knowledge_sharing.md was merged into it during submission packaging) | design note only |
| `python -m shahid.smoke` (README quickstart) | IMPLEMENTED + MEASURED | yes | yes | results/smoke.json, tests/test_smoke.py | **was broken** after the CP5 detector change; fixed and now tested |
| Full `python -m shahid.reproduce` | IMPLEMENTED + NOT YET MEASURED | yes | never end to end | shahid/reproduce.py | several hours |
| Fresh-clone checks | IMPLEMENTED + MEASURED | yes | yes | results/repro_check.json, results/repro_check_long.json | headline stages identical; 29 CP6 cells and CP4 not re-run in a clone |
| CP2 smoke record (C2-01) | INVALID / REMOVE as a performance figure | — | — | results/cp2_smoke.json | superseded detector; kept as history only |
| "Accuracy when decided" as a stand-alone headline | INVALID / REMOVE | — | — | old docs/RESULTS.md | hides 28–40% abstention |
| Stuck-meter 100% detection, 0 false alarms | INVALID / REMOVE as a result | — | — | results/cp8_single_meter.json | the simulator never repeats readings |

## 2. Same-episode comparison of all methods (coverage = 1 − abstention)

Held-out grid urban6, test weeks, seeds 301–303, 109 outage and 155 comms episodes, identical
observed inputs for every method (`results/audit.json` → `same_episode_tables.cp7_heldout_urban6`):

| Method | Coverage | Accuracy when decided | Outage recall | Comms recall | False outage | Missed outage | Balanced | Fault-free false outages per meter-day |
|--------|------|------|------|------|------|------|------|------|
| bayes | 0.723 | 0.995 | 0.670 | 0.755 | 0.000 | 0.009 | 0.712 | 0.0010 |
| ztest | 0.636 | 0.994 | 0.615 | 0.645 | 0.000 | 0.009 | 0.630 | 0.0002 |
| lr | 0.720 | 0.963 | 0.716 | 0.677 | 0.039 | 0.009 | 0.697 | 0.0038 |
| share | 0.720 | 0.963 | 0.725 | 0.671 | 0.045 | 0.000 | 0.698 | 0.0045 |
| naive baseline | 0.871 | 0.943 | 0.890 | 0.774 | 0.065 | 0.028 | 0.832 | 0.0104 |
| step baseline | 1.000 | 0.682 | 0.752 | 0.632 | 0.368 | 0.248 | 0.692 | 0.0629 |
| count baseline | 1.000 | 0.545 | 0.826 | 0.348 | 0.652 | 0.174 | 0.587 | 0.0039 |
| structure baseline | 0.765 | 0.604 | 0.624 | 0.348 | 0.394 | 0.174 | 0.486 | 0.0031 |

The same ordering holds on CP5 validation and CP6 nominal (`audit.json`). On balanced score bayes
is ahead of ztest in all three: 0.631 / 0.583 / 0.712 against 0.577 / 0.534 / 0.630.

**Strongest method under this project's constraints: bayes.** It has the same coverage as lr and
share (0.72), but no false outages and about 4× fewer fault-free false alarms. **It is not the best
on raw balanced score.** The naive baseline is higher (0.832) because it decides 87% of episodes,
at the cost of 6.5% false outages, 2.8% missed outages and 10× the fault-free false alarms. Which
is "better" depends on the cost of errors. We chose safety: missed and false outages are capped and
abstention goes to a human (decision 0003). The z-test is the simplest safe alternative, with fewer
false alarms but 9 points less coverage.

## 3. Coverage–performance tradeoff
`results/figs/audit_risk_coverage.png` plots every swept threshold setting on CP5 validation
(`audit.json` → `risk_coverage_cp5`). Requiring error-when-deciding ≤ 2%, false outages ≤ 1% and
missed outages ≤ 5%, the highest reachable coverage is 0.735 (bayes), 0.720 (ztest) and 0.712
(share with a 2 kWh minimum). lr and all four baselines cannot meet these limits at any setting.
Beyond about 0.74 coverage, every method pays in false or missed outages. **The tradeoff is a
property of the evidence, not of one threshold.** No headline in this repository may now quote
accuracy-when-decided without coverage.

## 4. Held-out verification

| Question | Finding | Evidence |
|----------|---------|----------|
| 1. Grid excluded from selection? | Yes. urban6 was chosen on network facts only (CP1). No detector or episodes ran on it before CP7. Its simulated world was first created at 2026-10-07 09:41, during the CP7 run | `cache/truth_63fa55cd894e.npz` creation time; decision 0001 |
| 2. Thresholds frozen before held-out results? | Yes. `results/detector_params.json` last changed at b24addb (10-06 11:23). The CP7 run was at 9de959a (10-07). The protocol was committed at 6f9d9e0 (10-06 11:32) | `git log` |
| 3. Hyperparameters frozen? | Yes. Between b24addb and 9de959a the only code changes are the worker cap (`shahid/world.py`) and a crash-only slicing fix in `shahid/baselines.py`. The detector, evaluation, simulation and configs are byte-identical | `git diff b24addb 9de959a` |
| 4. Results inspected before selection? | No CP7 result existed before selection. Development and validation results were inspected, which is legitimate | timeline |
| 5. Assumptions changed after held-out? | No method or threshold change. Afterwards: documentation, the CP8 study, the smoke fix, the escalation wording (AI → AUTOMATED), two extra unmetered cells. None feeds back into CP7 | commits after 9de959a |
| 6. Seeds independent? | Event and observation seeds 301–303 (event streams 1301–1303) are disjoint from every earlier seed (1, 101–103, 201–202, 999). The customer-diversity world seed is 0 everywhere. On urban6 that gives a different customer set and array shape, so it is a different draw | `shahid/episodes.py`, `shahid/scenario.py` |
| 7. Scenarios independent? | Held-out urban6: yes. **Dev-semiurb5 "test weeks": not an independent world.** Same simulated customers as all development, with unseen weeks and seeds. It is a held-out-period result, not held-out data | `shahid/cp7_heldout.py` |
| 8. Shared generated data? | Held-out urban6: none. Dev-semiurb5 test: the world cache is shared with development, as stated above | cache keys |

**Verdict: the urban6 result meets strict hold-out methodology. The dev-semiurb5 test-week result
must be described as held-out period and seeds only.** No rerun was needed.

## 5. Leakage trace

`truth (world.py: power flow)` → `shahid/observe.py` (meter and transformer error, delivery lags from
truth-side outage and comms masks) → `observed/` tables (meter_id, interval_start, energy_kwh,
arrival_ts, voltage_v; transformer interval_start, energy_kwh) + `context/` (concentrator,
pv_kw, zones) → `shahid/detect.py` (imports only numpy, pandas, scipy, pathlib; reads only those four
tables) → `shahid/evaluate.py` (the only module that reads labels).

| Hidden item | Can the detector reach it? | Why not |
|-------------|------|---------|
| true fault type, outage schedule | no | in `labels/` only. No observed column depends on cause except physically (missing rows, transformer energy) |
| true comms state | no | only its consequence: rows missing or arriving late |
| true customer load | no | only noisy, quantised, delayed readings |
| hidden labels | no | `tests/test_no_leak.py`; audit found no input column shared with truth or labels (`leak_audit.json`) |
| future observations | no | every evidence array is masked with `arrival ≤ decision time`; history uses earlier rows only; backlog arrives after the decision |
| variables made only because the answer is known | none found | outaged meters send nothing (same as real unpowered meters); last-gasp and backfill are off |

Controls on held-out data: shifting the transformer series drops outage recall from 0.641 to 0.103.
A transformer series without these outages drops it to 0.026 (C7-06). **No leakage found; nothing
to fix or rerun.**

## 6. Fault model (`results/audit_faults.json`; same world and seed, with and without the event, 8-interval window)

| Scenario | Physical system changes | Observations change | Transformer truth changes | Meter truth changes | Detector sees fault label |
|----------|:---:|:---:|:---:|:---:|:---:|
| Physical outage (line opened, re-solved) | yes | yes | yes (8.523 → 2.030 kWh) | yes (6.490 → 0.000 kWh) | no |
| Comms failure (zone) | no | yes | no | no | no |
| Concentrator failure | no | yes | no | no | no |
| Real load change × 2 | yes | yes | yes (8.523 → 15.022 kWh) | yes (6.490 → 12.979 kWh) | no |
| Unmetered energy, load-shaped 5 kW | no network change | yes | yes (8.523 → 20.829 kWh) | no | no |
| Stuck meter (CP8) | no | yes (readings frozen) | no | no (true load still varies) | no |

Every event changes exactly what it claims. Nothing is a data deletion pretending to be a
physical event.

## 7. Energy-balance physics
- Units: power flow in MW; energy per interval kWh = MW × 1000 × 0.25 (`grid.DT_H`). Profile values
  are treated as interval means (A-INTERVAL).
- Sign: LV delivered = −`res_trafo.p_lv_mw` (test-verified). Metering point: LV side, so
  transformer losses are outside the balance. PV sits behind customer meters, and readings are
  net (can be negative).
- Losses are not double-counted. Line losses stay inside the observed gap, which the detector
  learns from the last day's history. An outage removes the isolated part's losses (at most
  0.047 kWh per interval, C3-01).
- One interval of the fault-free simulation, 2016-04-25 10:00 (`audit_faults.json`):

| Quantity | kWh |
|----------|-----|
| customer load | 18.707 |
| PV generation | 15.050 |
| line losses | 0.020 |
| load − PV + losses | 3.677 |
| transformer LV delivered (truth) | 3.677 (residual −1.8e-7) |
| transformer losses (outside LV meter) | 0.435 |
| HV side = LV + transformer losses | 4.113 |
| observed transformer reading | 3.690 |
| observed sum of the 103 meters that reported | 3.639 |
| observed gap | 0.051 |

- Information unavailable in reality: the detector uses the zone map (GIS connectivity), the
  concentrator map and installed PV, which utilities hold. It also uses an LV transformer meter,
  whose existence in Tunisia is unverified (P7).

## 8. Expected-load estimation
- **Estimator**: per meter, the same-slot mean over the previous 14 days of its own readings that
  had arrived by decision time, plus ρ(lead) × the group's deviation in the last interval before
  silence. Uncertainty is a per-lead multiplier of sqrt(Σ sd²). ρ and the multipliers are fitted
  once on the fault-free year's training weeks (`detect.fit`, observed data only).
- **Leakage**: none backwards. History rows are strictly earlier, masked by arrival time. Earlier
  events' silent intervals are missing and skipped by the nan-mean. Real load changes inside the
  history are kept, as they would be in reality.
- **Distinguishable customers**: SimBench gives 10 shapes for 104 loads (exact copies, C1-06). With
  copies, the neighbour-based estimator looks good (d = 0). Under the diversity model the advantage
  disappears (C4-01). Per-customer ML on raw SimBench would mostly learn the copies.
- **ML**: gradient boosting is within 1% of group energy of the simple estimator at d ≥ 0.25 (C4-06).
  ML is not used.

## 9. Detectability boundary (`results/audit.json` → `detectability`; figure `results/figs/audit_detectability.png`)

> **Superseded by CP10 (post-hoc, 2026-10-07):** the 16% / 32% values are bin edges. The continuous estimate of the share at which P(correct) reaches 0.90 is 0.160 (0.124–0.207) nominal, 0.083 (0.059–0.119) on the held-out grid, and 0.114 (0.080–0.165) on the development grid's test weeks. A signal-to-noise axis is more consistent across conditions. See `docs/RESULTS.md` §1 and ledger CP10-T3.
Boundary = the smallest silent-energy share above which every bin has correct cause ≥ 90% and
wrong cause ≤ 2%:

| Condition | Boundary (share of typical transformer energy) |
|-----------|------|
| nominal; diversity d = 0 / 0.25 / 1; history 7 / 28 days; meter noise × 0 / 3 / 10; transformer gain error 0 / 1%; constant unmetered 2–10 kW; load-shaped unmetered 1 kW; PV × 0 / 2 / 3; non-aligned concentrators; concentrator = zone; night | 16% |
| midday PV; comms during a real load change; 10% packet loss; transformer gain error 2%; load-shaped unmetered 2, 3, 5 kW | 32% |
| load-shaped unmetered 10 kW; simultaneous outage + comms failure | none (no bin meets the criterion) |

- Below 1% silent share, the nominal detector decides 0 of 63 episodes (always abstains).
- By silent-meter count (nominal): correct cause rises from 0.23 for single meters (74% abstained)
  to 0.83 for 20–40 meters (17% abstained). Wrong cause stays ≤ 3% in every size bin.
- Expected-load uncertainty (diversity) moves the curve but not the 16% boundary. Abstention
  rises from 34% (d = 0) to 52% (d = 1).

**Answer:** in this simulation a comms failure is distinguishable from an outage when the silent
customers would normally draw at least about 16% of the transformer's energy over the 30–90
minute decision window (32% under adverse conditions). Below about 1% it is not distinguishable
from the available observations, and abstention is the intended behaviour.

## 10. Unmetered energy (synthetic assumptions, not Tunisian measurements)
Injected after the power flow into the true transformer energy (≤ 1.8% error vs a real load,
C3-02). Mean transformer energy is about 43.8 kW (C3-04: 384 758 kWh / 8 784 h).

| Unmetered energy | Coverage | False outage | Missed outage | Accuracy when decided | Brier |
|-----|------|------|------|------|------|
| none (nominal) | 0.599 | 0.000 | 0.013 | 0.990 | 0.075 |
| constant 2 / 5 / 10 kW | 0.599 / 0.597 / 0.597 | 0 | 0.013 | 0.990 | 0.075 |
| load-shaped 1 kW (2.3% of mean) | 0.581 | 0.015 | 0.017 | 0.972 | 0.103 |
| load-shaped 2 kW (4.6%) | 0.556 | 0.019 | 0.038 | 0.949 | 0.135 |
| load-shaped 3 kW (6.8%) | 0.560 | 0.045 | 0.063 | 0.903 | 0.162 |
| load-shaped 5 kW (11%) | 0.534 | 0.034 | 0.122 | 0.857 | 0.206 |
| load-shaped 10 kW (23%) | 0.538 | 0.045 | 0.241 | 0.743 | 0.277 |

- Constant unmetered energy has no effect: the recent-gap baseline absorbs it.
- Load-shaped unmetered energy raises **both** error types and degrades calibration (Brier 0.075 →
  0.277). Abstention grows only slightly, so the detector does not know it is wrong.
- **Failure boundary**: the 5% missed-outage constraint breaks between 2 and 3 kW of load-shaped
  unmetered energy, about 5–7% of mean transformer energy.

## 11. CP8 (single meters)
Already run (C8-01 to C8-03). Gain, bias and noise faults on one meter are detected in at most 20%
of 7-day episodes. **The approach works on groups, not on individual-meter anomalies.** The
stuck-meter result is an artefact.

## 12. Reproducibility
- Quick check (C9-02): a fresh clone and a fresh venv from `requirements.lock` (Windows 11, Python
  3.11.7). 14/14 tests pass. cp1_diversity, cp3_checks, cp5_gap, the decision-log demo and all six
  fault-free dataset tables are identical.
- Long check (AU-08): in the same kind of fresh clone at dac48a2, cp5_compare (with the frozen
  `detector_params.json`), the CP6 nominal cell, cp7_heldout and leak_audit regenerate
  **identically** (stamps excluded). Runtimes with 4 workers: 518, 170, 906 and 88 s. Command:
  `python -m shahid.verify_repro --long`.
- Not re-run in a clone: the other 29 CP6 cells and CP4 (same code paths; about 2–3 h).
- Dependency versions: `requirements.txt` (top level) and `requirements.lock` (full freeze).

## 13. Which claims survive

| Claim | Verdict | Evidence |
|-------|---------|----------|
| A. "We built an outage detector." | **Not supported as worded.** We never test outage detection independently of meters going silent. We classify silences. Do not use | — |
| B. "We distinguish physical outages from communication failures." | **Supported conditionally**: in simulation, for silent groups above the detectability boundary. On the held-out grid, 67% of outages and 75% of comms failures are classified correctly, and the rest are mostly abstained | C7-01, AU-03 |
| C. "Uncertainty-aware diagnosis with abstention." | **Supported, with a caveat.** Errors fall with abstention along a measured tradeoff; on the held-out grid there are no false outages at 72% coverage. Caveat: mid-range probabilities are noisily calibrated, and confident errors happen (demo 0.996 wrong; load-shaped unmetered energy) | AU-02, C7-05, C9-01, AU-04 |
| D. "We quantify the detectability limit." | **Supported; the strongest claim.** [CP10: continuous estimate 0.160 (0.124–0.207) nominal, 0.083 held-out; superseding the bin edge] Boundary about 16% of transformer energy (32% under adverse conditions, none in two failure cases); undecidable below 1% | AU-03 |
| E. "We improve over simple baselines." | **Supported on safety metrics only.** 0 vs 6.5% false outages and 0.0010 vs 0.0104 fault-free false alarms against the best baseline. **Not on balanced score**: naive 0.832 vs 0.712 | AU-01 |

## 14. Defensible contributions
1. **A measured detectability boundary** for outage-vs-comms diagnosis from transformer energy
   balance, with how it moves under diversity, transformer-meter error, PV and unmetered energy.
2. **Abstaining diagnosis with controlled false outages**: zero false outages on a held-out grid at
   72% coverage, with frozen thresholds, beating the baselines on false outages and false alarms.
3. **An evaluation design where topology cannot cheat**: outages and comms failures share silent
   sets, so structure-only rules are near chance (balanced 0.49–0.59 held-out). The leak audit
   shows the decisions come from the transformer physics.

Not claimed: novelty (no full literature review), robustness in general (two named failure modes),
generalisation beyond one held-out grid, real-time operation, Tunisian relevance, "AI".

## 15. Technology not added
No language model, retrieval-augmented generation, SHAP, dashboard, streaming, cloud, hardware or deep learning. The ML test (CP4) showed
no need.

## 16. Corrections made in this audit
- `docs/RESULTS.md` rewritten: coverage now accompanies every accuracy figure, and the
  dev-test result is labelled held-out period only.
- Escalation label "AI" → "AUTOMATED (statistical detector)".
- `python -m shahid.smoke` was broken by the CP5 detector change. Fixed, and covered by
  `tests/test_smoke.py`.
- Two finer unmetered cells (1 and 3 kW) added to locate the failure boundary.
