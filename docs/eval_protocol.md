# Evaluation protocol (CP7, frozen before the held-out run)

This file is committed before `python -m shahid.cp7_heldout` is run for the first time. The commit
hash of that run is recorded in `docs/process/checkpoints/CP7.md`. If the method changes after the held-out
results have been seen, the held-out grid is no longer called held-out.

## Frozen method
- Detector `shahid.detect`, primary method **bayes**: Student-t likelihood ratio (df 4), prior
  P(comms) = 0.5, abstention band 0.03, no minimum-energy cut, silence after K = 2 missing
  intervals, sequential decision at L = 0..4 extra intervals.
- Thresholds for every method are frozen in `results/detector_params.json` (`thresholds`), as
  chosen in CP5 on validation weeks with rule v3 (`docs/process/decisions/0003-detector-and-thresholds.md`).
- The fitting procedure (`detect.fit`) is part of the method. On each evaluation grid it runs on
  that grid's own fault-free year, training weeks only. Thresholds are never refitted.
- Baselines: naive, step, count, structure (`shahid/baselines.py`), unchanged.

## Splits
- **Held-out grid**: `1-LV-urban6--0-sw`. CP1 only measured its network facts and ran two weeks of power flow. No checkpoint generated episodes on it or ran a detector on it.
- **Held-out period**: test weeks, week index % 4 = 3 (week = row // 672 from 2016-01-01). No
  earlier checkpoint scored them.
- **Held-out seeds**: 301, 302, 303 for events and observation noise. Earlier checkpoints used 1, 101–103 and 201–202. The world seed for customer diversity stays 0, but on urban6 it produces a different draw because the grid differs.
- A second report uses the same test weeks and seeds on the development grid semiurb5.
- The episode mix is that of `configs/cp5_episodes.yaml`: 40% outage, 30% zone comms, 15%
  concentrator comms, 15% random-meter comms, durations 4–16 intervals.

## Episode matching
- One labelled episode per injected OUTAGE or COMMS_FAILURE event (labels are emitted by the
  injector).
- A detected silent group matches a labelled episode when its onset equals the event start and
  the Jaccard similarity of the meter sets is ≥ 0.5. An unmatched labelled episode is MISSED.
- Detected groups that match no labelled episode (random loss, delays) are counted separately.
  An OUTAGE verdict on one of them is a false alarm.

## Metrics (test weeks only)
- Outage recall: outage episodes called OUTAGE / outage episodes.
- Comms recall: comms episodes called COMMS_FAILURE / comms episodes.
- Precision per class: correct calls of a class / all calls of that class.
- False-outage rate: comms episodes called OUTAGE / comms episodes.
- Missed-outage rate: outage episodes called COMMS_FAILURE or MISSED / outage episodes.
- Abstention rate: UNCERTAIN verdicts / all labelled episodes.
- Accuracy when decided: correct / episodes with an OUTAGE or COMMS_FAILURE verdict.
- Detection latency: intervals from onset to the decision (K + L), median.
- False alarms per meter-day: OUTAGE verdicts on the grid's fault-free year (test weeks) /
  meter-days, with a Wilson 95% interval.
- Expected-load MAE and 90% interval coverage: for matched comms episodes, the anchored expected
  energy M against the true energy of the silent meters over the decision window.
- Brier score and reliability (10 bins) of P(comms) for bayes, over episodes where it is defined.
- Confidence intervals: bootstrap over episodes, resampled within each class, 1 000 replicates,
  95%. Every metric is reported next to the baselines.

## Addendum A (CP10, committed 2026-10-07 before any run it describes)

All runs below use the **frozen** version 1 method (`results/detector_params.json`, unchanged code
paths). Nothing is re-tuned. Every result they produce is labelled **"post-hoc descriptive analysis,
added after CP7"**.

1. **Per-episode records** (`python -m shahid.records`) regenerate CP5 (seeds 101–103), every CP6
   cell (201–202), CP7 (301–303, both grids) and the two fault-free years (seed 1) with the
   original seeds. Their aggregates must equal the published result files exactly, or the analysis
   stops.
2. **New seeds, never used before** (event streams = seed + 1000 where the generator is used):
   - whole-feeder families: explicit outage and comms-failure events on feeder-head lines and feeder
     zones only, about one event per day, durations 4–16 intervals; semiurb5 seeds 401–402, urban6
     seeds 411–412;
   - 10% packet loss, fault-free year: semiurb5 seed 421, urban6 seed 422;
   - 10% packet loss with events (CP5 episode mix): semiurb5 seeds 431–432, urban6 seeds 433–434;
   - fault-free diagnostic years for Task 8: transformer gain error sd 2% (seed 441) and
     load-shaped unmetered 5 kW (seed 442), semiurb5;
   - world seeds for the nominal CP6 cell: world seed 1, 2, 3 with episode seeds 201–202.
3. Scoring uses all weeks for operator-load and size-class descriptions. Metrics comparable to CP7
   use test weeks only. Every table states which weeks it uses.
4. The Isolation Forest baseline (Task 6) is fitted on fault-free training weeks, and its
   score-to-verdict mapping is chosen on CP5 validation weeks only. It is then applied once to the
   CP7 episodes and labelled as added after CP7.

## Addendum B (CP11, committed 2026-10-07 before any version 1.1 number exists)

**Version 1.1** is a post-processing and escalation layer on the unchanged version 1 outputs. It
never changes evidence or likelihoods. Every version 1.1 number on records that already exist is
labelled **"post-hoc variant, not pre-registered"**.

**Policy.** For each silent group, at version 1's decision time τd, compute a gate variable g:
- SNR = |M| / sqrt(sd_C² − sd_O²);
- |M|, the expected silent energy over the window, in kWh;
- n, the meter count.

If g is below the threshold θ, the group gets no verdict and no human item. It enters WATCH:
- **resolved as comms**, with no human, if at least half of its meters have delivered their reading
  for the onset interval by τd + T (late data recovered);
- **escalated to a human** at τd + T if at least half of its meters are still silent then;
- otherwise (meters reporting again but the onset readings never recovered) **closed as an
  unexplained short gap**, with no human item. This is the gate's cost.

Groups at or above θ keep the version 1 verdict:
- OUTAGE → human approval;
- UNCERTAIN → human;
- COMMS_FAILURE → provisional (revised R3): confirmed if the onset readings are recovered by
  τd + T, otherwise escalated to a human at τd + T.

**Candidate grid.**
- SNR θ ∈ {1, 2, 3, 4, 5, 6};
- |M| θ ∈ {0.25, 0.5, 1, 2, 4} kWh;
- n θ ∈ {2, 3, 4, 6} (gate if n < θ);
- T ∈ {1, 2, 4, 6, 8} hours.

**Data used for the choice.**
- Fault-free development year (semiurb5, seed 1), training weeks 0–1: human items per
  transformer-day and false outage verdicts per transformer-year.
- CP5 validation episodes (seeds 101–103, week 2): outages without real-time human attention, by
  size class.

**Rule (DESIGN CHOICE).** Among settings with (a) at most 4 false outage verdicts per
transformer-year on the fault-free training weeks and (b) at most 2% of validation branch and feeder
outages without real-time human attention, choose the fewest human items per transformer-day.
Break ties by the smaller T. If no setting meets (a) and (b), report that and recommend version 1
alone.

**Evaluation after the choice (run once).**
- Existing records: CP7 held-out and dev-test, whole-feeder families, 10% loss families, and the
  adverse CP6 cells (gain sd 2%, load-shaped unmetered 10 kW, simultaneous events), to measure the
  revised R3.
- **New fault-free observation seeds** on the cached worlds, with no new power flow: semiurb5
  451–454, urban6 455–458. They share customers with the existing worlds.
- **Optional untouched grid**: `1-LV-rural3--0-sw` (118 loads, 9 feeders; only CP1 network facts
  were ever computed for it). One fault-free year (seed 1) is used for fitting, and episode seeds
  501–502 use the CP5 mix. Test weeks only, frozen version 1 thresholds and the chosen version 1.1
  setting, run once.

## Addendum C (CP11, committed 2026-10-07 after the development sweep, BEFORE any held-out version 1.1 number)

**Declared deviation.** Under addendum B's rule, no setting is feasible (`results/cp11_select.json`).
The reason is definitional: constraint (b), at most 2% of branch and feeder outages without real-time
human attention, is violated by version 1 itself (11.9% on validation). Many simulated outages last
4 intervals and end before any decision is possible. Addendum B's own outcome stands as the
registered result: **recommend version 1 alone**.

As a declared deviation, decided on development data only, version 1.1 is also evaluated under an
incremental reading of (b):

- (b′) branch and feeder outages without real-time attention may exceed version 1's rate by at most
  2 percentage points;
- (a) is unchanged.

Selection under (a) + (b′) uses the same sweep and the same tie-break. Every held-out version 1.1
number carries the label "post-hoc variant, not pre-registered; selected under addendum C
(deviation)". The recommendation in CP11 must state both outcomes.

## Addendum D (CP12, committed 2026-10-10 BEFORE any CP12 number is computed)

**One episode-matching rule for every table.**
- A labelled episode is matched to the silent group that starts at the episode's onset and has
  set overlap (Jaccard index of meter sets) of at least 0.5; ties go to the larger overlap. This is
  the registered evaluation rule (`shahid/evaluate.py: match_episodes`), and it is stored per group
  as `matched_episode` in `results/records/*__groups.parquet`.
- Attention accounting, policy outcome tables and operator-load attribution use the same match.
- The CP11 rule (any group with the same onset; with several groups at that onset, the last one)
  is retired. It can attribute an unrelated group's outcome to an episode.

**Policy components, reported separately (all post-hoc variants, not pre-registered).**
- Version 1: version 1 escalation table. R3 closes COMMS verdicts with p ≥ 0.95 and at most 40
  meters automatically; R4 sends other COMMS verdicts to a human.
- Meter-count gate: groups of fewer than 3 meters go to WATCH for 1 hour (the addendum C setting,
  not re-chosen). If the onset reading arrives within the hour, close as communication. If the
  group is still silent at the timeout, escalate as uncertain. If meters resume without the onset
  reading, close with no verdict.
- Provisional communication re-check, timeout T ∈ {1, 2, 4, 8} h, replacing R3/R4. A COMMS verdict
  is confirmed if the onset reading arrives within T. Otherwise it is escalated at T.
- Gate + re-check: both; the WATCH timeout stays 1 hour, and the re-check uses T.

**Human item types, never merged:**
1. uncertain: detector UNCERTAIN, or a WATCH group still silent at its timeout;
2. outage verdict awaiting approval;
3. communication verdict unconfirmed: R4 under version 1, or unconfirmed at the timeout under
   the re-check.

**Real-time attention:** the outage reaches a human before the outage ends.

**Break-even (Task 4)**, computed from the whole-feeder outcome tables:
- wrong automatic verdict: an outage closed as communication, or a communication failure called
  outage;
- human review: any human item other than an outage verdict.

**Small-group uncertainty (Task 3).** Fault-free validation weeks (week 2) of the development
grid, original and extra observation seeds; the held-out grid is reported alongside.
- Standardised residual z = (R − M) / sd_C at the decision time.
- Nominal 90% interval: |z| < t₀.₉₅ with 4 degrees of freedom, as in the detector's model.
- Size bins: 1, 2, 3–5, 6–20 and more than 20 meters.
- Single-meter near-zero test (thresholds are a DESIGN CHOICE fixed here):
  - near-zero actual: at most 0.005 kWh per interval;
  - clearly positive expectation: same-slot 14-day mean of at least 0.05 kWh.
