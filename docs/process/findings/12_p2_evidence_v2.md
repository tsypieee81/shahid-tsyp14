# Finding 12 — Priority 2: evidence accounting version 2 (development, SIMULATED)

Protocol 02. Sources: `results/p2/v2_select.json`, `results/p2/v2_dev.json`. Ledger P2D-06 and P2D-07.

## Selection (quarter-hour readings, development validation)
Version 2 is frozen at band 0.1: missed outages 0.0446, false outages 0.0066, fault-free 0.00042 per
meter-day, abstention 0.2652 against 0.3371 for version 1. The margin is one episode: bands 0.01, 0.02
and 0.05 miss 0.0536.

## Development diagnostics (not used for selection)
- **Onsets inside an interval, quarter-hour readings:** version 2 misses 0.0456 of outages against
  0.0875 for version 1, with outage recall 0.673 against 0.365. Leaving the partial onset interval out
  works as intended: version 2's decisions do not depend on the offset.
- **Hourly and half-hourly readings: version 2 fails.** It misses 0.5133 (60 min) and 0.4981 (30 min) of
  outages, against 0.2433 and 0.0494 for version 1, and its fault-free false outages reach 0.00194 and
  0.00355 per meter-day, above the 0.001 limit. **Mechanism:** the registered rule "silence = 30
  minutes" becomes a single missing reading at these intervals, so every randomly delayed reading
  starts a silent group (16594 and 33205 groups against 2816 and 4829). Small outages are merged with
  delayed meters, no longer match their episode, and count as missed.
- False outages at 60 minutes fall from 0.0144 to 0.0048, the direction the protocol hoped for, but
  not at an acceptable price.
- **Merge case of finding 09:** still a communication verdict under version 2 (posterior 0.998), as the
  protocol expected; its remedy is the split (finding 11).

## Status
Version 2 goes to the confirmatory batch unchanged, as registered: the diagnostics were declared not to
be used for selection. They predict that S2 fails at 30 and 60 minutes. A variant that keeps at least
two readings of silence at coarse intervals is a candidate for later work, not tested here.
