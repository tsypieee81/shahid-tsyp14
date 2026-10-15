# CP1 — SimBench reality check (2026-10-05)

All numbers come from `results/cp1_simbench_facts.json` (command `python -m shahid.cp1_facts`,
commit 43b6eda, config hash d4caee1b0b84) and `results/cp1_diversity.json`
(`python -m shahid.cp1_diversity`). Ledger IDs C1-xx in `docs/CLAIMS_LEDGER.md`.

## Environment (FACT, measured)
- Python 3.11.7 venv in `.venv`, created with uv. Pins in `requirements.txt`, full lock in `requirements.lock`.
- pandapower 3.5.5 + simbench 1.6.3 install together without conflicts. They load all 18 LV grid variants and converge on every step tested. That is the reason for this pair: it is the current release pair and it works.
- numba 0.68.0 installs alongside numpy 2.4.6. One power flow takes about 15–20 ms per step on one core (C1-01).
- SimBench data ships inside the pip package (`simbench/networks/1-complete_data-*`). No download is needed.

## What SimBench gives (scenario 0, `-sw` variants)

| Grid | loads | PV units | feeders | trafo MVA | annual load MWh | annual PV MWh |
|------|-------|----------|---------|-----------|-----------------|---------------|
| rural1 | 13 | 4 | 4 | 0.16 | 200 | 104 |
| rural2 | 99 | 8 | 4 | 0.25 | 261 | 94 |
| rural3 | 118 | 17 | 9 | 0.4 | 349 | 125 |
| semiurb4 | 41 | 1 | 3 | 0.4 | 388 | 4 |
| semiurb5 | 104 | 9 | 6 | 0.63 | 475 | 91 |
| urban6 | 111 | 5 | 7 | 0.63 | 537 | 38 |

(C1-02; one load is treated as one customer meter, ASSUMPTION A-METER.)

- **Profiles**: one year, 2016-01-01 00:00 to 2016-12-31 23:45, 35 136 steps of 15 min. Absolute load arrays are 35 136 × n_loads in MW and Mvar.
- **Topology**: all grids are radial in the `-sw` variant with zero open switches. Switches are load-switches at both ends of every line, plus a circuit breaker at the transformer. There is no fuse, relay or protection data. Each line opening isolates a distinct set of customers, giving one candidate zone per line (for example 109 zones in semiurb5).
- **Not provided**: metering, communication, a transformer measurement, protection. Every such layer here is our own model.
- **Scenario digit**: PV count grows with the digit (semiurb5: 9, 14, 15 PV units) and storage appears in scenarios 1 and 2. That storage has no profile, so it runs at a fixed setpoint and discharges every interval. This is not physical behaviour over a time series, so scenarios 1 and 2 are not used. Scenario 1–2 rural1 also overloads its transformer to about 256%.

## Power flow and truth balance (two weeks: 15–21 Jan and 21–27 Jun 2016)
- 1 344/1 344 steps converge in every grid variant (C1-03).
- semiurb5 scenario 0: voltages 1.006–1.029 pu, transformer peak loading 23.1%, line losses 0.17% of load, transformer losses 3.33% of load, 62 reverse-flow intervals (C1-04).
- **Sign conventions** (prior P5, established empirically, `tests/test_balance.py`): `res_load.p_mw` and `res_sgen.p_mw` are positive for consumption and generation. `res_trafo.p_lv_mw` is positive into the transformer, so power delivered into the LV network is `-p_lv_mw`. `res_storage.p_mw` is positive when charging.
- **Balance**: `-p_lv = Σload − Σpv + Σstorage + Σline losses` closes to at most 6e-8 MW (0.06 W) in all 18 variants (C1-05). Storage must be included. Without it, scenarios 1–2 leave up to 0.25 MW unexplained.
- **Metering point**: the transformer meter is modelled on the LV terminals, so transformer losses (mostly the constant 1.65 kW iron loss in semiurb5) sit outside the balance. On the LV side the only structural gap is line losses, about 0.2% of load in scenario 0.
- **Energy per interval**: kWh = mean MW × 1000 × 0.25. This assumes a profile value is the mean power over the interval starting at its timestamp (ASSUMPTION A-INTERVAL, untested).

