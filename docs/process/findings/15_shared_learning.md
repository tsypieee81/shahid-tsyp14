# Finding 15 — Shared learning: supported by its criterion, negligible in practice (proof of concept, SIMULATED)

Protocol 08. Source: `results/p8/shared.json`. Ledger P2D-10. Grids urban6 and rural3 were examined
before; this is not a confirmatory test.

## Result
- With shared shape parameters from the development site, a new site's coverage of the nominal central
  interval moves slightly closer to the nominal value for every small amount of local data on both
  grids (urban6 with one day: 0.96 shared against 0.978 local). **H8 is supported by its registered
  criterion.**
- **But no condition is usable**, not even the full-year fit of the site itself (0.964 urban6, 0.952
  rural3): the intervals are too wide on both grids under the registered definition.
- Shared parameters also give more fault-free outage verdicts (urban6 with one day: 9 against 4).
- One day of the site's own data already comes close to the full-year fit.

## Interpretation
Exchanging a handful of dimensionless parameters is cheap and leaks no readings, but in this simulation
it buys almost nothing: local calibration is fast. The Section V-D claim that sharing speeds up a new
site is not contradicted, but its benefit here is too small to matter. The over-wide intervals at every
site are themselves a finding: the noise model is conservative at the deciding lead.
