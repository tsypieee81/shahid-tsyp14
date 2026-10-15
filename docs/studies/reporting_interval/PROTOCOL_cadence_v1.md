# Protocol: customer reporting-interval sensitivity (cadence-v1)

Written 2026-10-11 before any cadence result was computed. Its SHA-256 is recorded in
`results/cadence_v1/protocol_sha256.txt` before the first run, and every result file carries that
hash. Branch `cadence-study` (worktree), based on `tunisia-study` 1cbf994. The frozen baseline
`phase1-frozen-cp12` is untouched.

## 1. Classification

**Post-hoc sensitivity study.** The three grids used here (SimBench `1-LV-semiurb5--0-sw`,
`1-LV-urban6--0-sw`, `1-LV-rural3--0-sw`) were examined in earlier checkpoints and in the Tunisia
study. They are not independent held-out data, and results here are not confirmatory. Fresh event
seeds limit, but do not remove, that dependence: the customer populations are the same.

A separate **confirmatory** evaluation is proposed on two grids whose detector outcomes have never
been computed: `1-LV-rural2--0-sw` (99 loads, 0.25 MVA) and `1-LV-semiurb4--0-sw` (41 loads,
0.4 MVA; used only in 4-day unit tests). It will **not** run until this study is frozen and the
user approves it.

Everything is SIMULATED on German benchmark networks. Nothing here is Tunisian data or validation.

## 2. Research question and hypotheses

How does customer-meter reporting cadence affect SHAHID's ability to distinguish physical outages
from communication failures?

- **H1 (primary):** coverage falls monotonically as the interval grows (15 > 30 > 60 min), and the
  paired difference between 60 and 15 min has a 95% interval excluding 0. Coverage is the share of
  all labelled episodes that receive an OUTAGE or COMMS_FAILURE verdict.
- **H2:** median detection delay in minutes rises with the interval.
- **H3:** among decided episodes, accuracy stays high. The lower 95% bound of accuracy when
  deciding is at least 0.95 at every cadence.
- **H4:** lr_band keeps a lower false-outage rate than the naive baseline at every cadence, on
  matched episodes.

**Safety classification per cadence** (lr_band): "safe" if the upper 95% bounds of both the
false-outage rate and the missed-outage rate are at most 0.05. "Unsafe" if either point estimate
exceeds 0.05. Otherwise "inconclusive".

## 3. Conditions

| Condition | Customer interval | Transformer interval | Silence rule |
|---|---|---|---|
| C15 (reference) | 15 min | 15 min | K = 2, L_max = 4 readings |
| C30 | 30 min | 30 min | K = 2, L_max = 4 readings |
| C60 | 60 min | 60 min | K = 2, L_max = 4 readings |
| C30-K1, C60-K1 (pre-specified secondary) | 30 / 60 min | same | K = 1, L_max = 4 readings |

C15 runs the unchanged code path. It must reproduce version 1 behaviour, and a test enforces this.

## 4. Measurement and timing model (DESIGN CHOICES approved 2026-10-11)

- **Ground truth is identical across conditions.** The world (SimBench grid, diversity d = 0.5,
  world seed 0, PV scale 1), the event list and the power-flow truth at 15 min are the same.
- **Aggregation:** a coarse reading for [t, t + Δ) is the **sum of energy (kWh)** of its
  15-minute sub-intervals; nothing is averaged. The transformer series is summed over the same
  windows. Customer and transformer windows are aligned to midnight (00:00, 00:30, ... or 00:00,
  01:00, ...).
- **Transmission:** each coarse reading is one transmission at the interval end, with the same
  per-reading probabilities as the default (1% lost, 3% delayed, Geometric mean 4 readings).
  - **Outage:** a reading is never sent if the meter has no supply at its transmission time (the
    last 15 minutes of the window). If supply returned earlier in the window, the reading is sent
    with the partial energy.
  - **Link failure:** a link failure covering the transmission time delays the reading until the
    link returns (backlog). Otherwise it is not delayed.
- **Arrival time:** for interval index i (width Δ), the reading arrives at (i + 1 + lag) × Δ.
  - The detector reads only arrival-filtered observed data. A reading counts as known at decision
    time τ only if it arrives at or before τ (in coarse units).
  - The transformer reading for window i is assumed known at (i + 1) × Δ, as in version 1
    (assumption A-LATENCY).
- **RNG:** measurement-noise and delivery draws come from the same scenario seed, but arrays of
  different shape give different draws. This is unavoidable and documented, and the physical truth
  is unaffected.

