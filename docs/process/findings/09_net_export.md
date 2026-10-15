# Finding 09 — Net-exporting silent groups and the 10:00 confident-wrong verdict (post-hoc, SIMULATED)

Source: `results/diagnostics/export_groups.json` (`python -m shahid.diag_export`, commit fdeb289,
config hashes ed4c402d67d5 and d4233c3d3d4c) and `results/demo/showcase.json`. Ledger EXP-01 to EXP-03.
Post-hoc diagnostic of two demo replays. The diagnostic reads simulation truth on the evaluation side
only; the detector and the operator views never do. No protocol was registered: this explains two
observed results and does not estimate a rate.

## Question

At midday, rooftop PV makes some silent groups net exporters, so their expected energy M is negative.
Two replays involve such groups:
- the confidently wrong communication-failure verdict on `feeder_outage` at 10:00 (posterior 0.9992);
- the negative gap on the `showcase` day while 20 meters are silent.

Does the negative expected energy of a net-exporting group explain them?

## Evidence

| | feeder_outage 10:00 (EXP-01) | showcase 09:45 (EXP-02, EXP-03) |
|---|---|---|
| silent group | 38 meters: the outaged feeder plus m093, a powered meter on another feeder | 20 meters behind a failed concentrator |
| expected energy M (comms hypothesis) | −2.10 kWh | −3.73 kWh |
| visible residual R at the transformer | 3.39 kWh | −3.51 kWh |
| spreads sd_O / sd_C | 0.165 / 2.81 kWh | — / 1.66 kWh |
| standardised R under outage / under comms | 20.56 / 1.95 | — |
| verdict, posterior P(comms) | COMMS_FAILURE 0.9992 (**wrong**: outage) | COMMS_FAILURE 1.0 (correct) |
| simulated true energy of the silent group | 3.344 kWh, all of it from m093 | −3.454 kWh (net export) |
| gap in the 10:15 interval | — | −1.60 kWh |

## Findings

1. **The 10:00 error is not caused by net export. It is caused by a powered meter merged into the
   outage group.**
   - m093 is on a feeder that stayed energised. Its readings went missing at the same onset, so the
     silence rule merged it into the outage group.
   - Its consumption in the window (3.344 kWh) is the whole residual R (3.39 kWh). Under the outage
     hypothesis R should be near zero with a spread of 0.165 kWh. It sits 20.56 spreads away, so the
     outage hypothesis is rejected. Under the comms hypothesis it sits 1.95 spreads from M.
   - This is the same family as LIMITATIONS item 12 (a powered meter's energy counted on the wrong
     side of the balance), now with a measured decomposition.
2. **Net export makes such errors easier, not inevitable.**
   - Because the group's expected energy is negative (−2.10 kWh), the comms hypothesis predicts a value
     on the other side of zero from the observed R. Its spread (2.81 kWh) is also wide, because it
     scales with the variability of the PV-dominated group.
   - A wide comms spread lets a positive residual remain "plausible" under comms while the narrow
     outage spread rules the outage out.
3. **The negative gap on the showcase day is correct physics, not an error.**
   - The 20 silent meters export at midday (true −3.454 kWh). The transformer therefore shows less than
     the sum of the reporting meters, and the gap is negative (−1.60 kWh in the 10:15 interval).
   - The detector expects a negative value (M −3.73 kWh), sees one (R −3.51 kWh), and decides correctly
     with posterior 1.0. The method handles negative expected energy; only an operator reading the gap
     card needs to know that a negative gap at midday is expected.

## Consequences

- The Phase 1 numbers do not change. The confident-wrong mechanism is already a known limitation
  (item 12); this finding adds a measured second instance and shows that net export alone does not cause it.
- **Status after Phase 2:** the split by feeder was tested and removed every confident wrong verdict of
  this kind on two unseen grids (findings 11 and 16); evidence version 2 does not fix it, as registered
  (finding 12).
- **Candidate remedies as listed at the time of this finding** (Phase 2 plan, Table XVII):
  - split a silent set by line section, so a meter on an energised feeder is not merged into an
    outage group (priority 5);
  - wait for delayed readings before deciding, as part of the version 2 evidence accounting
    (priority 2);
  - use the voltage reported by electrically close meters to tell an energised section from a dead
    one (priority 3). This addresses which section is dead, not the merge itself. On the benchmark
    grid the upstream voltage is fixed, so voltage evidence will look better in simulation than in
    the field.
- **Console:** the grid-health card should say that a negative gap at midday is expected when
  net-exporting meters are silent.
