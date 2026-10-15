# Protocol 03 — Priority 5: split candidate silent groups by line section before scoring

Registered 2026-10-14, before any code for it exists. Frame: protocol 00. Ranked immediately after
protocols 01 and 02.

## Motivation
Finding 09 (ledger EXP-01) is the only measured cause of the confident-wrong verdict family
(LIMITATIONS 12 and 27): a powered meter on an energised feeder went silent at the same onset, was
merged into the outage group and supplied the whole residual. Splitting candidate groups along the
network should keep such a meter out of the outage group.

## Method P5 (module `shahid/p5_split.py`; version 1 untouched)
- **Line sections**: the feeder partition derived from the context zones only (the maximal zones:
  zones not contained in another zone). On semiurb5, rural2 and semiurb4 this partition covers every
  meter (network facts checked 2026-10-14).
- Each candidate silent group of version 1 (`detect.silent_groups`) is split into its subsets per
  feeder. Each subset is scored by version 1 unchanged (evidence, thresholds, sequential leads); the
  other silent subsets at that onset enter the evidence as other missing meters, as version 1 already
  does for any meter outside the group.
- No new parameter: nothing is selected. The development check is whether P5 still meets rule v3 on
  validation; if it does not, that is reported and P5 is still carried to protocol 05 as registered.
- Stated limit: a merge inside one feeder (powered meter on the same feeder as the outage) is not
  removed at this level. Its frequency is measured, not fixed.

## The price of the fix (measured on the same events)
A comms failure that spans several feeders (random-meter comms; concentrators in the random layout)
is split into smaller groups with lower signal-to-noise. Measured on development:
- CP5 validation episodes by selector (outage, comms_zone, comms_concentrator, comms_random):
  abstention, coverage, missed and false outages, v1 against P5, paired bootstrap intervals;
- the CP6 random-concentrator cell (seeds 201–202);
- the whole-feeder families (seeds 401–402).
The same tables are repeated on the confirmatory grids in protocol 05.

## Merge frequency
On event runs (development: CP5 seeds 101–103 all weeks and the whole-feeder families; confirmatory:
protocol 05), from the simulation labels (evaluation side only): the number of version 1 groups
matched to an outage episode that contain at least one meter outside the episode (a powered meter),
per transformer-year, with a Poisson 95% interval; split into cross-feeder and same-feeder merges;
and how many of those groups received a wrong verdict, and with what posterior.

## Endpoints (confirmatory, protocol 05)
- **H5a (primary)**: wrong COMMS verdicts with posterior ≥ 0.95 on outage episodes whose v1 group
  contained a cross-feeder powered meter: fewer under P5. Reported as counts with exact intervals;
  supported if P5's count is lower and P5 meets the safety limits. With few such events the
  result may be inconclusive; that is reported as such.
- **H5b (safety)**: P5 meets the v3 limits on rural2 test-week episodes.
- **Price (no direction claimed)**: abstention difference P5 − v1 on cross-feeder comms episodes,
  with interval.

## Compute ESTIMATE
Split evidence tables reuse the development cache of protocol 01; extra evidence for split subsets
≈ 1 h. Merge counting is post-processing (minutes).

## Addendum A (2026-10-14, after the development run, before any confirmatory run)
**What was seen.** On development data, the registered matching rule (same onset, Jaccard ≥ 0.5 with one
group) marks most split comms episodes as MISSED: no single subset holds half of the episode's meters
(cp5 validation: 18 of 32 random-meter comms episodes; random-concentrator cell: 32 of 63 concentrator
episodes). MISSED comms episodes do not count as abstentions, so the registered abstention comparison
understates the price of splitting.

**Added measure (the registered one is still reported unchanged).** Episode outcome over all its
subsets: the P5 groups at the episode's onset that share at least one meter with the episode. Outcome
OUTAGE if any such subset is called OUTAGE; otherwise UNCERTAIN if any is UNCERTAIN; COMMS_FAILURE if all
are; MISSED only if none exists. Also reported: subsets per episode and human items per episode (subsets
not closed automatically under the version 1 escalation table). The price endpoint of protocol 05 uses
this outcome; H5a and H5b keep the registered rule and are reported under both.
