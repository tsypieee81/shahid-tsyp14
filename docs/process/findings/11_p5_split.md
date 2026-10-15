# Finding 11 — Priority 5: splitting by feeder removes cross-feeder merges, at a large price for scattered comms failures (development, SIMULATED)

Protocol 03 with addendum A. Source: `results/p5/p5_dev.json`. Ledger P2D-04 and P2D-05.

## Result
- **Safety.** P5 meets rule v3 on development validation; missed outages fall from 0.0357 to 0.0179 at
  the same abstention (0.3371) under the registered matching rule.
- **Merges are frequent.** Version 1 groups that are matched to an outage and contain a powered meter:
  12.3 per transformer-year in the CP5 runs, 10.47 in the random-concentrator cell, 19.45 in the
  whole-feeder families. Wrong communication verdicts with posterior at least 0.95 on cross-feeder
  merges: 1, 2 and 1 under version 1, none under P5. The finding-09 mechanism is not a one-off.
- **The price is large where the protocol predicted.** Measured over all subsets of an episode
  (addendum A, because the registered rule counts split comms episodes as MISSED and hides the cost):
  random-meter comms failures are abstained 0.969 of the time under P5 against 0.344 under version 1
  (difference 0.625, 0.469–0.781), and random-layout concentrator failures 1.0 against 0.333; human
  items per episode rise from 0.34 to 2.44 and from 0.33 to 2.76. Outages, aligned concentrators and
  zone failures are unchanged.

## Interpretation
Splitting moves the cost from a rare dangerous error (a confident wrong comms verdict on an outage) to a
frequent safe one (more human items) — but only where a comms failure spans feeders. In an aligned
layout (one concentrator per feeder) the price is nil; in a scattered layout it is several human items
per failure. Which is acceptable depends on the utility's concentrator layout, which we do not know.
Confirmatory result: protocol 05.
