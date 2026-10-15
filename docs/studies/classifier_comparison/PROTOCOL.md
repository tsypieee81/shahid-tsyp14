# Protocol: supervised-classifier comparison (classifier-v1)

Written 2026-10-12 and committed alone, before any model is trained or any feature table is built.

## 1. Question and classification

Using exactly the observed evidence the frozen method computes, does a supervised classifier trained
on labelled simulated events match or beat the frozen likelihood-ratio test with abstention, on
networks it was not trained on and under the same safety limits?

**Post-hoc.** The two evaluation networks (SimBench `1-LV-urban6--0-sw` and `1-LV-rural3--0-sw`)
were examined in earlier work, so this is not a confirmatory test. Everything is SIMULATED. The
registered method does not change, whatever the outcome. A classifier that wins is reported as a
candidate learned fusion for Phase 2.

## 2. Hypotheses (pre-specified)

- **H-A:** no classifier reaches higher coverage than the frozen method while meeting all three
  safety limits (section 6) on the held-out urban network.
- **H-B:** removing the energy-balance features drops every classifier to the level of the
  structure-based baselines (count, structure).
  - Operationalised: on the held-out urban network, every ablation classifier with a feasible band
    has accuracy when deciding, or false-outage plus missed-outage rate, no better than the better of
    the count and structure baselines.
  - An ablation classifier with no feasible band also supports H-B.
- **H-C:** the classifiers' safety holds on the rural network as well.
  - Operationalised: the upper 95% Wilson bounds of the false-outage rate and the missed-outage rate
    are both at most 0.05, and fault-free false outages are at most 0.001 per meter-day.

Each hypothesis is assessed separately for every model and every seed.

## 3. Data and labels

- **Examples.** One example per detected silent group, from the same simulation families as the
  stored records (`shahid/records.py: families()`), regenerated deterministically. Each family uses
  the frozen nuisance fit of its network: frozen parameters on the development network, and a refit
  on the network's own fault-free training weeks elsewhere, as in the held-out evaluation.
- **Evidence per lead.** For every group, the evidence at each decision lead L = 0..4 (window of
  K + L intervals after onset, K = 2), computed by the unchanged `detect.evidence_table`.
- **Label.** From the injector's cell-level ground truth: OUTAGE if more than half of the group's
  meters had no supply at the group's onset interval, otherwise NOT_OUTAGE (a communication failure
  or random data loss). The number of groups with an outage share between 20% and 80% is reported.
- **Use of labels.** Labels and all ground-truth columns are used only as training targets and for
  evaluation, never as features.
- **Episode-level evaluation.** The registered matching rule maps groups to labelled episodes (same
  onset, meter-set overlap at least 0.5). An episode with no matched group is "never detected".

## 4. Features (observed evidence only)

- **Full set:**
  - R, M, sd_O, sd_C;
  - the number of intervals in the window, the gap baseline and the number of meters;
  - the hour of onset as sine and cosine;
  - the visible share R/M (M floored at 0.01 kWh in the denominator);
  - the standardised residuals R/sd_O and (R − M)/sd_C.
- **Ablation set:** the full set without R, the visible share and both standardised residuals.
- **Training lead.** Each training and validation example uses the evidence at one lead drawn
  uniformly from 0..4 with a fixed seed (2026), so the model sees every window length while keeping
  one example per group.
- **Test.** Evidence at every lead, used sequentially (section 6).
- **Leak test.** `tests/test_classifier_study.py` fails if any truth, label, cause or episode column
  enters the feature table, or if any urban or rural row enters training or validation.

## 5. Splits

| Use | Data |
|---|---|
| Training | Development network semiurb5 only: event seeds 101–103 (`cp5` family) and the fault-free year (`ff_semiurb5`), training weeks (week mod 4 in {0, 1}) |
| Validation (hyperparameters, calibration, abstention band) | Same families, week mod 4 = 2 |
| Test, run once | Urban6: test weeks (week mod 4 = 3) of seeds 301–303 (`cp7_heldout_urban6`) and of its fault-free year (`ff_urban6`). Rural3: test weeks of `rural3_eps` and `rural3_ff`. Whole-feeder families `feeder_semiurb5` and `feeder_urban6`, all weeks |

The classifiers never see urban6, rural3 or the feeder families before the test.

## 6. Models, selection and decision rule

**Models.**
- Logistic regression on standardised features. Class weights balanced. Grid C ∈ {0.01, 0.1, 1, 10}.
- Histogram gradient boosting (scikit-learn). Class weights balanced. Grid max_depth ∈ {3, None} ×
  learning_rate ∈ {0.05, 0.1}, max_iter 300, early stopping on an internal 10% split.
- Multilayer perceptron (scikit-learn), on standardised features with early stopping. The minority
  class is randomly oversampled to balance (MLPClassifier has no class weights). Grid hidden layers
  ∈ {(16,), (32, 16)} × alpha ∈ {1e-4, 1e-2}.
- Each model also on the ablation set: six model variants in total.
- Hyperparameters are chosen by validation log-loss.
- The stochastic models (gradient boosting, MLP) are trained with seeds 0, 1, 2; their spread is
  reported.

**Calibration.** Probabilities are calibrated on the validation set: isotonic, or Platt if either
class has fewer than 200 validation examples.

**Decision rule.**
- A classifier decides like the frozen method: OUTAGE if the calibrated outage probability is at
  least an upper threshold, COMMUNICATION FAILURE if it is at most a lower threshold, UNCERTAIN in
  between.
- It is applied sequentially over leads 0..4, stopping at the first decided lead; the verdict at
  lead 4 is final.

**Band selection on validation, with the frozen method's rule.**
- Thresholds are searched over lower ∈ {0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5} and upper ∈
  {0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99}, with lower < upper or both 0.5.
- A setting is feasible if missed outages are at most 5%, false outages at most 5% (episode level,
  validation weeks), and fault-free false outages at most 0.001 per meter-day (fault-free year,
  validation weeks).
- Among feasible settings, choose the least abstention. If none is feasible, report "infeasible" and
  also the setting with the lowest false-outage plus missed-outage rate.

## 7. Evaluation (run once)

Each classifier is reported next to the frozen method and the four simple baselines (naive share,
step, count, structure), on identical groups and episodes. For each network:
- coverage (decided over all eligible episodes), outage recall, communication recall, false-outage
  rate, missed-outage rate and accuracy when deciding, with Wilson intervals;
- fault-free false outage verdicts per transformer-year and per meter-day;
- the Brier score and a reliability plot (test groups);
- whole-feeder outcomes;
- median decision latency in intervals;
- paired bootstrap 95% intervals of the difference to the frozen method in coverage, false-outage
  rate and missed-outage rate (1000 resamples of episodes, stratified by cause, seed 2026);
- training, validation and test log-loss and AUC side by side, to show overfitting.

**Controls.**
- A shuffled-label control: the same pipeline trained on permuted training labels must lose its
  discrimination.
- Any accuracy when deciding of 0.99 or more triggers the leak test and this control before it is
  reported.

## 8. Explanations

- Logistic-regression coefficients on standardised features.
- For gradient boosting, SHAP values if the `shap` package installs cleanly with the pinned numpy;
  otherwise permutation importance on the validation set, with the reason stated.

## 9. Time box and integrity

- Four hours of wall time, at most 2 workers.
- No change to the frozen method's code, configuration or results.
- No tuning after the test is run. A demonstrable bug fixed after the test is logged in the study
  README, and the whole test is rerun.
