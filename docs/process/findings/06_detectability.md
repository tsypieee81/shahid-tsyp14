# CP6 — Detectability and robustness

Sources: `results/cp6/<cell>.json` (`python -m shahid.cp6_sweep`) and `results/cp6_summary.json`
(`python -m shahid.cp6_summary`). Figures: `results/figs/cp6_detectability.png` and
`results/figs/cp6_robustness.png`. Ledger C6-01 to C6-07.

## Setup
- Base family `configs/cp6_base.yaml`: development grid, nominal parameters, 50% outages and 50%
  zone-shaped comms failures drawn from the same zones, so silence structure carries no
  information. Seeds 201 and 202. Weeks 0–2 only; week 3 stays reserved for CP7.
- Every cell scores the same 504 episodes (237 outages, 267 comms failures), so cells are a paired
  comparison. Exceptions are cells that change the episode mix.
- **Frozen parameters.** The detector keeps the parameters fitted on the nominal fault-free year
  and the CP5 thresholds. Off-nominal cells therefore also test a wrong noise model. History-length
  cells are the exception and refit with that history.
- Cells finished under commits ee3c840, 6f9d9e0 and 9de959a (ledger appendix). Between them only the
  worker cap, documents and a crash-only baseline fix changed, not the simulation or detector logic.

## Detectability (nominal cell, primary detector)

> **Superseded by CP10 (post-hoc, 2026-10-07):** the 16% / 32% values are bin edges. The continuous estimate of the share at which P(correct) reaches 0.90 is 0.160 (0.124–0.207) nominal, 0.083 (0.059–0.119) on the held-out grid, and 0.114 (0.080–0.165) on the development grid's test weeks. A signal-to-noise axis is more consistent across conditions. See `docs/RESULTS.md` §1 and ledger CP10-T3.
Binned by |expected silent energy| over the decision window, divided by typical transformer energy
for the same window:

| Silent share of transformer energy | Episodes | Correct cause (95% CI) | Abstained | False outages | Missed outages |
|------|------|------|------|------|------|
| ≤ 1% | 63 | 0.00 (0.00–0.06) | 100% | 0/30 | 0/33 |
| 1–2% | 35 | 0.23 (0.12–0.39) | 77% | 0/17 | 0/18 |
| 2–4% | 81 | 0.40 (0.30–0.50) | 60% | 0/46 | 0/35 |
| 4–8% | 126 | 0.69 (0.61–0.76) | 30% | 0/66 | 1/60 |
| 8–16% | 82 | 0.72 (0.61–0.81) | 26% | 0/49 | 2/33 |
| 16–32% | 70 | 0.94 (0.86–0.98) | 6% | 0/36 | 0/34 |
| > 32% | 44 | 1.00 (0.92–1.00) | 0% | 0/20 | 0/24 |

- **Smallest reliably decided silent load**: about 16% of the transformer's energy. Above it, the
  correct-cause rate is ≥ 0.94 with no false outages. Below about 1% the detector always defers to
  a human. Across all bins the false-outage rate is 0 of 264 comms episodes.
- **Baselines on the same episodes**: the naive share detector decides more often but is wrong in
  up to 26% of episodes per bin (0–26%). The step and count rules are wrong in 16–61% (figure, middle panel).
- 3 of 504 episodes were not detected as a group (small comms failures). 53 involved net-exporting
  PV customers (negative expected energy). The balance works on the magnitude: 21 were decided
  correctly, 31 abstained and 1 outage was missed.

## Robustness (primary detector, frozen thresholds)

