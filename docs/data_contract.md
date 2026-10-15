# Data contract

Status: IMPLEMENTED (CP2 skeleton). All data is SIMULATED from SimBench profiles and pandapower
power flows. Nothing here comes from a real utility.

One scenario = one directory `data/<config-stem>_<config-hash>/` with four areas. The detector's
entry point (`shahid.detect.load_inputs`) reads only `observed/` and `context/`. The test
`tests/test_no_leak.py` fails if it touches `truth/` or `labels/`.

Time: `interval_start` is the start of a 15-minute interval, timezone-naive, in the SimBench
profile year 2016. Energy over an interval is mean power × 0.25 h (ASSUMPTION A-INTERVAL: a
SimBench profile value is the mean power over the interval that starts at its timestamp).

## observed/ (what a utility data export could contain)

`meter_readings.parquet`: one row per reading that arrived. A reading that never arrived has no row.

| Column | dtype | Unit | Meaning | Real-world analogue |
|--------|-------|------|---------|---------------------|
| meter_id | str | — | customer meter, `m000`… | meter serial number |
| interval_start | datetime64 | — | start of interval | load-profile register timestamp |
| energy_kwh | float64 | kWh | net import over the interval (import − PV export). Negative = net export | difference of import and export registers |
| arrival_ts | datetime64 | — | when the head-end received it | head-end system receive time |

Planned for CP3 (not yet emitted): optional `voltage_v`, a `status` column, delayed and
backlog arrivals, meter error.

`transformer.parquet`: one row per interval.

| Column | dtype | Unit | Meaning | Real-world analogue |
|--------|-------|------|---------|---------------------|
| interval_start | datetime64 | — | start of interval | meter timestamp |
| energy_kwh | float64 | kWh | energy delivered from the transformer LV terminals into the LV network. Negative = reverse flow to MV | LV-side transformer meter. Existence in Tunisian substations is unverified (P7) |

The transformer meter sits on the LV side, so transformer losses are outside the balance.
Truth-level balance (verified in `tests/test_balance.py`):
`transformer = Σ customer load − Σ PV + Σ storage charging + line losses`.

## context/ (static information the detector may use)

`meters.parquet`

| Column | dtype | Unit | Meaning | Real-world analogue |
|--------|-------|------|---------|---------------------|
| meter_id | str | — | meter | serial |
| concentrator_id | int | — | data concentrator the meter reports through | AMI network inventory |
| pv_kw | float64 | kW | installed PV behind this meter (0 if none) | connection register |

`zones.parquet`: long format, one row per (zone, meter). A zone is the set of meters isolated
when one LV line opens. Zones are nested. DESIGN CHOICE: SimBench has no protection data.

| Column | dtype | Meaning | Real-world analogue |
|--------|-------|---------|---------------------|
| zone_id | int | pandapower line index that defines the zone | GIS feeder/section model |
| meter_id | str | member meter | customer-to-network connectivity |

## truth/ (hidden physical state, never given to the detector)

- `powerflow.npz`: arrays per interval: `load_p`, `sgen_p`, `vm_load` (pu, NaN when isolated), `trafo_p_lv`, `trafo_pl`, `line_pl`, `storage_p` (MW, pandapower signs), `converged`.
- `meter_energy_true.parquet`: wide, interval × meter, true net kWh. Zero for an outaged customer.

## labels/ (evaluation ground truth, emitted by the injector, never hand-written)

`episodes.parquet`

| Column | dtype | Meaning |
|--------|-------|---------|
| episode_id | int | event index in the scenario file |
| cause | str | `OUTAGE` or `COMMS_FAILURE` |
| start, end | datetime64 | event interval range, end exclusive |
| n_meters | int | silent meters |
| meters | str (JSON list of ints) | silent meter indices |

`manifest.json`: config, config hash, git commit, command, date.
