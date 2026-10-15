# CP5 — Balance validation, detector comparison and baselines

## Implemented
- `shahid/cp5_gap.py`: fault-free gap analysis (distribution, load dependence, autocorrelation).
- `shahid/detect.py`: `fit` (gap noise, anchored persistence and uncertainty per lead for groups and single meters), `evidence_table`, `decide_table`, and the methods share, ztest, lr (Student-t) and bayes (posterior with abstention band). Other missing meters are estimated with the single-meter anchored model.
- `shahid/baselines.py`: count, structure, step, naive.
- `shahid/evaluate.py`: episode matching, group truth from labels, rates, bootstrap and Wilson intervals.
- `shahid/cp5_compare.py`: fitting, threshold sweeps on validation, safety-constrained selection, difficulty breakdown, shifted-transformer sanity check, fault-free false alarms.
- `shahid/episodes.py`: deterministic episode generator. `results/detector_params.json` holds the frozen parameters.
- `docs/process/findings/05_detectors.md`, `docs/process/decisions/0003-detector-and-thresholds.md`.

## Measured
- C5-01 to C5-08. The primary detector, bayes, on validation is right 98.8% of the time when it decides. It abstains on 33.7% and never calls a comms failure an outage. It misses 3.6% of outages and issues 0.0006 fault-free false outages per meter-day. The best baseline (naive) has a false-outage rate of 0.105 and 20× more fault-free false alarms.

## Failed or surprising
- The first selection rule optimised labelled episodes and produced a detector that would raise about 4.6 false outage alarms a day from ordinary data loss. The second rule fixed that by missing 37% of outages. Both runs are kept as results.
- No detector reaches both high coverage and safety. Small or PV-cancelled silent groups are undecidable by the energy balance, and abstention is driven by expected silent energy.
- In the smoke case, a delayed meter with unusual consumption dominated the evidence. Other missing meters are now modelled with calibrated single-meter uncertainty.
- The shifted-transformer control falls below chance for bayes, because abstentions count as wrong. Its decisions collapse without a matching transformer signal, as they should.

## Assumptions remaining
- New DESIGN CHOICE: the v3 selection constraints (5%, 5%, 0.001 per meter-day) are ours, not operator-validated.
- H-core: supported for silent groups with expected energy above about 5 kWh over the decision window. Not supported below about 1 kWh (C5-07).

## Decision and recommendation
- Freeze bayes with the v3 thresholds. Proceed to CP6 robustness sweeps with frozen parameters.
