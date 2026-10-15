# Finding 16 — Joint confirmatory batch on the two untouched grids (run once, SIMULATED)

Protocol 05 with addendum A. Source: `results/p2/confirm.json` (`python -m shahid.p2_confirm evaluate`,
commit 235ab3f). Ledger P2C-01 to P2C-06. Grids `1-LV-rural2--0-sw` (primary) and `1-LV-semiurb4--0-sw`,
never used for any detector outcome before. Every candidate was frozen before the run.

## Version 1 transfers (P2C-01)
On both new grids, frozen version 1 meets the safety rule: rural2 misses 0.0093 of outages with no false
outage and abstains on 0.3295; semiurb4 misses none and abstains on 0.4735; fault-free false outages
0.0004 and 0.0006 per meter-day. These are the fourth and fifth grids on which version 1 keeps its
false-outage rate at zero.

## Priority 5, split by feeder (P2C-02, P2C-03)
- **Safe on both grids (H5b met)** and **H5a supported**: confident wrong communication verdicts on
  cross-feeder merges, 4 under version 1, 0 under P5 (all four in the whole-feeder families).
- Merges are frequent: outage groups with a powered meter 16.044 and 14.959 per transformer-year on
  rural2, 4.011 and 5.9836 on semiurb4.
- **The price confirms development:** random-meter communication failures are abstained 0.973 of the
  time under P5 (0.4054 under version 1) on rural2 and 0.9744 (0.4872) on semiurb4; human items per such
  episode rise from 0.4054 to 2.7838 and from 0.4872 to 1.6154. Outages, aligned concentrators and zone
  failures are unchanged.

## Priority 1, escalating gate (P2C-04)
P1 and P1+5 were not frozen (finding 10) and were not run. On the new grids the meter-count gate lost no
whole-feeder outage even when closing, so escalating instead of closing only adds human items (rural2:
4.1516 per transformer-day against 0.0109). The development grid's 16 silent losses did not recur here.

## Priority 2, evidence version 2 (P2C-05)
- **S1 not supported:** false outages at 60 minutes fall from 0.016 to 0.0074, but the interval of the
  difference (−0.0173 to 0.0012) includes zero.
- **S2 not supported, and in the wrong direction:** for onsets inside an interval, version 2 misses
  0.2568 of outages against 0.1174 for version 1 (difference 0.1394, 0.108–0.1709). The mechanism seen in
  development (finding 12) recurs: at 30 and 60 minutes the minute-based silence rule is a single missing
  reading and merges delayed meters into outage groups.
- Version 2 is safe at quarter-hour readings on rural2 (missed 0.0288, false 0.0124). **Version 2 is not
  adopted.** Its two good parts (ignoring the partial onset interval, the stored-reading evidence) would
  need a variant that keeps a silence rule of at least two readings; untested.

## Priority 3, single-meter faults (P2C-06)
**H3 not supported:** on rural2 the per-meter gap regression detects gain × 0.5 only 0.3467 of the time,
gain × 0.8 0.1067, bias −0.05 0.0067; neighbour voltage at most 0.0533. Goal G1 stays partly covered.

## Overall decision
Version 1 stays the method. **Split by feeder** is the one candidate that removed a dangerous error
without breaking a safety limit; it is recommended as a **configurable option for utilities whose
concentrators follow the feeders**, with its price stated. A scattered concentrator layout pays several
human items per comms failure.
