# Protocol 05 — Joint confirmatory batch on the two untouched grids (run once)

Registered 2026-10-14. Frame: protocol 00. Runs only after every candidate below is frozen and its
parameter file is committed; the freezing commit hash is written into the run's result file.

## Grids and data (never used for any detector outcome before)
- `1-LV-rural2--0-sw` (primary) and `1-LV-semiurb4--0-sw` (secondary).
- Fitting: each grid's own fault-free year (observation seed 1), training weeks only, as in
  `docs/eval_protocol.md`. Thresholds are never refitted on these grids.
- Event runs (CP5 mix, `configs/cp5_episodes.yaml`): seeds 801–803, test weeks (week mod 4 = 3).
- Fault-free exposure: the fitting year's test weeks plus observation seeds 821–822 (no new power
  flow).
- Whole-feeder families (addendum A design): seeds 811–812, all weeks (gate and attention tables).
- 10% packet loss, fault-free: seed 831 (operator load).
- Reporting-interval runs for protocol 02: seeds 841–842 at 15, 30 and 60 minutes; sub-interval
  offsets at 15 minutes: seed 843 (offsets drawn uniformly from 5 and 10 minutes).
- Single-meter fault injections for protocol 06: seed 851 on the fault-free year.

## Candidates (all frozen before the run)
Version 1 (reference); P1 (protocol 01); P5 (03); P1+5 (04); policy rows v1+gate-close,
v1+gate-escalate, P1+gate-escalate (01); version 2 and "v1 at any interval" (02); the single-meter
detectors of protocol 06.

## Procedure
One command, `python -m shahid.p2_confirm`, simulates, scores every candidate, and writes
`results/p2/confirm.json` plus per-group records. It is run once. Every endpoint is the one
registered in protocols 01–04 and 06; no new endpoint is added after the run. Labels are read only
on the evaluation side.

## Reporting
For each candidate: the CP7 metric set with intervals, fault-free false outages per meter-day and per
transformer-year, human items per transformer-day, merge frequency (protocol 03), and each registered
hypothesis marked supported / not supported / harmful. Results are labelled "confirmatory, run once".

## Compute ESTIMATE
About 9 simulated years with power flow per grid (CP7 needed about 10 min for one new grid's
fault-free year and three event seeds, FC-01), plus evidence for every candidate and three intervals:
≈ 3–4 h with two workers. Below the 10 h limit; no reduction needed.

## Addendum A (2026-10-14, after development, before any confirmatory row exists)
- **Candidates actually frozen.** P1 and P1+5 met no feasible setting on development (protocols 01 and
  04, registered outcome "recommend version 1"); they are **not** run here. Version 1, P5 (protocol 03),
  version 2 at band 0.1 with "v1 at any interval" (protocol 02), the policy rows v1, v1+gate-close and
  v1+gate-escalate (protocol 01), and D1/D2 (protocol 06) are run.
- **Weeks.** CP5-mix event runs 801–803: test weeks only (as registered). Fault-free exposure: test
  weeks of the fitting year (seed 1) and all weeks of observation seeds 821–822 (no fitting data in
  them). Whole-feeder families 811–812 and the 10% loss year 831: all weeks. Reporting-interval runs
  841–843: all weeks (fitting uses only the seed-1 fault-free year). P3: protocol 06's own scheme on
  rural2 seed 851.
- **P5 price** uses the addendum-A outcome of protocol 03 (episode over all its subsets); H5a and H5b
  are reported under the registered matching rule.
- **Line sections** on the confirmatory grids are checked to equal the network feeders before scoring;
  if they differ, the run stops.
