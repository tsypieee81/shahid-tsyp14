# CP6 — Detectability and robustness experiments

## Implemented
- `shahid/cp6_sweep.py`: 28 cells (nominal, diversity, history, meter noise, transformer-meter error, constant and load-shaped unmetered energy, PV share, concentrator layout, six hard negatives). Each has 2 seeds and paired episodes. The detector is frozen; only the history cells refit. Runs in parallel processes capped by `SHAHID_WORKERS` (default 4), and finished cells are skipped on rerun.
- `shahid/episodes.py`: hard-negative kinds (comms failure during a real load change, simultaneous outage and comms failure).
- `shahid/cp6_summary.py`: cell table and detectability curves with Wilson intervals. `shahid/figures.py`: detectability (correct, wrong, abstention) and robustness figures.
- `docs/process/findings/06_detectability.md`.

## Measured
> **Superseded by CP10 (post-hoc, 2026-10-07):** the 16% / 32% values are bin edges. The continuous estimate of the share at which P(correct) reaches 0.90 is 0.160 (0.124–0.207) nominal, 0.083 (0.059–0.119) on the held-out grid, and 0.114 (0.080–0.165) on the development grid's test weeks. A signal-to-noise axis is more consistent across conditions. See `docs/RESULTS.md` §1 and ledger CP10-T3.

- C6-01 to C6-07 (see the ledger; per-cell stamps in its appendix). Nominal: accuracy when decided 0.990, abstention 0.401, missed outages 0.013, false outages 0. Decisions are reliable (≥ 0.94 correct, ≤ 6% abstention) once the silent customers' expected energy exceeds about 16% of the transformer's energy over the decision window. Below 1% the detector always defers. No false outages in any detectability bin.
- Main sensitivities: load-shaped unmetered energy (missed outages 12% at 5 kW and 24% at 10 kW), transformer-meter gain error 2% (missed 4.6%, false 1.9%), diversity (abstention 34–52%).

## Failed or surprising
- Simultaneous outage and comms failure in disjoint zones: 37% of outages missed. Grouping silent meters by onset merges the two events.
- Load-shaped unmetered energy defeats the recent-gap baseline. Constant unmetered energy does not matter at all.
- Night outages are easier than daytime ones.
- The sweep was stopped once on the user's request because the laptop overheated, and was restarted with a 4-worker cap. One cell crashed on a baseline slicing bug at the first eligible onset. It was fixed (b27d428) and only that cell was rerun. The bug could only crash, never change a value.
- Cells carry three commit stamps (ee3c840: 8 cells, 6f9d9e0: 19, 9de959a: 1). Only the worker cap, the baseline slice fix and documents changed between them. The slice bug could only crash a run, never change a value.

## Assumptions remaining
- A-DIV (diversity) and P7 (transformer meter exists and is accurate) remain the assumptions that results depend on most. Load-shaped non-technical losses are a new, identified risk.

## Decision and recommendation
- Keep the frozen method for CP7. Report the simultaneous-event failure and the unmetered-energy sensitivity as limitations, with zone-decomposition of silent sets and a load-dependent gap model as the upgrade paths.