## Profile diversity (prior P2): supported, and it matters
- Loads that share a profile name are **exact scaled copies**. After normalising by peak, the maximum difference is 2.2e-16 in every grid (C1-06).
- semiurb5 has 104 loads but only 10 distinct normalised shapes, five of them household shapes (H0-A to H0-L) shared by 92 customers.
- Among semiurb5 households, 21.3% of customer pairs have correlation above 0.999 and the mean pairwise correlation is 0.355 (C1-07).
- **Consequence**: without added diversity, the summed load of a silent group is a fixed combination of a few shapes, and any method that predicts it from neighbours with the same shape is exact by construction. SimBench as-is is not diverse enough for an expected-load study.
- **Remedy (DESIGN CHOICE, ORIGINAL)**: `shahid.world.diversify` with knob d adds a per-customer daily time shift, a daily scale factor and AR(1) interval noise, all mean-one. d = 0 reproduces SimBench exactly. Effect on semiurb5 households (C1-08):

| d | mean pairwise corr | pairs with corr > 0.999 | annual energy vs d = 0 |
|---|--------------------|-------------------------|------------------------|
| 0 | 0.355 | 21.3% | 1.000 |
| 0.25 | 0.289 | 0% | 1.000 |
| 0.5 | 0.232 | 0% | 0.999 |
| 1.0 | 0.129 | 0% | 0.998 |
| 2.0 | 0.026 | 0% | 0.998 |

The knob magnitudes are not calibrated against real households (ASSUMPTION A-DIV). CP6 sweeps d.

## Reuse survey (time-boxed, web access available)

| Candidate | What was verified | Use |
|-----------|-------------------|-----|
| UCI ElectricityLoadDiagrams20112014 | Official UCI page: 370 clients, 15-min kW, 2011–2014, CC BY 4.0, DOI 10.24432/C58C86. Client type not stated as households | Not used. Possible calibration source for d. |
| London Datastore "SmartMeter Energy Consumption Data in London Households" (Low Carbon London) | Official page: 5 567 households, half-hourly kWh, Nov 2011–Feb 2014, "Creative Commons Attribution" (version not shown on the summary), about 765 MB | Not used. Half-hourly, so not a direct 15-min substitute. The best candidate for calibrating d. |
| LEAD1.0 | Not checked | UNVERIFIED |

## Decisions (see `docs/process/decisions/0001-grid-and-diversity.md`)
- Development grid `1-LV-semiurb5--0-sw`. Held-out grid `1-LV-urban6--0-sw`, not touched until CP7.
- Scenario 0. PV share is varied with a `pv_scale` parameter instead of the scenario digit.
- Period: the full 2016 profile year is affordable (about 35 k steps × 16 ms ÷ parallel workers). Splits are by week.
- Diversity: parameter d, swept in CP6. Nominal d = 0.5 (DESIGN CHOICE, uncalibrated).

## Priors
| Prior | Outcome | Evidence |
|-------|---------|----------|
| P1 | supported: semiurb4 has 41 loads, semiurb5 104 | table above |
| P2 | supported: loads are exact scaled copies of 5–23 shapes per grid | C1-06, C1-07 |
| P3 | supported: no protection, metering, comms or trafo measurement in the network tables | switch types `l/LS` and `t/CB` only |
| P4 | supported: PV count and storage depend on the scenario digit | `counts` per grid in the facts JSON |
| P5 | resolved: conventions determined empirically | `tests/test_balance.py` |
| P6 | supported for 1 year at 15 min (2016). German origin rests on the SimBench authors' institutions in the package licence. No Tunisian claim | facts JSON `profile_time_first_last` |
| P7 | untested; cannot be tested in simulation | stated limitation |
