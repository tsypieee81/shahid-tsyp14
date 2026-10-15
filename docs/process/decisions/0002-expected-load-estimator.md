# 0002 — Expected-load estimator

**Context.** The balance test needs the energy the silent group would have drawn. CP4 measured
five simple estimators and gradient boosting (`docs/process/findings/04_expected_load.md`).

**Options.** median, mean, ratio, transfer, anchored, gradient boosting.

**Evidence.** Anchored has the lowest validation error in every diversity × group cell. Gradient
boosting differs from anchored by under 1% of group energy at d ≥ 0.25, with an inconsistent
sign. Independent-Gaussian intervals undercover. Scaled intervals calibrated on training weeks
reach about 0.89 coverage at a nominal 0.90.

**Choice.** Anchored (same-slot 14-day mean + ρ·pre-onset deviation), with a sigma multiplier per
lead fitted on fault-free training weeks. Simplest method within the uncertainty of the best.

**Consequence.** Expected-load error (about 20% of group energy) is the dominant uncertainty in
the detector. For a 10-meter group it is more than 10× the gap noise (CP5: gap sd about 0.018 kWh per interval). Groups whose expected energy is near zero (PV
cancelling consumption) cannot be resolved by the energy balance, and the detector must abstain.
