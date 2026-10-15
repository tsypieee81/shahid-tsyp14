# 0001 — Development grid, held-out grid, scenario, period, diversity

**Context.** CP1 measured all 18 SimBench LV variants (`docs/process/findings/01_simbench_reality.md`).

**Options.** Dev grid: semiurb4 (41 loads), semiurb5 (104), rural2/rural3 (99/118), urban6 (111).
Scenario: 0, 1, 2. Diversity: SimBench as-is, stochastic per-customer variation, real public series.

**Evidence.** semiurb4 is too small for group-size sweeps. semiurb5 has about 100 customers,
6 feeders, 109 nested candidate zones and 9 PV units (PV is 19% of annual load energy). urban6 has a
different topology class (4 loads per bus on 36 buses, 7 feeders), so it is a real generalisation test.
Scenarios 1–2 add storage with no profile, which discharges at a fixed setpoint all year. SimBench
loads are exact scaled copies of a few shapes. Public 15-min household data with a clear licence was
not found in the time box.

**Choice.** Dev = `1-LV-semiurb5--0-sw`. Held-out = `1-LV-urban6--0-sw`. Scenario 0. Full 2016
year, split by week. PV share via a `pv_scale` parameter. Diversity via `shahid.world.diversify`
knob d (nominal 0.5, swept in CP6).

**Consequence.** All conclusions are conditional on an uncalibrated diversity model (A-DIV).
Calibrating d against the Low Carbon London households is a possible upgrade if time allows.
