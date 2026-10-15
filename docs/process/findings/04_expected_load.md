# CP4 — Expected-load study

Source: `results/cp4_expected_load.json` (command `python -m shahid.cp4_expected_load`,
commit 7680614, config hash f282d1a2eca5). Ledger C4-01 to C4-06. Development grid semiurb5,
full 2016 year, nominal meter and comms error. 3 000 target intervals from training weeks and
3 000 from validation weeks. Groups are 200 random groups per size and all 109 electrical zones.
Targets are true energies and are used for evaluation only.

## Question
Can the energy of a silent meter, and of a silent group, be predicted from the meters' own
history and from the meters still reporting?

## Estimators
| Name | Rule | Uses |
|------|------|------|
| median | same-slot median of the last H days | own history |
| mean | same-slot mean of the last H days, with sd | own history |
| ratio | group's historical share of the other meters' energy × their current energy | reporting meters |
| transfer | mean + current deviation of reporting meters, fitted per interval as a·scale + b·PV kW and applied to the group | reporting meters + context PV |
| anchored | mean + ρ × the group's deviation in the last interval before silence (lead 2) | own history |
| gradient boosting | sklearn HistGradientBoosting on mean, pre-onset deviation, transfer deviation, sd, hour, PV kW | all of the above |

## Results (validation weeks, H = 14, error as a share of the group's true energy)

| Diversity d | Group | median | mean | ratio | transfer | anchored |
|-------------|-------|--------|------|-------|----------|----------|
| 0 | 1 meter | 0.386 | 0.405 | 1.713 | 0.359 | 0.311 |
| 0 | 10 random | 0.276 | 0.261 | 1.756 | 0.202 | 0.190 |
| 0 | 50 random | 0.267 | 0.241 | 1.098 | 0.179 | 0.178 |
| 0 | zones | 0.336 | 0.315 | 0.679 | 0.232 | 0.210 |
| 0.5 | 1 meter | 0.462 | 0.484 | 1.841 | 0.480 | 0.376 |
| 0.5 | 10 random | 0.323 | 0.298 | 1.129 | 0.304 | 0.204 |
| 0.5 | 50 random | 0.288 | 0.235 | 0.929 | 0.261 | 0.134 |
| 0.5 | zones | 0.365 | 0.324 | 0.795 | 0.338 | 0.185 |
| 1.0 | 10 random | 0.432 | 0.397 | 1.463 | 0.470 | 0.298 |
| 1.0 | zones | 0.461 | 0.386 | 0.857 | 0.518 | 0.255 |

- **Anchored is best in every cell.** At nominal d = 0.5 its MAE for 10-meter groups is 0.272 kWh per interval, against 0.432 for the median. That is 2.4% of transformer energy.
- **Errors are shared across customers.** Going from 10 to 50 meters barely lowers the relative error of the plain mean (0.298 to 0.235 at d = 0.5). Common day-level swings, PV most of all, dominate. Anchoring removes much of this shared part.
- **History length barely matters.** For 10 random meters at d = 0.5, anchored error is 0.211, 0.204 and 0.200 at H = 7, 14 and 28 days.
- **The ratio estimator fails.** Its errors exceed 100% of group energy, because PV pushes the reporting meters' net energy close to zero around midday. Transfer helps only at d = 0, where neighbours are scaled copies, and hurts at d ≥ 0.5.
- **Scaled-copy artefact (P2).** Own-history estimators are not near-perfect at d = 0, with 19–31% error, because SimBench shapes vary from day to day. The neighbour-based transfer estimator gains most at d = 0. That is consistent with copies inflating neighbour methods, and it is why diversity stays a swept parameter.

## Prediction intervals (90% nominal, validation)
- **Independent Gaussian** (±1.645 × sqrt(Σ sd²)) undercovers as groups grow. Coverage is 0.558 for 50 random meters at d = 0 and 0.718 at d = 0.5, because errors are correlated.
- **Conformal-scaled anchored** (multiplier fitted on training weeks) covers 0.882–0.897 in every cell listed above. The half-width is 47–67% of the group's energy for 10 random meters.

## ML test
Gradient boosting against anchored on the same features. Mean-absolute-error difference (ML − anchored) on validation, in kWh per interval:

| d | 10 random | zones |
|---|-----------|-------|
| 0 | −0.030 | −0.015 |
| 0.25 | −0.007 | +0.004 |
| 0.5 | −0.002 | +0.008 |
| 1.0 | +0.001 | +0.007 |

The bootstrap 95% intervals are narrow (for example −0.0022 to −0.0013 at d = 0.5) but too narrow, because the resampling treats every (interval, group) pair as independent. ML gains only where SimBench's scaled copies help it (d = 0). Elsewhere the difference is within 1% of group energy and changes sign between group types. **ML was tested and is not needed.** The downstream test was not run because there is no upstream gain to carry forward.

## Decision
Detector uses the anchored estimator with H = 14 and conformal-style uncertainty fitted on training
weeks. See `docs/process/decisions/0002-expected-load-estimator.md`.
