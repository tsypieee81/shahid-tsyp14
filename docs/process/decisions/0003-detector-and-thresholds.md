# 0003 — Detector and threshold-selection rule

**Context.** CP5 compared four physics detectors and four baselines on validation weeks
(`docs/process/findings/05_detectors.md`).

**Options.** Maximise balanced correct-cause rate (v1). Add a fault-free false-alarm budget (v2).
Add safety constraints on missed and false outages and minimise abstention (v3).

**Evidence.** v1 picked a detector that raised about 4.6 false outage alarms per day on this
neighbourhood's ordinary data loss. v2 picked a detector that missed 37% of outages by calling
them comms failures, which the escalation table would then handle without a human. Under v3 only
bayes and ztest are feasible, and bayes abstains least (0.337 against 0.398).

**Choice.** Primary detector: `bayes`. Student-t likelihood ratio, prior 0.5, abstention band 0.03,
no minimum-energy cut, decided at the first of L = 0..4 extra intervals that is not uncertain.
Selection rule v3 is a DESIGN CHOICE: missed outages ≤ 5%, false outages ≤ 5%, fault-free false
outages ≤ 0.001 per meter-day, then least abstention. Thresholds are frozen in
`results/detector_params.json`.

**Consequence.** About a third of silent episodes go to a human, almost all with small expected
energy. The headline is accuracy when decided plus an abstention rate, never one number alone.
The constraint values are ours, not an operator's.
