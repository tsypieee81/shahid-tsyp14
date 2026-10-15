# CP3 — World depth

## Implemented
- `shahid/world.py`: cached full-year baseline truth (`cache/`), physical events re-solved only on affected rows (outage = open a line; real load change), overlapping events combine, unmetered energy (none / constant / profile).
- `shahid/observe.py`: meter gain/noise/quantisation, transformer-meter error, random loss, delays, concentrator failure with backlog, optional outage backfill and last-gasp (both default off), optional interval voltage.
- `shahid/scenario.py`: config (merged over `configs/defaults.yaml`) → truth/observed/context/labels. Labels are emitted per episode and per affected cell.
- `shahid/detect.py`: decision-time semantics. A group is silent when K = 2 readings have not arrived. The decision is taken L = 2 intervals later using only data that had arrived by then. Backlogged readings cannot leak the answer.
- `configs/baseline.yaml` (fault-free year, one command), `shahid/cp3_checks.py`, `docs/anomaly_generation.md`.
- Tests: `tests/test_world.py` (5), plus existing balance and leak tests. 11 pass.

## Measured
- C3-01: re-solved vs naive subtraction differs by at most 0.047 kWh per interval, 0.76% of the lost energy at p95.
- C3-02: post-hoc unmetered energy is within 1.8% of a power-flow-injected load.
- C3-03, C3-04: fault-free year has 1.006% lost readings. Line losses are 0.2% of transformer energy, and in this seed the transformer-meter gain error (−0.26%) is larger than all line losses.
- C2-01 rerun with nominal noise: both smoke verdicts still correct, but the outage share rose from 0.03 to 0.38.

## Failed or surprising
- The structural gap is dominated by transformer-meter calibration, not physics. The detector must learn the gap from history, never assume it.
- Random losses alone create about 11 silent groups per day (mostly single meters), so false-alarm control on small groups matters.
- The committed dataset is deferred. A full year is 11 MB observed plus 76 MB truth. Committing every regenerated version would bloat git, so one frozen snapshot is planned for CP7, with truth regenerable by command.

## Assumptions remaining
- New: A-METERERR, A-TMETERERR, A-COMMS, A-TCOMMS, A-NOBACKFILL (untested by nature: no real metering data). A-UNMET supported.

## Decision and recommendation
- Proceed to CP4: quantify expected-load error for silent groups, which now looks like the main limit on discrimination.
