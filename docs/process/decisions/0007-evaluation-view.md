# 0007: Simulation evaluation view and simulated track record in the operator UI preview

Date: 2026-10-13. Decided by the team (Phase 2 dashboard brief).

**Context.** The operator console preview (decision 0006, `ui/app.py`) replays stored simulations
(`shahid.demo_day`). Two things in it need simulation labels, which no operator would have:
- **an evaluation view**: what the verdicts of the replayed day were against the simulated truth;
- **the track record and override outcomes** of the trust view (proposal Section V-C), which in
  deployment would come from field confirmations that Phase 1 does not have.

**Decision.**
- Labels never reach the detector. `shahid.demo_day` passes only the observed and context tables to
  the frozen detector and never names truth or labels. The simulation outcomes are written by a
  separate module, `shahid.demo_eval`, into `results/demo/<scenario>_eval.json`.
- The evaluation view (`ui/panels/evaluation.py`) is a separate page behind an explicit toggle
  labelled "SIMULATION EVALUATION — labels are not available to the detector". It imports nothing
  from `shahid.detect`, is disabled in presentation mode, and is not reachable from the queue views.
- The trust view (`ui/panels/trust.py`) computes the track record per verdict class and the eventual
  outcome of overrides from the same `_eval.json` files. It says on screen that these are simulated
  outcomes standing in for field confirmations.
- The situation, queues, network, trace and audit views, and the evidence card, never open an
  `_eval.json`, `labels/` or `truth/` file.

**Evidence.**
- `tests/test_demo_day.py`: the replay opens no truth or labels file, and its verdicts equal a direct
  `shahid.detect` call on the same inputs.
- `tests/test_ui_panels.py`: the operator views open no outcome, labels or truth file at run time
  (every `open` is recorded); the evaluation view imports nothing from the detector.

**Consequences.** Counts in the evaluation view describe one simulated day and are not results; the
measured rates stay in the proposal (Section VI) and `docs/RESULTS.md`.
