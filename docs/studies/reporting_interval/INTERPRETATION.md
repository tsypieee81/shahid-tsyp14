# Reporting-interval sensitivity (cadence-v1): interpretation

This is a post-hoc sensitivity study on three previously examined SimBench grids. Everything is
SIMULATED; nothing here is Tunisian data or validation. Sources: `results/cadence_v1/summary.json`
(pre-specified) and `results/cadence_v1/posthoc/posthoc.json` (**not pre-specified, added after
results**; every number from it is marked †). The design is frozen version 1 with nuisance
parameters refitted per interval.

**Base:** 2,040 eligible episodes per condition (796 outages, 1,244 comms failures), identical in
every condition and method.

## Answers to the five questions

**1. Is the change monotonic?** Yes. Every primary quantity degrades monotonically from 15 to 30 to
60 min (lr_band):

| Quantity | 15 min | 30 min | 60 min |
|---|---|---|---|
| coverage | 0.629 | 0.555 | 0.421 |
| outage recall | 0.531 | 0.416 | 0.265 |
| comms recall | 0.687 | 0.613 | 0.472 |
| false outage | 0.002 | 0.012 | 0.021 |
| missed outage | 0.006 | 0.036 | 0.245 |
| accuracy when deciding | 0.996 | 0.966 | 0.930 |

The paired coverage difference between 60 and 15 min is −0.208 (−0.230 to −0.186).

One quantity moves the other way: fault-free false-outage verdicts fall from 32.2 to 9.7 to 3.1 per
transformer-year (exposure 2.89 transformer-years per condition). The likely reason, an inference,
is that coarser readings create fewer random-loss silent groups.

**2. Is the change due to discrimination, abstention or delay?** All three, in different
proportions.
- **At 30 min, mainly abstention:** paired abstention +0.069 (0.050 to 0.087), with undetected
  episodes nearly unchanged.
- **At 60 min, mainly observability:** of the −0.208 coverage change,† −0.128 comes from
  short events that no longer suppress two readings (structurally unobservable), and −0.120 from
  newly abstained episodes. This is offset by +0.041 of episodes abstained at 15 min but decided
  at 60. Observable-but-undetected events contribute −0.0015.
- **Discrimination also worsens:** the share of wrong verdicts rises by 0.016 (30 min) and 0.027
  (60 min).†
- **Delay:** median 30 → 60 → 105 min; 90th percentile 45 → 105 → 210 min.
- **During the event:**† verdicts arrive while the event is still ongoing for 0.529 → 0.376 →
  0.191 of outages and 0.682 → 0.580 → 0.423 of comms failures. Outages reaching any human item
  before they end: 0.884 → 0.543 → 0.153.

**3. Which events become hard?** Duration matters, not size.
- At 60 min, events lasting 1–2 h are 0.52 undetected. Events over 2 h are 0.00 undetected.
- Single connections are hard at every interval: coverage 0.07, 0.07, 0.03.
- Branch and feeder outages lose recall in step with the overall decline.

**4. Does the advantage over the baselines persist?** For safety, yes. lr_band has fewer false
outages than naive at every interval: paired difference −0.102, −0.195, −0.286, all excluding 0
(H4). It also has fewer missed outages: −0.065, −0.092, −0.090. Its coverage gap to naive widens
from −0.20 to −0.35. Naive's own false-outage rate grows to 0.307 at 60 min, so the simple
baselines degrade faster.

**5. What remains valid?** Only the direction and the mechanisms, for version 1 as configured, on
these three simulated populations. See the limitations below.

## Supported findings (pre-specified)
- **H1, H2 supported.** Coverage falls monotonically, the paired 60 − 15 difference excludes 0, and
  delay rises.
- **H3 fails at 60 min:** the lower bound of accuracy when deciding is below 0.95 (0.930,
  0.911–0.945). It holds at 15 and 30 min.
- **H4 supported** at all three intervals.
- **Safety:** 15 min safe; 30 min inconclusive (missed outage 0.036, upper bound 0.052); 60 min
  unsafe (missed outage 0.245); K = 1 at 30 and 60 min unsafe.

## Findings not pre-specified (†, added after results)
- **Late backlog readings flip comms failures to outage verdicts.** After a link failure ends, the
  silent meters' stored readings can arrive inside the evidence window.
  - `detect.evidence` counts every arrived reading as "reported", including the silent group's
    own, while `M` still expects that energy to be missing. The residual then collapses
    (median R/M 0.12 at 30 min and 0.07 at 60 min, against about 1.0 otherwise).
  - Comms failures with own readings in the window are called outage in 13 of 22 cases (30 min)
    and 26 of 39 (60 min).
  - Among comms failures decided after the event ended, the false-outage rate is 0.214 (30 min) and
    0.299 (60 min), against 0.004 and 0.000 before it ended.
  - All 26 false outages at 60 min come from this mechanism.
  - The same accounting exists at 15 min but rarely triggers (1 of 21).
  - These verdicts do not rest on the energy balance as the method describes it. They rest on the
    late readings entering the "reported" sum. **Not fixed, as instructed.**
