# CP7 — Held-out evaluation

Protocol: `docs/eval_protocol.md`, committed in 6f9d9e0 before the run. The run itself is
`python -m shahid.cp7_heldout` → `results/cp7_heldout.json` (commit 9de959a, config hash
a011dae77ec4). It was run **once**, and the method was not changed afterwards. The leak audit is
`python -m shahid.leak_audit` → `results/leak_audit.json` (commit 03afc74). Ledger C7-01 to C7-07.

Two targets, both scored on test weeks only (week % 4 = 3) with seeds 301–303:
- **Held-out grid** urban6: 109 outage and 155 comms episodes.
- **Development grid** semiurb5 test weeks: 105 outage and 159 comms episodes.

## Results (primary detector bayes, frozen thresholds; 95% bootstrap CIs)

| Metric | Held-out urban6 | Dev semiurb5 (test weeks) |
|--------|------|------|
| Accuracy when decided | 0.995 | 1.000 |
| Abstention (sent to a human) | 0.277 (0.223–0.333) | 0.303 (0.250–0.352) |
| Outage recall | 0.670 (0.578–0.752) | 0.619 (0.524–0.714) |
| Comms recall | 0.755 (0.684–0.819) | 0.736 (0.667–0.805) |
| Precision, outage / comms | 1.000 / 0.992 | 1.000 / 1.000 |
| False-outage rate | 0.000 (0.000–0.000) | 0.000 |
| Missed-outage rate | 0.009 (0.000–0.028) | 0.000 |
| Median latency (intervals of 15 min) | 2 | 2 |
| Fault-free false outages per meter-day (Wilson 95%) | 0.0010 (0.0005–0.0018) | 0.0008 (0.0004–0.0017) |
| Expected-load error, matched comms episodes | 18.2% (MAE 0.625 kWh) | 19.2% (MAE 0.611 kWh) |
| 90% interval coverage of expected load | 0.852 | 0.847 |
| Brier score of P(comms) | 0.048 | 0.049 |

## Baselines on the same episodes (held-out urban6)

| Method | Balanced correct | Abstention | False outage | Missed outage | Fault-free false outages per meter-day |
|--------|------|------|------|------|------|
| **bayes** (primary) | 0.712 | 0.277 | 0.000 | 0.009 | 0.0010 |
| ztest | 0.630 | 0.364 | 0.000 | 0.009 | 0.0002 |
| lr | 0.697 | 0.280 | 0.039 | 0.009 | 0.0038 |
| share | 0.698 | 0.280 | 0.045 | 0.000 | 0.0045 |
| naive baseline | 0.832 | 0.129 | 0.065 | 0.028 | 0.0104 |
| step baseline | 0.692 | 0 | 0.368 | 0.248 | 0.0629 |
| count baseline | 0.587 | 0 | 0.652 | 0.174 | 0.0039 |
| structure baseline | 0.486 | 0.235 | 0.394 | 0.174 | 0.0031 |

- **Generalisation.** The frozen thresholds transfer to a grid of a different type: 4 loads per bus,
  7 feeders, less PV. All three CP5 safety constraints still hold on urban6. Fault-free false
  outages sit exactly at the 0.001 per meter-day budget (10 alarms), with a Wilson interval up to
  0.0018.
- **The trade-off is the same as in CP5/CP6.** The naive baseline has a higher balanced score
  because it rarely abstains. It also calls 6.5% of comms failures outages and raises 10× more
  fault-free false alarms. Bayes decides about 72% of episodes and almost never errs when it does.
- **Calibration.** Most probabilities lie in the outer bins (below 0.1: 80 episodes; above 0.9:
  124), and those bins are well calibrated (observed comms fraction 0.013 and 0.992). The
  intermediate bins hold 3–14 episodes each and are noisy (`results/figs/cp7_reliability.png`).
- **Expected-load intervals undercover slightly**: 0.85 against a nominal 0.90. The 68% sigma
  multiplier scaled by 1.645 is a Gaussian approximation and the residuals are heavy-tailed. This
  affects only the uncertainty figures, not the decisions, which use the Student-t likelihood.
- No held-out number was used to change the method.

## Leak audit (integrity rule 9: accuracy when decided ≥ 0.99)
Run on held-out urban6, seed 301, test weeks, bayes:

| Check | Result |
|-------|--------|
| Detector inputs (`readings`, `trafo`, `meters`, `zones`) come only from observed/ and context/; columns shared with truth or label tables, other than join keys | none |
| `tests/test_no_leak.py` (reads only observed/context; mutation-checked in CP2) | pass (14/14 tests) |
| Actual transformer series | accuracy when decided 1.000 on 63 decided episodes (Wilson 95% 0.943–1.000), outage recall 0.641, missed outage 0 |
| Transformer series shifted by 7 days | accuracy when decided 0.627, outage recall 0.103, missed outage 0.513 |
| Transformer series from another seed (same customers, without these outages) | accuracy when decided 0.613, outage recall 0.026, missed outage 0.615 |

Outage calls disappear when the transformer stops showing the outage's physical effect. Comms
recall stays roughly unchanged, because a comms failure leaves the transformer series unchanged.
This is what a physics-driven detector should do. The near-perfect accuracy when decided comes
from abstaining on ambiguous cases, not from leakage. It is reported together with the abstention
rate and never alone.
