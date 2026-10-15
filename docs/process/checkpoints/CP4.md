# CP4 — Expected-load study

## Implemented
- `shahid/cp4_expected_load.py`: five simple estimators plus a gradient-boosting comparison, evaluated on validation weeks across diversity d ∈ {0, 0.25, 0.5, 1}, history H ∈ {7, 14, 28} days, group sizes 1–50 and all electrical zones. It also computes prediction-interval coverage and error by hour.
- `docs/process/findings/04_expected_load.md`, `docs/process/decisions/0002-expected-load-estimator.md`.

## Measured
- C4-01 to C4-06. Anchored is best: 20% of group energy for 10 meters at d = 0.5, against 32% for the median. Calibrated intervals reach about 0.89 coverage. ML was not better beyond 1% of group energy at d ≥ 0.25.

## Failed or surprising
- Relative error falls only slowly with group size because errors are shared across customers (weather, PV). The same reason makes independent-Gaussian intervals undercover badly.
- The neighbour-ratio estimator is unusable on net-metered PV networks. Deviation transfer helps only at d = 0, consistent with the scaled-copy artefact (P2).
- The first CP4 result file was stamped dirty because the run truncated its own tracked log. Logs are now untracked and the study was rerun on clean commit 7680614.

## Assumptions remaining
- A-DIV remains the main untested assumption. All errors scale with d.

## Decision and recommendation
- Use anchored, H = 14, with uncertainty fitted on training weeks. ML is not adopted. Proceed to CP5.
