# CP2 — Walking skeleton

## Implemented
- `shahid/scenario.py`: config → truth/, observed/, context/, labels/ for one scenario. Outages open a line and re-solve the power flow for the affected intervals. A comms failure silences one concentrator.
- `shahid/detect.py`: naive detector using only observed/ and context/. It computes the visible share of the silent group's expected energy (same-slot 14-day median) with a fixed threshold of 0.5.
- `shahid/smoke.py` + `configs/smoke.yaml`: one command runs the whole path and prints verdict against truth.
- `tests/test_no_leak.py`: fails if the detector reads truth/ or labels/ or names them in its source. Mutation-checked: injecting a truth read makes it fail.
- `docs/data_contract.md`.

## Measured
- C2-01: smoke scenario, both episodes correct (the visible-share values of this superseded d = 0 run are withdrawn in CP12: its result file was overwritten; the current smoke run is ledger C2-01), about 18 s end to end. This shows the pipeline runs. It is not a performance claim.
- Re-solve check (exploratory, not ledgered): with a 22-meter feeder opened at a summer noon interval, the re-solved transformer power differed from naive load subtraction by about 35 W.

## Failed or surprising
- First smoke run labelled events with January timestamps for a June scenario. Fixed: timestamps now use the absolute step.
- The comms-failure visible share was well above 1 (value withdrawn in CP12, see above). The same-slot median underestimates the evening load on that day even with d = 0. CP4 has to quantify expected-load error.

## Assumptions remaining
- No meter noise, no transformer-meter error, no delays, no unmetered energy yet (CP3). H-core still untested.

## Decision and recommendation
- Keep the four-area layout and the detector entry point. Next is CP3: meter and comms error models, delayed and backlog delivery, unmetered energy, a scenario generator with emitted labels, and `docs/anomaly_generation.md`.