## 5. Frozen and refitted parameters

- **Frozen** (from `results/detector_params.json` and code defaults):
  - all classification thresholds: lr_band abstention band 0.03, prior 0.5, Student-t 4 df, its
    minimum expected energy; z-test z_crit; lr threshold; share threshold;
  - baseline rules: count/structure cover 0.9, step 0.5, naive 0.5 and 0.5 kWh;
  - baseline K = 2 and L = 2 readings;
  - history 14 days and gap baseline 1 day, both in days.
- **Refitted nuisance parameters** (`detect.fit`, unchanged code, on unlabelled fault-free data at
  the condition's cadence, training weeks 0–1 of the fault-free year, seed 1): gap level, gap noise
  sd, gap lag-1 autocorrelation, and the anchored-estimator persistence and sigma multipliers by
  lead. This mirrors CP7's per-grid refit. No label is used.

## 6. Data, seeds and separation

| Role | Data | Seeds | Use |
|---|---|---|---|
| Nuisance fit | fault-free year per grid (`configs/baseline.yaml`) | observation seed 1 | weeks 0–1 only |
| Development (implementation checks only) | semiurb5 events (`configs/cp5_episodes.yaml`) | 701 | debugging; reported as development, never pooled |
| Sensitivity evaluation | events on each grid | 711, 712 | all labelled episodes, all weeks |
| False-alarm exposure | fault-free year per grid | observation seed 721 | all weeks; exposure in transformer-days |

No threshold, rule or parameter is chosen on any of these data. There is no validation selection
step because nothing is selected.

## 7. Matching, eligibility, exclusions

- **Eligible episodes:** every labelled OUTAGE or COMMS_FAILURE episode of the event seeds. The
  generator starts events on day 15, which gives the 14-day history. **Nothing is excluded.** An
  episode with no matched silent group is "undetected" and stays in every denominator.
- **Matching** (all methods, all conditions): a group matches an episode if the group's onset is
  the coarse interval containing the episode's start (floor of the start to Δ) and the meter-set
  overlap (Jaccard) is at least 0.5. At 15 min this equals the registered rule (addendum D).
- **Observable stratum** (reported, not used for exclusion): an episode is observable at Δ if at
  least K consecutive coarse readings are suppressed by it. Its count per condition is reported
  next to the full denominator.

## 8. Metrics (per condition, per method, pooled over grids and per grid)

Every metric is computed over all eligible episodes unless stated otherwise:
- counts of outage and comms-failure episodes, and of undetected episodes;
- outage recall; comms recall;
- false-outage rate (comms failures called outage);
- missed-outage rate (outages called comms or undetected);
- **coverage** = decided / all eligible. This **replaces** the legacy 1 − abstention, which
  counted undetected episodes as covered;
- abstention rate (UNCERTAIN / all); unsupported rate (UNSUPPORTED / all); undetected rate;
- accuracy among decided episodes, always printed with coverage;
- detection delay in minutes from episode start to decision: median and 90th percentile, decided
  episodes only;
- fault-free false-outage verdicts per transformer-year, with the exposure in transformer-days;
- strata: size class (single, branch, feeder, scattered), duration (1–2 h vs above 2–4 h), cause,
  grid.

**Uncertainty:**
- Wilson 95% intervals per proportion. This assumes independent episodes, which understates
  uncertainty because the episodes on a grid share one simulated population.
- Paired cadence differences (C30 − C15, C60 − C15): paired bootstrap over matched episodes,
  stratified by grid and cause, 2,000 resamples, seed 2026.
- Fault-free rates: exact Poisson interval.

## 9. Integrity rules for this study

- Run order:
  1. implement;
  2. pass the leakage, aggregation and timing tests;
  3. run the development seed and check the plumbing only, comparing against no performance target;
  4. record the protocol hash;
  5. run the evaluation once;
  6. analyse.
- **No change to code, configuration or this protocol after the evaluation outcomes are
  inspected**, except to fix a demonstrable bug. A bug fix is logged as a deviation in
  `docs/cadence/DEVIATIONS.md` with its reason, and every condition is rerun.
- Zero observed false outages is reported as an upper bound, never as zero risk.
- Commit only after the acceptance criteria pass and the user approves.

**Acceptance criteria:**
1. All tests pass, including the new aggregation, alignment and future-data tests.
2. C15 verdicts on the development seed equal the unchanged version 1 code path.
3. Every eligible episode appears in every condition's denominator.
4. Every number in the summary is generated from the result files.
