# Version 2 candidates (from cadence-v1 findings). NOT implemented.

Nothing here is implemented, tuned or tested. **A version 2 protocol must be committed on its own,
in a commit containing only the protocol, before any version 2 code is run on any data.** Version 1
and its results stay frozen. The confirmatory grids (`1-LV-rural2--0-sw`, `1-LV-semiurb4--0-sw`)
stay untouched until then.

| # | Candidate | Motivating finding | Open questions |
|---|---|---|---|
| 1 | **Treat the arrival of the silent group's own stored readings as direct evidence of a communication failure.** At minimum, exclude those readings from the "reported" sum while their energy is still counted in `M` | CAD-10, CAD-L1: late own readings flip comms failures to OUTAGE (26 of 39 at 60 min); this accounts for all 26 false outages at 60 min | How should a verdict already issued be revised? Does a delayed or partial backlog differ from a full one? Under assumption A-COMMS (meters store and resend) this is strong evidence; without store-and-forward it does not exist |
| 2 | **Handle the onset interval in the balance**, for example by excluding it, modelling the partial interval, or starting the window at the first fully silent interval | CAD-11, CAD-L2: late-onset outages are called comms failure (32 of 191 at 60 min with a 45-min offset) | What does it cost in delay? Does the same treatment apply to the restoration interval? |
| 3 | **Simulate sub-interval onsets** (event starts not aligned to reading boundaries, at any resolution including 15 min) | CAD-L2: all simulated starts are aligned; the version 1 missed-outage rate may be optimistic | This needs truth below 15 min, or a partial-interval model on the 15-min truth. It changes the simulator, so it needs its own protocol |
| 4 | **Express rules in time, not readings:** silence duration, decision window, delay and backlog in minutes; minimum expected energy per hour; the gap baseline over a fixed time | CAD-7, CAD-12 and the limitations list: K, L_max and the delay and backlog parameters scale with the interval, and absolute-kWh thresholds are compared with window sums | Re-select thresholds on development data only, at each interval or with a single interval-free rule? |

Each candidate needs, before implementation:
- a pre-registered hypothesis and success criterion;
- development and validation separation;
- an untouched evaluation set.

The candidates interact (1 and 2 both change the residual), so they should be tested in a
pre-specified factorial or in a pre-specified order, not chosen after inspecting test outcomes.
