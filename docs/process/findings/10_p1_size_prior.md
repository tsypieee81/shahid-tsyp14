# Finding 10 — Priority 1: a size-dependent prior breaks the missed-outage limit (development, SIMULATED)

Protocols 01 and 04. Source: `results/p1/p1_dev.json`, `results/p1/p15_dev.json`. Ledger P2D-01 to P2D-03.

## Result
- **No candidate meets the safety rule.** Neither the size prior (P1a) nor the learned combination of
  the balance evidence with group size (P1b) has a band that keeps missed outages at or below 0.05 on
  development validation: 0.1071–0.1875 (P1a) and 0.1161–0.3214 (P1b) over the seven bands. The same
  holds after splitting by feeder (P1+5: at least 0.1071).
- **Why.** On the development data, a silent group of one meter is almost always a data loss (fitted
  P(comms) 0.996). A size-aware prior pushes the genuine small outages towards "communication
  failure", where the escalation table may close them without a human. This is the risk that Phase 2
  candidate 2 named in advance.
- What it would buy: zero fault-free false outages and less abstention, at the price of the costliest
  error. Under rule v3 that price is not allowed. **Registered outcome: recommend version 1.** Neither
  P1 nor P1+5 goes to the confirmatory batch.

## Escalating gate (policy layer, development, all weeks)
On 350 whole-feeder outages: the meter-count gate that closes resumed groups loses 16 of them with no
verdict; the escalating variant loses none. Human items per transformer-day on the fault-free year:
10.23 (version 1), 0.019 (gate-close), 4.50 (gate-escalate). Outages without real-time attention: 31,
49, 48. The escalating gate keeps most of the load reduction of the gate and removes its silent loss;
it does not restore real-time attention, because small outages often end before the hour of WATCH.
Confirmatory rows: protocol 05.

## Consequence
The base-rate problem behind tiny-group false verdicts (LIMITATIONS 24) is real, but a prior learned
from simulated frequencies trades it for missed outages. A utility prior would have to come from its
own outage and data-loss records; with none available, version 1's 50/50 prior stays.
