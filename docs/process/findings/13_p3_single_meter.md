# Finding 13 — Priority 3: single-meter faults with voltage and per-meter gap regression (development, SIMULATED)

Protocol 06. Source: `results/p3/p3_dev.json`. Ledger P2D-08. Baseline: CP8 (at most 20% of gain errors).

## Result
- **Neighbour voltage (D1) sees nothing here:** at most 0.027 of any fault setting is detected. In this
  simulation a customer's own load barely moves its voltage relative to its feeder neighbours, and the
  simulated reading noise is far larger than that signal. The benchmark also holds the upstream voltage
  fixed, so field conditions would make voltage evidence harder, not easier.
- **Per-meter gap regression (D2) catches large errors and names the meter:** gain × 0.5 detected 0.613
  of the time, the right meter named in 0.88 of the detections. Small errors stay hidden: gain × 0.8
  0.047, bias −0.05 0.013.
- Measured false alarms were 0.01015 per meter-window for both detectors, just above the registered 1%,
  so the primary hypothesis is not met on development even where detection exceeds 0.5. Confirmatory
  result on rural2: protocol 05.

## Scope reminder
Voltage cannot help a silent meter (finding 09); D1 was not tested on the merge case.
