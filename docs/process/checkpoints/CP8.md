# CP8 — Single-meter faults (time-boxed)

## Implemented
- `shahid/cp8_single_meter.py`: injects stuck, gain, bias and noise faults into one meter's observed readings for 7 days. Tests three simple detectors (identical-run rule, own-history daily ratio, energy-balance gap shift) with thresholds calibrated on fault-free weeks.
- `docs/process/findings/08_single_meter.md`.

## Measured
- C8-01 to C8-03. Gain errors, small biases and added noise on a single meter are detected in at most 20% of episodes at 1–3% false alarms. A stuck meter is caught every time, but only because the simulator never produces naturally repeated readings.

## Failed or surprising
- Customer variability (diversity model) makes own-history thresholds extremely wide (0.011× to 4.0×).
- The balance check's threshold rests on only 36 fault-free weeks, so its false-alarm estimate is coarse.

## Assumptions remaining
- A-METERERR: real meter fault statistics and real vacant-home behaviour are unknown.

## Decision and recommendation
- Report single-meter faults as "not detectable with the Phase 1 method", except stuck meters, with the simulator caveat. Proceed to CP9.
- **Superseded (submission packaging, 2026-10-12):** the stuck-meter result is withdrawn as a simulator artefact and is not reported; it is on the "Do NOT report" list in [docs/RESULTS.md](../../RESULTS.md).
