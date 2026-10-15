# Anomaly and data-quality generation

Status: IMPLEMENTED and SIMULATED. Code: `shahid/world.py` (truth), `shahid/observe.py`
(observation), `shahid/scenario.py` (events, labels). Defaults: `configs/defaults.yaml`. Every
parameter value is an ASSUMPTION or DESIGN CHOICE (register: `docs/ASSUMPTIONS.md`). No value is
taken from a metering or communication standard, and none represents Tunisian (STEG) practice.

## Pipeline

1. **Profiles** (REUSED): SimBench absolute load and PV profiles, 2016, 15-min.
2. **Customer diversity** (ORIGINAL, `diversify`, knob d): per customer and day, a time shift of
   round(N(0, 4d)) intervals and a scale LogNormal(−s²/2, s) with s = 0.3d. Per interval, an AR(1)
   log-noise with φ = 0.7 and marginal sd 0.5d, corrected to mean one. d = 0 is SimBench unchanged.
3. **Baseline truth** (REUSED solver): one pandapower AC power flow per interval for the full year.
   Cached in `cache/` by world-config hash.
4. **Physical events** re-solve the power flow only for the rows they affect (`apply_physical`).
5. **Unmetered energy** is added to the true transformer energy.
6. **Observation**: meter error, transformer-meter error, delivery (loss, delay, failures).
7. **Labels** are written by the same code that injects the events.

## Classes

| Class | Layer | Generation rule | Parameters (default) | Label |
|-------|-------|-----------------|----------------------|-------|
| Physical outage | truth | Open one LV line (`line` index or `feeder` k). Customers downstream are isolated. The power flow is re-solved for rows [a, b). Isolated loads and their PV go to 0 and their voltage is undefined. Unpowered meters send nothing | `start_step`, `duration_steps`, line | episode `OUTAGE`; cells `OUTAGE` |
| Communication failure | observation | Readings of a meter set are not delivered during [a, b). The set is a concentrator group, an electrical zone (`zone`, for the hard negative where comms and zone coincide) or an explicit list. With `backlog: true` the readings arrive after b plus U{0..`backlog_spread`} intervals | `backlog` (true), `backlog_spread` (4) | episode `COMMS_FAILURE`; cells `COMMS_FAILURE` |
| Concentrator mapping | context | `aligned`: one concentrator per feeder. `random`: same group sizes, meters shuffled | `comms.concentrators` (aligned) | — |
| Random missing reading | observation | Each reading independently never arrives with probability p | `p_missing` (0.01) | cells `RANDOM_LOSS` |
| Delayed reading | observation | Each reading independently arrives late with probability p, by Geometric(1/mean) extra intervals | `p_delay` (0.03), `delay_mean_intervals` (4) | cells `DELAYED` |
| Real load change | truth | Multiply the load of a meter set by a factor over [a, b), then re-solve. Used to build "comms failure during a real load change" | `factor`, `zone` or `meters` | episode `LOAD_CHANGE` |
| Unmetered energy | truth | Energy the transformer sees but no meter reports. `constant`: kw × 0.25 kWh per interval. `profile`: kw × aggregate-load shape normalised to mean 1. Added after the power flow | `world.unmetered` (none) | in `truth/powerflow.npz` |
| Meter error | observation | Fixed gain 1 + N(0, `gain_sd`) per meter. Noise N(0, sqrt((`noise_rel_sd`·E)² + `noise_abs_kwh`²)). Quantised to `quant_kwh` | 0.005, 0.002, 0.0005 kWh, 0.001 kWh | — |
| Transformer-meter error | observation | Same model, one meter | `gain_sd` 0.002, `noise_rel_sd` 0.001, `quant_kwh` 0.01 | — |
| Outage backfill | observation | Optional, default off. After restoration, meters upload the outage intervals with 0 kWh | `outage_backfill` (false) | — |
| Last-gasp message | observation | Optional, default off. A power-fail message at outage onset in `observed/events.parquet`. No headline result uses it | `last_gasp` (false), `p_last_gasp` | — |

The transformer meter is assumed always to deliver on time (ASSUMPTION A-TCOMMS).

## Measured properties of the generator (`results/cp3_checks.json`, ledger C3-xx)

- **Re-solve vs naive subtraction** (600 cases: 30 zones of 1–37 meters × 20 random intervals).
  The re-solved transformer energy differs from "baseline minus the lost customers' energy" by a
  median of 0.0015 kWh per interval and at most 0.047 kWh. Where more than 0.1 kWh was lost, the
  difference is 0.18% of the lost energy at the median and 0.76% at the 95th percentile. The mean
  difference is negative: an outage also removes the line losses of the isolated part.
- **Unmetered energy added after the power flow** vs a real 2 kW load at the far end of the
  largest feeder (200 intervals). The error is at most 0.0089 kWh per interval, 1.8% of the
  injected 0.5 kWh. Mean error is +0.0028 kWh, the extra line loss the post-hoc addition ignores.
- **Fault-free baseline** (semiurb5, d = 0.5, full year): 1.006% of readings never arrive and
  108 897 readings are delayed. True line losses are 769 kWh, 0.2% of transformer energy. The
  transformer-meter gain draw in this seed is 0.9974, so its calibration error (−0.26%) is larger
  than all line losses.

## Not modelled
Phase imbalance (the power flow is balanced three-phase), fuse operation dynamics, partial
outages of one phase, meter clock drift, tariff-register semantics, and single-meter faults (CP8).
