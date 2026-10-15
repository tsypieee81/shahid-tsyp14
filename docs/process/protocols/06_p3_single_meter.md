# Protocol 06 — Priority 3: single-meter faults and falsified readings (goal G1)

Registered 2026-10-14, before any code for it exists. Frame: protocol 00. Baseline: CP8
(`docs/process/findings/08_single_meter.md`, ledger C8-01 to C8-03): at most 20% of gain errors were
detected at a 1–3% false-alarm rate.

## Scope (binding)
Voltage is a G1 tool for meters that **still report** (degraded, biased, falsified). It cannot remedy
the merge case of finding 09: a silent meter reports no voltage. Voltage is **not** tested against the
merge case; that case belongs to protocol 03.

## Detectors (module `shahid/p3_single_meter.py`)
- **D1, neighbour voltage.** For meter i, the voltage residual u_i(t) = V_i(t) − median of V over the
  other meters on the same feeder at t. Its own load lowers its own voltage, so on fault-free training
  weeks fit u_i = a_i − b_i·E_i (least squares, reported energy). Daily statistic: mean of
  u_i − (a_i − b_i·E_i) over the day. A falsified energy reading breaks the relation while the voltage
  still follows the true load. ASSUMPTION: the fault affects the energy register, not the voltage
  channel.
- **D2, gap regression on individual meters.** Over a 7-day window, ridge regression (penalty 1.0 on
  standardised regressors) of the transformer gap T − ΣE on every meter's reported energy. Statistic
  per meter: its coefficient. A gain error g on meter i makes the gap proportional to its readings,
  with coefficient about (1 − g)/g. D2 also names the meter.
- Thresholds of both: 1% false alarms per daily check on fault-free weeks (as CP8).

## Fault set (as CP8, new seeds)
One meter corrupted for 7 days; 150 episodes per setting; gain 0.5, 0.8, 0.9, 1.1, 1.2, 1.5; bias
−0.05, −0.02, +0.02, +0.05 kWh per interval; added noise sd 0.02, 0.05, 0.2. Falsified readings
(theft-like) are the gain < 1 and negative-bias settings. Development: semiurb5 fault-free year,
seed 951. Confirmatory: rural2, seed 851 (protocol 05).

## Endpoints
- **H3 (primary, confirmatory rural2)**: for gain × 0.8, gain × 0.5 and bias −0.05, detection rate
  ≥ 0.5 at ≤ 1% measured false alarms, for D1 or D2 (CP8's best was ≤ 0.20). Supported per fault
  setting; Wilson intervals.
- Localisation for D2: share of detected episodes where the corrupted meter has the largest
  statistic.
- **Optimism limit, stated in every report**: the benchmark grids hold the upstream (MV) voltage
  fixed, so feeder-wide voltage swings from tap changes and MV variation are absent. The neighbour
  median removes common-mode swings, but D1 will look better in simulation than in the field.

## Compute ESTIMATE
Development ≈ 1 h; confirmatory part ≈ 1 h inside protocol 05.
