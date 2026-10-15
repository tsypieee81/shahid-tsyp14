# Operator console (preview)

The operator screen proposed in Section V-C of the paper (decisions 0006 and 0007 in
`docs/process/decisions/`). It replays **SIMULATED** days from stored simulations. It is not deployed,
not real-time, and no operator has used or validated it.

```bash
pip install streamlit==1.65.0          # Altair comes with it
python -m shahid.demo_day              # replays the scenarios (already committed in results/demo)
python -m shahid.demo_eval             # simulation outcomes for the evaluation and trust views
streamlit run ui/app.py                # from the repository root (ui/dashboard.py also works)
```

## Design

Control-room style after ISA-101 high-performance HMI practice. Surfaces are grey; colour marks only the
verdict classes (outage red, uncertain amber, communication failure blue) and a verified chain (green).
Every number on screen goes through the `fmt_*` formatters in `ui/theme.py` (checked by a test), and
probabilities read ">0.999" or "<0.001" at the ends. Values come from `results/demo/*.json` and
`ui/operator_log.jsonl` at render time.

## Scenarios (`configs/demo_scenarios.yaml`)

One simulated June day on the development grid, frozen detector, 15 days of simulated history. Each
scenario opens at its own replay time (`default_cursor`).

| Scenario | Injected event | What the replay shows |
|---|---|---|
| `showcase` | constructed day (A-UI-SHOWCASE): five events, so every queue has items | largest-feeder outage decided; concentrator failure decided as a communication failure; midday outage of an eight-meter feeder abstained; two-meter data loss decided; one-meter data loss abstained |
| `calm` | none; ordinary random data loss | tiny silent groups, mostly abstained and sent to a person |
| `feeder_outage` | outage of the largest feeder at 10:00 | a confident wrong verdict: a delayed large consumer joined the outage group (LIMITATIONS item 12) |
| `feeder_outage_morning` | the same outage at 06:00 | decided correctly; added after the 10:00 replay, as its description says |
| `concentrator_comms` | a data concentrator fails at 14:00 | decided correctly and handled automatically; the re-check is displayed only (no code runs it) |
| `both_at_once` | outage and communication failure at once | the merged group called a communication failure: the documented missed outage |
| `midday_pv` | doubled PV; outage at 13:00, communication failure at 15:00 | both abstained; a one-meter data loss called an outage (base-rate effect) |
| `small_group` | outage of a two-meter line at 09:00 | decided correctly here |

The showcase day exercises every part of the screen. It is not a typical day, and its verdicts are not
results.

## Views

- Top bar: grid and detector chips, scenario, replay window, speed and clock, the amber `LINK: SIMULATED REPLAY` chip,
  chain state, jump-search (meter id such as `m042`, group number or `hh:mm`) and the presentation
  toggle. "SIMULATED DATA — Phase 1/2 prototype, not a deployed system." stays visible.
- Icon rail: Situation, Queues, Network, Trace, Audit, Trust, and Evaluation (only with its toggle).
- Situation, the landing view:
  - six KPI tiles: queue counts, abstention share, median decision latency with its IQR, and meters
    reporting. Deltas compare with one hour earlier (A-UI-DELTA);
  - the grid balance: transformer, reporting meters, and a dotted "if only data were lost" line (reporting
    plus the group's expected energy), with the gap shaded;
  - a rail with the abstention gauge, the verdict matrix, open-item confidence (evidence strength, not
    validated accuracy) and a tick bar of today's decisions;
  - the event feed, newest first, and the selected item's evidence card or a grid-health card.
- Evidence card: expected against visible energy with their spreads, the probability on its band, the
  explanation from `shahid.explain`, the rule, and the resolution-limit warning. The actions Approve,
  Override (with a reason), Defer and Escalate each enter the hash-chained operator log with the time
  taken.
- Queues: outages awaiting approval, uncertain cases and unconfirmed communication failures, never
  merged, plus the random audit sample. A selected row shows its balance chart.
- Network: the SimBench LV network at real bus coordinates. Meters are sized by previous-day energy and
  coloured by state; rooftop PV is ringed; the selected group glows. The tooltip shows meter, feeder, PV,
  lag and last voltage.
- Trace: the balance chart full size, with a group selector.
- Audit: chain state, the operator log, verification and a tamper test on a copy.
- Trust: track record per verdict class, overrides, approval times with fast approvals flagged, and the
  audit sample. Simulated outcomes stand in for field confirmations (decision 0007).
- Simulation evaluation: verdicts against simulation labels, behind its own toggle and outside the
  operator path.

## Sidebar

- Scenario, with what the day demonstrates.
- Replay: time as HH:MM; Step, Next event, and Play at 0.5–4 s per interval. Scenario and replay time stay
  in the URL, for example `?scenario=feeder_outage_morning&cursor=06:30`.
- Session: operator name; Reset session clears `ui/operator_log.jsonl` (not tracked).
- Evaluation toggle (decision 0007) and About.
- Export shift report: the replayed day, open queues, operator actions and chain head hash, in Markdown.

Presentation mode (top bar) is a recording aid: it enlarges type and disables the evaluation toggle.
