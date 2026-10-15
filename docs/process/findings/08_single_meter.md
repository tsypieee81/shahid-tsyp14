# CP8 — Single-meter faults (time-boxed)

Source: `results/cp8_single_meter.json` (`python -m shahid.cp8_single_meter`, commit 7604730, config
hash 7bddf3c73074). Ledger C8-01 to C8-03. Development grid, fault-free year (d = 0.5). One meter's
readings are corrupted for 7 days, 150 episodes per fault setting, starts in weeks 0–2. Thresholds
come from fault-free weeks at a 1% false-alarm target. Measured false-alarm rates: stuck rule 0,
own-history 0.009, balance 0.028 (the balance threshold rests on only 36 fault-free weeks).

| Fault | Stuck rule (≥ 8 identical readings) | Own-history daily ratio | Energy-balance gap shift |
|-------|------|------|------|
| stuck at last value | 1.00 | 0.00 | 0.23 |
| gain × 0.5 | 0.00 | 0.01 | 0.20 |
| gain × 0.8 / × 0.9 | 0.00 | 0.01 / 0.00 | 0.07 / 0.06 |
| gain × 1.1 / × 1.2 / × 1.5 | 0.00 | 0.01 / 0.01 / 0.02 | 0.01 / 0.04 / 0.10 |
| bias −0.05 / −0.02 kWh per interval | 0.00 | 0.57 / 0.19 | 0.15 / 0.06 |
| bias +0.02 / +0.05 kWh per interval | 0.00 | 0.01 / 0.05 | 0.00 / 0.00 |
| added noise sd 0.02 / 0.05 / 0.2 kWh | 0.00 | 0.01 / 0.01 / 0.13 | 0.03 / 0.03 / 0.04 |

## Findings
- **Gain errors, small biases and added noise on one meter are not detectable with the Phase 1
  method.** At most 20% are detected (gain × 0.5, balance) at a 1–3% false-alarm rate.
- **Why:** each customer's daily energy varies a great deal (diversity model, d = 0.5). The
  own-history thresholds needed for 1% false alarms are 0.011× to 4.0× the customer's usual daily
  energy, which hides gain errors. One meter's error is also small against the day-to-day spread of
  the transformer gap. The balance can say that some meter is wrong, not which one.
- **Stuck meters are caught every time with no false alarms, but this is a simulator artefact.**
  The meter model adds noise to every reading, so long runs of identical values never happen
  naturally. A real meter on an empty home reporting zeros would produce them. The false-alarm rate
  of this rule in the field is unknown.
- **Upgrade path, not done:** a per-meter balance requires sub-metering points (feeder heads) or
  regressing the transformer gap on each meter's readings over weeks. Neither was attempted.


**Superseded (submission packaging, 2026-10-12):** the stuck-meter result is withdrawn as a simulator artefact and is not reported; it is on the "Do NOT report" list in [docs/RESULTS.md](../../RESULTS.md).