# Protocol 08 — Priority 8: shared learning between simulated nodes (proof of concept)

Registered 2026-10-14, before any code for it exists. Frame: protocol 00. Tests the hypothesis of
proposal Section V-D for the first time.

## Question
If a new site receives only another site's fitted noise parameters, does it reach usable calibration
with less of its own history than if it fits alone?

## Nodes and what is exchanged
- **Node A** (established): semiurb5, fitted on its whole fault-free year (training weeks), as frozen.
- **Node B** (new site): urban6 and, separately, rural3 (both previously examined: this is a proof of
  concept, not a confirmatory test).
- **Shared** (dimensionless shape parameters, no readings): `rho_by_lead`, `sigma_mult_by_lead`,
  `rho1_by_lead`, `sigma1_mult_by_lead`, `gap_acf1`.
- **Local** (scale, site-specific, from B's own data): `gap_sd`, `gap_const`.
- Nothing else leaves a node; in particular no meter reading, no customer series.

## Conditions
Every site needs 14 days of history before its expected-load estimator works at all. d counts the
days of fault-free data available for fitting after that warm-up, d ∈ {1, 2, 4, 7, 28}.
- **Local(d)**: `detect.fit` on B's first d days after the warm-up (training weeks).
- **Shared(d)**: A's shape parameters + B's scale parameters estimated on the same d days.
- **Oracle**: B fitted on all its training weeks (the Phase 1 procedure).
Thresholds stay frozen (band 0.03, prior 0.5).

## Measures (B's fault-free year, validation weeks; evaluation side)
- Coverage of the nominal 90% interval of the standardised residual z = (R − M)/sd_C over silent
  groups at the deciding lead (as CP12 Task 3).
- Fault-free false outage verdicts per meter-day (Wilson interval).
- **Usable calibration** (DESIGN CHOICE, fixed here): coverage within [0.85, 0.95] and fault-free
  false outages ≤ 0.001 per meter-day.

## Endpoint
- **H8**: for d ≤ 4, Shared(d) reaches usable calibration on both B grids where Local(d) does not, or
  its |coverage − 0.90| is smaller on both. Reported per d and per grid; days-to-usable for each
  condition. If Local(1) is already usable, H8 is not supported (sharing adds nothing here) and that is
  the result.

## Compute ESTIMATE
5 values of d × 2 conditions × 2 grids of fits (seconds each) and evidence over validation weeks
(minutes each): ≈ 1.5 h.
