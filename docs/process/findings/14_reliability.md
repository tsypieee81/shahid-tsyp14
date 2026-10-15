# Finding 14 — Mid-range probabilities are not frequencies over all silent groups (held-out records, SIMULATED)

Protocol 07a. Source: `results/p7/reliability.json`, figure `results/figs/p7_reliability.png`. Ledger P2D-09.

## Result
- Over 6210 held-out silent groups (urban6 and rural3 test weeks, version 1 frozen), the mid-range bins
  predict P(comms) between 0.155 and 0.845, while 0.92–1.0 of those groups are in fact communication
  failures. Expected calibration error 0.494. **H7 is not supported.**
- On the 440 labelled episodes alone (descriptive, added after the registered result), the calibration
  error is 0.043: there, version 1's probabilities behave much more like frequencies.

## Why
The posterior uses a 50/50 prior. Most silent groups are random data loss, so the real base rate of a
communication cause is far above one half. The likelihood ratio orders groups well; the number on
screen is not the chance that the cause is a communication failure.

## Consequence for the console
On abstained items the operator sees a mid-range P(comms). It must be labelled as evidence strength
under an even prior, not as a probability of the cause; the open-item confidence card already says
"current evidence strength, not validated accuracy". A size- or rate-aware prior would fix the
calibration, but finding 10 shows that the simulated prior breaks the missed-outage limit.
