# CP5 — Balance validation, detector comparison, baselines

Sources: `results/cp5_gap.json` (`python -m shahid.cp5_gap`) and `results/cp5_compare.json`
(`python -m shahid.cp5_compare`, commit 329946f, config hash 02b13dbef9dc). Superseded runs are kept
as `results/cp5_compare_v1_unconstrained.json` and `results/cp5_compare_v2_fa_budget_only.json`.
Ledger C5-01 to C5-08.

## Setup
- Development grid semiurb5, d = 0.5, nominal meter and comms error.
- Detector parameters are fitted on the fault-free year's training weeks (week % 4 ∈ {0, 1}).
- Episodes: `configs/cp5_episodes.yaml` with seeds 101–103. About one event per day: 40% outages,
  30% comms failures on an electrical zone, 15% on a concentrator group, 15% on random meters.
  Outages and zone comms failures draw their silent sets from the same zones.
- All numbers below are **validation weeks** (week % 4 = 2): 112 outage and 152 comms episodes.
  Thresholds were chosen on the same weeks, so these figures are optimistic. CP7 is the unbiased test.

## Gap on fault-free data (training weeks)
- Gap = transformer − Σ meters, on intervals where every meter reported (only 35% of intervals,
  because each reading is lost with probability 1% across 104 meters).
- Mean 0.005 kWh, sd 0.021 kWh per interval. The gap change relative to its last-day median has a
  robust sd of 0.018 kWh and lag-1 autocorrelation 0.35. Residuals are right-skewed (0.71) and
  heavy-tailed (excess kurtosis 1.58). A linear-in-load model barely helps (sd 0.0204 vs 0.0206).
- **Consequence**: gap noise is about 15× smaller than the expected-load error of a 10-meter group
  (CP4). The outage hypothesis (R ≈ 0) is sharp; the comms hypothesis (R ≈ M) is broad. Residuals
  support a Student-t model (df 4) and AR(1) variance inflation for window sums.

## Detectors and baselines

Evidence for a silent group over the window: R = transformer − known readings − recent gap −
expected energy of other missing meters, and M = anchored expected energy of the group.

| Method | Rule |
|--------|------|
| share | R / M against a threshold |
| ztest | standardised residual under both hypotheses; abstain if both or neither fit |
| lr | Student-t log-likelihood ratio against a threshold |
| bayes | posterior P(comms) from the same likelihood ratio, prior 0.5, abstention band |
| baseline count | silent set fills ≥ 90% of its smallest electrical zone → outage |
| baseline structure | matches a concentrator → comms; fills a zone → outage; both → abstain |
| baseline step | transformer drop at onset ≥ half the expected group energy → outage |
| baseline naive | the CP2 detector: median expected load, share threshold 0.5 |

Isolation Forest was not added. The question is a two-hypothesis test with a physical model, and
an unsupervised anomaly score has no way to say which hypothesis the data supports.

## How thresholds were chosen (three attempts, all kept)
1. **v1, maximise balanced correct-cause rate on labelled episodes.** The likelihood ratio reached
   0.908, but on the fault-free year it called 419 of 1 051 random-loss silences outages
   (0.044 per meter-day). Labelled episodes alone hid the false alarms from ordinary data loss.
2. **v2, add a fault-free budget of ≤ 0.001 false outages per meter-day.** The likelihood ratio
   then met the budget only by calling 37% of outages comms failures. Under the escalation table a
   confident comms verdict is handled automatically, so a missed outage leaves customers without
   power unattended. That is the costliest error.
3. **v3 (final), safety-constrained.** Choose the setting with the lowest abstention subject to:
   fault-free false outages ≤ 0.001 per meter-day, missed-outage rate ≤ 5%, false-outage rate ≤ 5%
   (DESIGN CHOICE, `docs/process/decisions/0003-detector-and-thresholds.md`).

## Results (v3, validation)

| Method | Meets constraints | Accuracy when decided | Abstention | Outage recall | Comms recall | False outage | Missed outage | Fault-free false outages per meter-day |
|--------|------|------|------|------|------|------|------|------|
| **bayes** (band 0.03) | yes | 0.988 | 0.337 | 0.545 | 0.717 | 0.000 | 0.036 | 0.0006 |
| ztest (z 2.9, min 2 kWh) | yes | 0.987 | 0.398 | 0.536 | 0.618 | 0.000 | 0.036 | 0.0010 |
| lr (closest) | no | 0.984 | 0.288 | 0.714 | 0.671 | 0.013 | 0.027 | 0.0051 |
| share (closest) | no | 0.962 | 0.288 | 0.714 | 0.645 | 0.040 | 0.027 | 0.0052 |
| naive baseline | no | 0.887 | 0.148 | 0.777 | 0.724 | 0.105 | 0.098 | 0.0122 |
| step baseline | no | 0.648 | 0 | 0.652 | 0.632 | 0.362 | 0.348 | 0.0538 |
| count baseline | no | 0.498 | 0 | 0.795 | 0.270 | 0.724 | 0.205 | 0.0133 |
| structure baseline | no | 0.559 | 0.189 | 0.688 | 0.270 | 0.474 | 0.205 | 0.0128 |

Bootstrap 95% intervals (episodes resampled within class) for bayes: outage recall 0.446–0.634,
comms recall 0.645–0.783, abstention 0.284–0.394, false-outage rate 0.000–0.000.

- **Count and structure are near chance by design.** Outages and zone-shaped comms failures share
  the same silent sets, so structure carries no information. The structure baseline is right only
  for concentrator failures in random mode.
- **Bayes trades coverage for safety.** It decides two-thirds of episodes and is almost never
  wrong when it does. Its abstentions follow the physics.

Bayes correct-cause and abstention rates by difficulty (validation):

| Expected silent energy over the window (kWh) | ≤ 0.5 | 0.5–1 | 1–2 | 2–5 | 5–10 | > 10 |
|------|------|------|------|------|------|------|
| correct-cause rate | 0.27 | 0.51 | 0.59 | 0.75 | 0.94 | 1.00 |
| abstention | 0.71 | 0.46 | 0.39 | 0.25 | 0.05 | 0.00 |
| episodes | 45 | 37 | 49 | 77 | 38 | 15 |

By group size, groups of more than 5 meters are decided correctly 78–85% of the time, against
15–46% for groups of 1–5 meters. Midday (10:00–15:00) is the hardest period at 0.49, where PV
cancels consumption.

## Sanity controls
- **Transformer series shifted by 7 days** (seed 101): the bayes balanced correct-cause rate drops
  to 0.27 with 47% abstention, and lr to 0.38. The decisions depend on the transformer signal,
  not on artefacts of the silent sets.
- **Fault-free year**: bayes issues 0.0006 false outage verdicts per meter-day (budget 0.001).
- No headline metric is ≥ 0.99. "Accuracy when decided" of 0.988 is close, so CP7 re-checks it on
  held-out data. The shifted-transformer control, the leak test and the structure-only baselines
  all argue against a leak.
