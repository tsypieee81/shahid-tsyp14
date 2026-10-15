# Supervised-classifier comparison

**Post-hoc, SIMULATED. The registered method does not change.** The protocol
([PROTOCOL.md](PROTOCOL.md)) was committed alone (470b560) before any feature table was built or any
model was trained. The test was run once. Results: `results/studies/classifier_comparison/summary.json`
(stamped commit 71d626b); per-group test verdicts: `test_predictions.parquet`; figures:
[coverage_vs_safety.png](../../../results/studies/classifier_comparison/coverage_vs_safety.png) and
[reliability.png](../../../results/studies/classifier_comparison/reliability.png). Ledger rows CLF-01
to CLF-12.

## Question

Using exactly the observed evidence the frozen method computes, does a supervised classifier
match or beat the likelihood-ratio test with abstention on networks it was not trained on, under
the same three safety limits (missed outages at most 5%, false outages at most 5%, fault-free false
outages at most 0.001 per meter-day)?

## Set-up in brief

- Logistic regression, gradient boosting and a small neural network (MLP), each with all features
  and with the energy-balance features removed (ablation). Gradient boosting and MLP with seeds 0, 1, 2.
- Trained on the development network only: 8 505 silent groups (202 outages) in training weeks;
  4 565 groups (108 outages) in validation weeks.
- Fewer than 200 validation outages, so Platt calibration was used for every model, as the protocol
  requires. The abstention band was chosen on validation with the frozen method's rule.
- Test once: held-out urban network and untouched rural network (test weeks), whole-feeder families.

## Results: held-out urban network, test weeks (109 outage and 155 communication episodes)

| Method | Band met limits on validation | Coverage | False-outage rate | Missed-outage rate | Accuracy when deciding | Fault-free false outages per transformer-year |
|---|---|---|---|---|---|---|
| Likelihood-ratio test with abstention (frozen) | yes | 0.723 (0.667–0.774) | 0.000 | 0.009 (0.002–0.050) | 0.995 | 40.1 |
| Logistic regression | no | 0.307 (0.254–0.365) | 0.000 | 0.046 (0.020–0.103) | 0.938 | 0 |
| Gradient boosting, seeds 0–2 | no | 0.523–0.557 | 0.000 | 0.064–0.073 | 0.945–0.949 | 0 |
| MLP, seeds 0–2 | no | 0.818–0.886 | 0.000–0.019 | 0.165–0.229 | 0.880–0.909 | 0 |
| Logistic regression, ablation | yes | 0.004 | 0.000 | 0.009 | 0.000 | 0 |
| Gradient boosting, ablation | no | 0.091 | 0.000 | 0.073 | 0.667 | 0 |
| MLP, ablation | no | 0.140–0.258 | 0.000–0.084 | 0.147–0.165 | 0.550–0.568 | 0 |
| Naive share baseline | — | 0.871 | 0.065 | 0.028 | 0.943 | — |
| Step baseline | — | 1.000 | 0.368 | 0.248 | 0.682 | — |
| Count baseline | — | 1.000 | 0.652 | 0.174 | 0.545 | — |
| Structure baseline | — | 0.765 | 0.394 | 0.174 | 0.604 | — |

Brackets are 95% Wilson intervals (seed 0 for the stochastic models). Coverage is decided episodes over
all episodes. Fault-free rates come from 91 transformer-days of the fault-free year's test weeks.
Paired bootstrap against the frozen method, seed 0: gradient boosting coverage −0.201 (−0.265 to
−0.140) and missed-outage rate +0.055 (0.009 to 0.110); MLP coverage +0.110 (0.049 to 0.163) and
missed-outage rate +0.174 (0.110 to 0.257).

**Untouched rural network, test weeks (66 outage and 110 communication episodes).** The frozen method
covered 0.494 with no false or missed outages. Missed-outage rates of the full-feature classifiers:
logistic regression 0.091, gradient boosting 0.273–0.288, MLP 0.242–0.303. All classifiers had no
fault-free false outages (frozen method: 24.1 per transformer-year).

**Whole-feeder outages.** Frozen method missed 0.011 on both networks. Gradient boosting missed
0.143–0.180 and the MLP 0.149–0.266. Logistic regression missed 0.009 on the semi-urban network but
decided only 0.207 of episodes.

