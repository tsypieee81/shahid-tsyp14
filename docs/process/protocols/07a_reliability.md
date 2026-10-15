# Protocol 07a — Priority 7 (compute part): reliability of mid-range probabilities on held-out data

Registered 2026-10-14, before the analysis is run. Frame: protocol 00. Ledger C7-05 already reports
the extremes (P(comms) < 0.1 and > 0.9) on held-out episodes; the middle range was never examined.

## Data (existing records, no new simulation; version 1 frozen)
- `results/records/cp7_heldout_urban6__groups.parquet` and `results/records/rural3_eps__groups.parquet`,
  method bayes, test weeks (week mod 4 = 3): every detected silent group, including random-loss
  groups, with its posterior P(comms) at the deciding lead (lead 4 for abstained groups) and its
  simulated true cause (`truth`, evaluation side).
- Groups whose truth is neither OUTAGE nor COMMS_FAILURE, or whose posterior is undefined, are
  excluded and counted.

## Analysis (`python -m shahid.p7_reliability`)
- Ten equal-width bins of P(comms). Per bin: count, mean predicted, observed comms frequency, Wilson
  95% interval. Expected calibration error (count-weighted).
- **Mid range** = bins with predicted P(comms) in [0.1, 0.9): mostly abstained groups.
- Each grid separately and pooled. Figure `results/figs/p7_reliability.png`.
- The same table for P1 and P1+5 posteriors on the confirmatory grids is produced in protocol 05.

## Endpoint
- **H7 (descriptive, registered)**: in the mid range, the mean predicted P(comms) lies inside the
  Wilson interval of the observed frequency in at least 6 of 8 bins that hold ≥ 10 groups (pooled).
  If fewer bins hold ≥ 10 groups, the result is reported as underpowered, not as support.
- Interpretation rule: mid-range probabilities are only shown to operators on abstained items, so
  miscalibration there affects trust, not automatic decisions.

## Compute ESTIMATE
Minutes (records only).