- **Partial-interval energy hides outages.** An outage starting late in a coarse interval leaves up
  to 45 min of genuine consumption in that reading's window. Such outages are called comms failure
  in 32 of 191 cases at 60 min with a 45-min start offset, against 0–2 of about 200 at other
  offsets; and in 22 of 398 at 30 min with a 15-min offset.

## Not pre-specified: additions required at approval (2026-10-11)

Source: `results/cadence_v1/posthoc/mechanisms.json`, generated by
`results/cadence_v1/posthoc/mechanisms.py` from the raw and diagnostic files. Every number below is
†.

**a. Every simulated event starts on a 15-minute boundary.**
- `shahid/episodes.py` `expand` draws `start` as an integer 15-minute row (line 40), and
  `scenario.simulate` sets `start = index[a]`.
- In the data, all 2,040 starts fall on minutes 0, 15, 30 or 45, with zero seconds.
- So the partial-interval effect cannot occur at 15 min.
- **HYPOTHESIS, untested:** the 15-min missed-outage rate (0.006) is optimistic for outages that
  begin between meter reading boundaries.

**b. Every wrong or missed lr_band outcome, by mechanism.** Each outcome is assigned to one
mechanism, in the order listed. Denominator per interval: 796 outages and 1,244 comms failures.

| Interval | Undetected, unobservable | Undetected, observable | Late own readings in window | Late-onset partial energy | Other | Total |
|---|---|---|---|---|---|---|
| 15 min | 0 | 2 | 1 | 0 | 4 | 7 |
| 30 min | 0 | 6 | 15 (13 comms called outage, 2 outages called comms) | 20 (outages called comms) | 3 | 44 |
| 60 min | 160 (outages) | 1 | 26 (comms called outage) | 34 (outages called comms) | 0 | 221 |

**c. The fall in fault-free false-outage verdicts is at least partly a design consequence.**
- Loss and delay probabilities are constant per reading. Fewer readings per day therefore produce
  fewer random-loss silent groups.
- Per transformer-year, silent groups fall from 4,553 to 2,303 to 1,075, and false-outage verdicts
  from 32.2 to 9.7 to 3.1.
- Per 1,000 silent groups, false-outage verdicts fall less: 7.1, 4.2, 2.9.
- A per-time loss model would change both columns.

**d. Simulated event durations of 1–4 h (uniform 4–16 intervals) are an unsourced ASSUMPTION.**
The "during the event" shares, the unobservable count and the late-readings mechanism all depend
on them.

## Negative results
- At 60 min, version 1 is unsafe (missed outage 0.245) and answers during the event for only 0.191
  of outages.
- The K = 1 secondary does not rescue coarse intervals. Unrelated delayed or lost readings merge
  into the event's silent group and push the overlap below 0.5 for 0.281 (30 min) and 0.292
  (60 min) of all episodes†. The missed-outage rate reaches 0.62–0.70.

## Limitations
- Thresholds were chosen at 15 min and frozen. This describes version 1 as configured, not the best
  achievable at each interval.
- **Comparisons that are not like-for-like across intervals:**
  - Thresholds in absolute kWh compared with window sums that grow with the interval: the 2.0 kWh
    minimum expected energy of the z-test, lr and share methods; naive's 0.5 kWh.
  - Rules counted in readings, so their duration grows with the interval:
    - silence K = 2 and window L_max = 4 (lr_band, z-test, lr, share);
    - baseline K = 2 and L = 2 (step, naive, count, structure);
    - delay mean 4 readings and backlog spread 4 readings (observation model);
    - 1-day gap baseline (96, 48 or 24 samples).
  - lr_band's own minimum is 0 kWh, and count/structure use a scale-free fraction (0.9).
- Loss and delay probabilities are constant per reading (a design choice). A per-time model would
  give coarse intervals fewer losses and change the results.
- Fault-free exposure is 2.89 transformer-years per condition. A zero count would still allow up to
  1.28 per transformer-year (95% upper bound). Non-zero counts are not zero risk.
- Three grids of about 100 customers, one simulated population per grid. The Wilson intervals
  assume independent episodes and are too narrow. The grids were examined before (post-hoc).
- No Tunisian figure is used. "About 53 customers per substation" is UNVERIFIED in the claims
  ledger (it is derived in `docs/tunisia/TUNISIA_EVIDENCE_REVIEW.md` N3 from STEG's 2020 report)
  and is withdrawn as a justification for the confirmatory grids.
