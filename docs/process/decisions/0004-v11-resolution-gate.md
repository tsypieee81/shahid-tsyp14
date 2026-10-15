# 0004 — Version 1.1 resolution gate (DESIGN CHOICE, post-hoc variant)

**Context.** CP10 showed about 11 human items per transformer-day and 32–40 false outage verdicts per
transformer-year, all from silent sets of 1–3 meters, below the method's resolution limit.

**Options.** Gate on signal-to-noise, expected silent energy (kWh) or meter count, with timeouts of
1–8 h (`docs/eval_protocol.md` addendum B). Sweep: `results/cp11_select.json`.

**Evidence (development data only).**
- Gating on SNR or kWh hardly reduces false outage verdicts: the false verdicts sit on 1–2-meter
  groups with high apparent SNR. Gating on meter count removes them.
- Under addendum B's rule no setting is feasible, because version 1 itself leaves 11.9% of
  validation branch and feeder outages without real-time attention (short outages end before any
  decision).
- Under addendum C's declared incremental reading, exactly one setting is feasible: **gate groups of
  fewer than 3 meters, timeout 1 hour**. Human items per transformer-day 9.88 → 0.022, false outage
  verdicts per transformer-year 27.8 → 0, branch and feeder outages without real-time attention
  11.9% → 12.9%, single-connection outages without real-time attention 36% → 73% (11 episodes).

**Choice.** Version 1.1 = version 1 + gate (n < 3 → WATCH) + 1-hour timeout + provisional comms
re-check (revised R3). The registered result remains version 1 (addendum B outcome).

**Consequence.** Single and two-meter silences no longer reach a human unless they persist for an
hour. A single-connection outage shorter than about an hour is never seen in real time. This relies
on meters re-sending stored readings after a comms failure (A-COMMS).
