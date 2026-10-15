# Protocol 02 — Priority 2: evidence accounting version 2 (a registered alternative method)

Registered 2026-10-14, before any version 2 code exists. Frame: protocol 00. Sources:
`docs/studies/reporting_interval/V2_CANDIDATES.md` (candidates 1–4), ledger CAD-4, CAD-10, CAD-11.

## Question
At coarser reporting intervals and with onsets inside an interval, version 1 makes false outages
(late stored readings of the silent group itself flip comms failures to OUTAGE, CAD-10) and misses
late-onset outages (CAD-11). Does a revised evidence accounting fix these without breaking the
safety limits at 15 minutes?

## Method version 2 (module `shahid/detect_v2.py`; `shahid/detect.py` untouched)
Interval-general (the reporting step is read from the data). Changes against version 1, all
switchable so that version 1 behaviour is a configuration of the same module:
1. **Own stored readings as evidence.** At decision time, if at least half of the group's readings
   for the onset interval have arrived late, the verdict is COMMS_FAILURE with reason "stored
   readings delivered" and no posterior. Under assumption A-COMMS (meters store and resend) this is
   direct evidence; without store-and-forward it does not exist.
2. **Own late readings stay out of the visible sum.** Readings of the silent group's meters that
   arrive during the window are excluded from the reporting sum, so their energy is counted once
   (in M), not on both sides.
3. **Onset interval excluded** from R and M at every interval length (it may be partial).
4. **Rules in minutes**: silence 30 min (K = ceil(30 / step)), decision window up to 60 min after
   the silence check (L_max = ceil(60 / step)), history and gap baseline in days. Nuisance
   parameters are refitted per interval on unlabelled fault-free training weeks, as in the cadence
   study.
- **Reference "v1 at any interval"**: the same module with changes 1–4 off and K = 2, L_max = 4
  readings, frozen thresholds (the cadence-study configuration). A test checks that at 15 minutes
  it equals `shahid.detect` exactly.

## Simulator additions (defaults reproduce every existing result; checked by a test)
- Reporting interval option (`cadence_min`), ported from branch `cadence-study` (`observe.coarsen`).
- Sub-interval onsets at 15 minutes: event option `offset_min` ∈ (0, 15). Partial-interval model on
  the 15-minute truth: in the onset step the affected meters' energy is scaled by offset/15 and the
  transformer energy is reduced by the same amount (ASSUMPTION: linear, losses not re-solved). The
  onset reading is not sent for an outage and is stored for a comms failure.

## Selection (development only)
Abstention band b ∈ {0.005, 0.01, 0.02, 0.03, 0.05, 0.1, 0.2} chosen by rule v3 at 15 minutes on
development validation (seeds 101–103). Development diagnostics at 30 and 60 minutes and with
sub-interval offsets use new seeds 901–902 on semiurb5 and are not used for selection. Frozen
parameters go to `results/p2/v2_params.json`, committed before protocol 05.

## Endpoints (confirmatory, protocol 05, rural2 and semiurb4, intervals 15 / 30 / 60 min)
- **S1 (primary)**: false-outage rate at 60 minutes, v2 below v1 at any interval. Supported if
  the paired bootstrap 95% interval of the difference (pooled over both grids) lies below 0.
- **S2 (primary)**: missed-outage rate for onsets inside an interval (sub-interval offsets at 15 min;
  natural offsets at 30 and 60 min), v2 below v1, same test.
- **Safety**: v2 meets the v3 limits at 15 minutes on rural2.
- Reported, no criterion: detection delay in minutes, coverage, fault-free false outages.

## Named test case and its expected result
The m093-type merge (finding 09) is replayed under version 2. **Expected: version 2 does not fix it**,
because the merged meter's late reading arrives after every decision lead. A negative result on this
case does not count against version 2; its remedy is protocol 03.

## Compute ESTIMATE
Port and implementation are work time, not compute. Development runs: 3 intervals × 2 seeds plus
offset sets on semiurb5 ≈ 2–3 h. The confirmatory part is costed in protocol 05.