| Cell | Accuracy when decided | Abstention | Missed outage | False outage |
|------|------|------|------|------|
| nominal | 0.990 | 0.401 | 0.013 | 0.000 |
| diversity d = 0 / 0.25 / 1.0 | 0.979 / 0.991 / 0.983 | 0.337 / 0.363 / 0.516 | 0.025 / 0.013 / 0.017 | 0.004 / 0 / 0 |
| history 7 / 28 days (refit) | 0.989 / 0.993 | 0.429 / 0.369 | 0.013 / 0.038 | 0 / 0 |
| meter noise × 0 / × 3 / × 10 | 0.990 / 0.990 / 0.969 | 0.397 / 0.391 / 0.411 | 0.013 / 0.013 / 0.038 | 0 / 0 / 0 |
| transformer gain error sd 0 / 1% / 2% | 0.990 / 0.983 / 0.943 | 0.391 / 0.413 / 0.433 | 0.013 / 0.021 / 0.046 | 0 / 0 / 0.019 |
| constant unmetered 2 / 5 / 10 kW | 0.990 / 0.990 / 0.990 | 0.40 | 0.013 | 0 |
| load-shaped unmetered 2 / 5 / 10 kW | 0.949 / 0.857 / 0.743 | 0.444 / 0.466 / 0.462 | 0.038 / 0.122 / 0.241 | 0.019 / 0.034 / 0.045 |
| PV × 0 / × 2 / × 3 | 0.994 / 0.991 / 0.984 | 0.294 / 0.367 / 0.361 | 0.008 / 0.013 / 0.021 | 0 / 0 / 0 |
| concentrators not aligned with zones | 0.990 | 0.395 | 0.013 | 0.003 |

Mean neighbourhood load is about 44 kW, so 10 kW of unmetered energy is about 23% of it.

- **Not sensitive to**: meter noise up to 3×, constant unmetered energy, history length, PV share,
  concentrator layout. The recent-gap baseline absorbs anything constant.
- **Main weakness: unmetered energy that follows the load shape.** It changes within the decision
  window, so after an outage it looks like silent customers still drawing power. At 5 kW, 12% of
  outages are missed, and at 10 kW 24%. Any real deployment with time-varying non-technical losses
  would need the gap modelled as a function of load. Not done in Phase 1.
- **Transformer-meter accuracy matters** (prior P7): a gain error with sd 2% raises missed outages
  to 4.6% and false outages to 1.9%.
- **Diversity** (the uncalibrated assumption A-DIV) moves abstention from 34% to 52%. Accuracy when
  decided stays at 0.98–0.99.

## Hard negatives

| Cell | Accuracy when decided | Abstention | Missed outage | False outage | Naive baseline: false / missed |
|------|------|------|------|------|------|
| concentrator failure identical to a zone | 0.991 | 0.319 | 0.013 | 0.003 | 0.121 / 0.089 |
| outages at night (01:00–05:00) | 0.992 | 0.278 | 0.021 | 0.004 | 0.034 / 0.025 |
| midday, PV × 2 (10:00–15:00) | 0.989 | 0.472 | 0.013 | 0.000 | 0.247 / 0.156 |
| comms failure during a real load change (× 0.3–2.5) | 0.977 | 0.381 | 0.000 | 0.021 | 0.212 / 0.061 |
| outage and comms failure at once, disjoint zones | 0.888 | 0.239 | **0.373** | 0.016 | 0.110 / 0.418 |
| 10% random packet loss | 0.979 | 0.510 | 0.135 | 0.000 | 0.157 / 0.367 |

- **Simultaneous events fail**, as predicted (`docs/LIMITATIONS.md` item 10). Silent meters are
  grouped by common onset, so the two sets merge. The comms half's energy is still visible, and the
  merged group looks like a comms failure. Splitting a silent set into electrical zones and testing
  the combinations is the upgrade path. Not done in Phase 1.
- **10% packet loss** breaks up silent groups: 58 of 504 episodes were not detected as a group,
  and half of the rest are abstained. The detector still issues no false outages, and its
  fault-free false alarms stay at 0.001 per meter-day, against 0.083 for the naive baseline.
- **Night outages are easier than expected.** Night consumption is steadier, so expected-load error
  is smaller relative to the signal.
- **Midday PV is the hardest regular case**: abstention 47%, because PV cancels consumption and the
  expected silent energy shrinks.