## Hypotheses

- **H-A (no classifier beats the frozen method while meeting the limits on the urban network):
  supported.** No full-feature classifier met all three limits on the urban test; none had a feasible
  band on validation.
- **H-B (without the energy-balance features, classifiers fall to the level of the structure
  baselines): supported, but only through the protocol's infeasibility clause.** No ablation
  classifier except logistic regression had a feasible band, and that one decided almost nothing.
  On raw numbers the gradient-boosting ablation decided more accurately (0.667) than the count and
  structure baselines (0.545 and 0.604), with a much lower error sum, so the ablation is not
  literally at baseline level.
- **H-C (the classifiers' safety holds on the rural network): not supported.** For every
  full-feature run the upper 95% bound of the missed-outage rate is above 0.05 (0.184 to 0.422).

## What else was measured

- **Fault-free false outages.** Every classifier gave none on either network. This is better than
  the frozen method (40.1 and 24.1 per transformer-year).
- **Missed outages are the binding limit.** On validation, even at the lowest threshold tried, the
  full-feature classifiers missed 0.089 (logistic regression), 0.179–0.196 (gradient boosting) and
  0.232–0.250 (MLP) of outages, against 0.036 for the frozen method.
- **What the models rely on.** Group size is the largest input by both the standardised
  logistic-regression coefficients (2.14) and the mean absolute SHAP values of gradient boosting
  (0.386). Next come the standardised outage residual (logistic regression, −2.11) and the visible
  share (SHAP, 0.243).
- **Overfitting.** Training AUC 0.987–0.993 (gradient boosting) and 0.998–0.999 (MLP), against
  validation AUC 0.907–0.935.
- **Shuffled-label control.** Trained on permuted labels, validation AUC fell to 0.314 (logistic
  regression) and 0.337 (gradient boosting), against 0.935 with the real labels. The control loses
  its discrimination. It falls below 0.5 rather than at 0.5. Our reading (HYPOTHESIS): the fitted
  noise happens to run against group size, the strongest real predictor. One permutation only.
- **Leak checks.** No classifier reached an accuracy when deciding of 0.99 on any test set. The leak
  test (`tests/test_classifier_study.py`) passes. The frozen method's 0.995 is the registered result
  and was audited earlier (`results/leak_audit.json`).
- **Mixed groups.** Groups with an outage share between 20% and 80%: 14 (development events), 12
  (urban), 20 (rural), 16 and 6 (feeder families).
- **Check of the pipeline.** The frozen verdicts regenerated for this study agree with the stored
  records group for group, and the frozen urban and rural metrics equal the registered ones.

## Limitations

- Post-hoc: both evaluation networks were examined in earlier work.
- Simulator labels only; the classifiers learn our simulator. One training network.
- Every classifier was calibrated to the share of outages among all silent groups (202 of 8 505
  training groups). Most groups are 1-meter random data losses. Small outage groups therefore get low outage probabilities,
  which is the likely cause of the missed outages (HYPOTHESIS, not tested). Training weighted by
  episode, or a prior correction, might change the outcome. It was not tried, because the protocol
  forbids tuning after the test.
- With no feasible band, each classifier was tested at the band with the lowest validation error
  sum, as the protocol specifies.
- Three seeds; one permutation for the control; 1 000 bootstrap resamples.

## Text for proposal Section 4.2 (at most 150 words)

> Supervised comparison (post-hoc, simulated). On the same silent groups we trained logistic
> regression, gradient boosting and a small neural network on labelled simulated events from the
> development network, and tested them once on the two unseen networks under the same three safety
> limits. No classifier met the limits on validation data. On the held-out urban network the frozen
> method decided 0.72 of episodes and missed 0.009 of outages; gradient boosting decided 0.52–0.56
> and missed 0.064–0.073; the neural network decided 0.82–0.89 but missed 0.17–0.23. On the rural
> network the classifiers missed 0.09 to 0.30 of outages. The classifiers gave no fault-free false
> outages, against 40 per transformer-year for our method. Group size was their largest input.
> Removing the energy-balance features cut their coverage sharply. A learned fusion remains a
> candidate for Phase 2; the registered method is unchanged.

Figures and tables contain information from the SimBench database, made available under the ODbL 1.0.
