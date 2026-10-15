# CP1 — Environment and SimBench reality check

## Implemented
- `.venv` (Python 3.11.7, uv); `requirements.txt` (top-level pins), `requirements.lock` (full freeze).
- `shahid/grid.py`: grid loading, absolute profiles, per-step power flow, candidate zones.
- `shahid/cp1_facts.py`, `shahid/cp1_diversity.py`, `shahid/world.py` (diversity knob, parallel solve).
- `tests/test_balance.py`: truth balance closes and sign conventions hold (3 tests pass).
- `results/cp1_simbench_facts.json`, `results/cp1_diversity.json`, `docs/process/findings/01_simbench_reality.md`, `docs/process/decisions/0001-grid-and-diversity.md`.

## Measured
- C1-01 to C1-08 in `docs/CLAIMS_LEDGER.md`, all from `python -m shahid.cp1_facts` and `python -m shahid.cp1_diversity`.
- Key: semiurb5-0 has 104 loads, 9 PV, 6 feeders. All 18 variants converge. Truth balance closes to ≤ 6e-8 MW. Loads are exact scaled copies of a few shapes.

## Failed or surprising
- P2 strongly confirmed: 10 shapes for 104 loads, and 21.3% of household pairs are perfectly correlated. SimBench as-is cannot support an expected-load study. Diversity is now a parameter.
- Scenarios 1–2 contain storage without a profile that discharges at a fixed setpoint every interval. The first balance check missed storage and showed a 0.25 MW residual. Fixed by including storage, and scenarios 1–2 are excluded.
- Line losses are only about 0.2% of load on the LV side, so the structural gap is small. Detection difficulty will be set mostly by meter error, expected-load error and unmetered energy.
- Transformer losses are about 3% of load, mostly constant iron loss. They matter only if the transformer meter were on the MV side.

## Assumptions remaining
- Untested: H-core, P7, A-METER, A-INTERVAL, A-PV, A-ZONE, A-DIV (new, uncalibrated), A-TMETER, A-CONC.

## Decision and recommendation
- Dev grid semiurb5-0, held-out urban6-0, scenario 0, full year split by week, diversity knob d (nominal 0.5). Proceed to CP2.
