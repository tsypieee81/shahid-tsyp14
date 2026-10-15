# CP7 — Held-out evaluation and reproducibility

## Implemented
- `docs/eval_protocol.md`: metrics, matching rules, splits and the frozen method, committed in 6f9d9e0 before the run.
- `shahid/cp7_heldout.py`: held-out grid urban6 plus dev-grid test weeks, seeds 301–303. Reports all metrics with bootstrap CIs, Wilson intervals for fault-free alarms, expected-load MAE and coverage, Brier score and reliability.
- `shahid/leak_audit.py`: input provenance and two transformer-substitution controls on held-out data.
- `shahid/reproduce.py`: every stage in order as Python entry points. `shahid/figures.py`: all figures from result files.

## Measured
- C7-01 to C7-07. On held-out urban6 the primary detector is right 99.5% of the time when it decides and abstains on 27.7%. It made no false outages and missed 0.9% of outages, with 0.0010 fault-free false alarms per meter-day. The best baseline calls 6.5% of comms failures outages and raises 10× more fault-free false alarms.
- Leak audit: with the transformer series shifted or replaced, outage recall falls from 0.64 to 0.10 and 0.03.

## Failed or surprising
- The frozen thresholds held all three safety constraints on a grid of a different type. The fault-free false-alarm rate sits exactly at the 0.001 budget.
- Expected-load interval coverage is 0.85 against a nominal 0.90 (Gaussian scaling of a heavy-tailed error).
- Clean-clone reproduction (done in CP9, C9-02): a fresh clone with a fresh environment regenerates the fast stages and the dataset identically. The long stages (cp4, cp5_compare, cp6, cp7, several hours) were not re-run in a clone.
- The held-out run was executed once. Before it, the session ended once with the run not yet started, and one sweep crash delayed it. The results were not looked at before the run completed, and the method was not changed after.

## Assumptions remaining
- H-core: supported on held-out data for silent groups with enough expected energy (see CP6 curve). Unresolvable below about 1% of transformer energy.
- A-DIV, P7 and A-METERERR/A-TMETERERR remain untested against real data.

## Decision and recommendation
- Method frozen as final for Phase 1. CP7 finished on 7 October, before 11 October, so CP8 (single-meter faults, time-boxed) runs next, then CP9.
