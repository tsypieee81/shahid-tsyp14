# Protocol 00 — Common frame for the Phase 2 studies (registered before any Phase 2 run)

Registered 2026-10-14. Applies to protocols 01–10 in this folder. Everything here is SIMULATED on
SimBench German benchmark grids; nothing is Tunisian data or field validation.

## 1. Fixed points
- **Version 1 is frozen**: `shahid/detect.py`, `results/detector_params.json`, `docs/eval_protocol.md`.
  Every candidate is a separate, named method in its own module; version 1 is always run alongside
  as the reference.
- **Safety selection rule (v3, decision 0003)** for any threshold or variant choice: missed-outage
  rate ≤ 0.05, false-outage rate ≤ 0.05, fault-free false outages ≤ 0.001 per meter-day; among
  feasible settings, least abstention. If no setting is feasible, report that and recommend version 1.
- **Episode matching**: addendum D (`evaluate.match_episodes`, same onset, Jaccard ≥ 0.5). Metrics
  as in `docs/eval_protocol.md` (Metrics section), with bootstrap 95% intervals (1 000 resamples,
  stratified by cause) and Wilson intervals for rates of rare events.
- **Mechanism language** (binding): the 10:00 confident-wrong verdict is a powered meter merged into
  the outage group that supplied the whole residual; net export only widened the comms hypothesis;
  the showcase negative gap is correct physics and was decided correctly (finding 09).

## 2. Data
- **Development** (selection only): grid `1-LV-semiurb5--0-sw`. Fitting on the fault-free year
  (seed 1) training weeks (week mod 4 ∈ {0, 1}); selection on validation weeks (week mod 4 = 2) of the
  CP5 event seeds 101–103 and of the fault-free year. Existing families may be reused on development.
- **Confirmatory grids, never used for any detector outcome**: `1-LV-rural2--0-sw` (99 loads,
  primary) and `1-LV-semiurb4--0-sw` (41 loads, secondary). Reserved since the cadence study
  (`docs/studies/reporting_interval/V2_CANDIDATES.md`). `1-LV-rural1--0-sw` (13 loads) is too small
  and is not used.
- **One confirmatory batch (protocol 05)** evaluates every frozen candidate of protocols 01, 02, 03
  and 06 once, together, on both grids. No candidate is evaluated on these grids before all are
  frozen. This resolves the conflict that both "a fourth grid" (P1/P5) and "two untouched grids" (P2)
  are needed while only two untouched grids exist.
- **New seeds** (never used before): development extras 9xx; confirmatory 8xx (protocol 05).
  Seeds already used: 1, 101–103, 201–202, 301–303, 401–458, 501–502, 701–721.

## 3. Status of results
- Development numbers are labelled **development, selection data**. Confirmatory numbers are
  labelled **confirmatory, run once**. A rerun after a bug fix is reported with the reason and both
  outputs.
- A hypothesis is **supported** if its pre-registered criterion holds, **not supported** otherwise,
  and **harmful** if a safety limit is broken. Negative results are reported in full.
- Every reported number gets a ledger row before it appears in any document; each protocol ends in a
  finding doc in `docs/process/findings/`.

## 4. Compute budget
- Datum: full fresh-clone reproduction ≈ 8 h on one laptop for 178 result files (ledger
  CP11-REPRO2); unit costs `cp5_compare` 945 s and `cp7_heldout` 1 121 s (ledger FC-01). At most two
  workers.
- Each protocol states an ESTIMATE in wall-hours. If an estimate exceeds ~10 h, the reduction is
  written into that protocol before its run.

## 5. Deviations
Any change after registration is committed as a dated addendum to the protocol concerned, before the
run it affects, and says whether development or confirmatory data had been seen.
