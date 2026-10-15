# Preliminary design for each challenge goal (from the team's proposal)

**Status: PROPOSED, not implemented. The hardware demonstrator (5.5) is also not built.**

**Status update (2026-10-14).** Since the proposal, the operator interface of 5.3 is IMPLEMENTED as a preview (`ui/`, Streamlit) that replays simulated days; no operator has used it. The quoted text below is unchanged. **Implementation status of the gate and the re-check.** The meter-count gate and the R3 re-check are evaluated in study code (`shahid/cp12.py`, `shahid/p2eval.py`). Neither is executed by `explain.escalate`. `configs/escalation.yaml` states the R3 re-check only as action text, and the console preview displays it as pending without acting on it. The gate is not in `configs/escalation.yaml`.

This page reproduces word for word Section 4.2 and Section 5 (5.1 to 5.5) of the team's proposal
draft `SHAHID_Phase1_proposal_v7_DRAFT.docx`, which supersedes earlier drafts. Nothing is added. Section 5.4 is the single G4 (shared learning) design of this repository.

- Statements about Phase 1 measurements are quoted as the proposal writes them. Their numbers are in
  `docs/CLAIMS_LEDGER.md` (C4-06, C7-02, C7-05, CP10-T0, CP12-T5) and `results/cp7_heldout.json`.
- Bracketed placeholders in the proposal are not designs. Each is shown as **pending, to be
  supplied by the team** and listed at the end.
- Section numbers (for example "Section 6.6" or "Section 11") refer to the proposal, not to this
  repository.

## 4.2 Why not a trained classifier or a neural network (stated rationale, not a design)

A supervised classifier could learn the same decision from labelled examples. We chose not to make
one the primary method, for reasons that are partly measured and partly expectations.

- **Labels.** No labelled examples of outages and communication failures are available to us for
  Tunisian networks. A classifier trained on our simulator's labels would learn our simulator. Our
  models learn only from fault-free history, which a utility accumulates in normal operation. Real
  outage records from field crews could provide labels in future; we have none.
- **Transfer between networks.** With thresholds chosen on one network and left unchanged, our method
  kept its false-outage rate at 0.00 on two networks it had never seen (Section 6.1). Whether a
  classifier trained on one network transfers is untested.
- **Explainability.** The brief favours interpretable approaches. Every number our system reports is
  a physical quantity in kWh that an operator can check against the transformer reading.
- **Data shape.** Each event is described by about eight numbers, and each network yields a few
  thousand events. On data of this size we expect a neural network to bring little; this is an
  expectation, not a measurement.
- **What we did test.** A gradient-boosting forecaster for the expected consumption differed from the
  simple model by less than 0.01 kWh per interval at nominal customer diversity, with the sign
  changing between group types, so it is not used (Section 6.7). An Isolation Forest detects that
  something happened but cannot attribute the cause (Section 6.2).

**Resolved since this draft (13 October 2026):**
- the supervised comparison was run as a post-hoc study: `docs/studies/classifier_comparison/README.md`,
  ledger CLF-01 to CLF-12;
- Figure 1, "One simulated day on the held-out grid: transformer energy, sum of reporting meters, and
  verdicts against truth", exists as `results/figs/pack_5_example_day.png`.

## 5. Preliminary design for each challenge goal (PROPOSED for Phase 2)

| Goal | IMPLEMENTED and measured (simulation) | Not done / PROPOSED for Phase 2 |
|---|---|---|
| G1 Detect, and tell a grid event from a data problem | Diagnosis of silent groups as outage, communication failure or uncertain; four simple baselines and an Isolation Forest | Single-meter bias, drift and noise are not detected. Interval voltage is unused |
| G2 Confidence, explanation, decision log | Probability per verdict; template explanation whose every number comes from the verdict record (enforced by a test); hash-chained, append-only decision log | Explanation quality has not been evaluated with people. Mid-range probabilities are not shown to be calibrated |
| G3 What the system may do alone | Escalation table; measured operator load; measured harm of one automatic rule; a post-hoc gate option | Not validated with operators |
| G4 Shared learning across nodes | None | Design only (Section 5.4) |

## 5.1 G1: anomaly detection (PROPOSED for Phase 2, not implemented)

Phase 1 covers one part of G1 in depth: deciding whether a silent group of meters is a genuine grid
event or a data problem. The table takes each item the brief lists under this goal and states where
we stand and what we propose for Phase 2. Nothing in the last column is implemented.

| Item in the brief | Phase 1 status | Phase 2 design (PROPOSED) |
|---|---|---|
| Smart-meter readings | Implemented and measured: interval energy, arrival times, silent groups | Version 2 of the evidence (Section 11) |
| Voltage | Recorded in the dataset, not used | Compare each meter's interval voltage with electrically close meters to flag a sensor that departs from its neighbours. The benchmark holds the upstream voltage fixed, so simulated results would be optimistic |
| Current, power quality | Out of scope | None. 15-minute meter data does not carry waveform quantities, and our simulator cannot produce them credibly (DESIGN CHOICE) |
| Equipment faults, natural equipment failures | Partly: detected as loss of supply to a group of customers (outage verdict). The cause is not diagnosed | The silent group already identifies the affected line section. No diagnosis of cause is planned |
| Degraded sensors | Tested, not detected (Section 6.8) | Per-meter comparison with neighbours over weeks; regression of the transformer gap on individual meters |
| Biased readings | Tested, not detected (Section 6.8) | Same two methods |
| Corrupted readings | Partly: missing and delayed readings are detected and classified. Wrong values are not | Range and consistency rules on values. An earlier stuck-meter result was withdrawn as a simulator artefact |
| Falsified readings | Not addressed | A reading falsified downwards leaves a persistent gap at the transformer; attributing it to a meter needs the regression above. A falsification that keeps the balance closed cannot be seen by any balance test |
| Genuine grid event or data-quality problem | Implemented and measured (Section 6) | Sections 6.9 and 11 |

## 5.2 G2: confidence and explainability (explanation study PROPOSED, not implemented)

Each verdict carries the probability of a communication failure. On the held-out grid the Brier
score is 0.048. Probabilities below 0.1 (80 events) and above 0.9 (124 events) match the observed
frequencies (0.013 and 0.992). The intermediate bins hold 3 to 14 events each and are too small to
judge. We therefore describe the confidence as reliable at the extremes and unverified in between.
One confident wrong verdict is documented in the repository.

Explanations are generated from fixed templates filled from the verdict record, and a test fails if
an explanation contains a number that is not in the record. That enforces faithfulness. Usefulness is
untested. PROPOSED for Phase 2: people outside the team read explanations alone and predict the
verdict and the recommended action; we report how often they agree with the system.

## 5.3 G3: escalation and governance (operator interface and trust devices now IMPLEMENTED as a preview in `ui/`; not used by operators)

The escalation table is a DESIGN CHOICE: an outage verdict needs human approval before a crew is
sent; an uncertain case goes to a human; a confident communication verdict was handled
automatically.

We measured the harm of that last rule. It closed 0.9% to 1.8% of real outages as communication
failures without supervision under nominal conditions, and up to 24.1% under large load-shaped
unmetered energy. The table now marks such verdicts as provisional, with an automatic re-check when
the stored readings arrive and escalation to a human after 8 hours (DESIGN CHOICE). Its cost depends
on how long real communication failures last, which we do not know (Section 6.6).

We also measured operator load and found that the registered configuration sends too many low-value
items to a human (Section 6.6). Both findings come from measuring the policy, not from assuming it
works.

**Operator interface (PROPOSED, not built).**
- The brief requires one for the final phase. Our preliminary design is a single screen with a queue
  of three item types that are never merged: an outage verdict awaiting approval, an uncertain case,
  and a communication verdict not yet confirmed.
- Each item shows the explanation, the expected and the visible energy with their spreads, and the
  alternative cause that was considered.
- The operator can approve, override or defer, with an optional reason, and every action is appended
  to the hash-chained log.

> Figure 2. Proposed operator screen (mock-up, not implemented). **Pending, to be supplied by the
> team.**

**Over-trust and under-trust (PROPOSED).**
- Against over-trust:
  - the alternative cause and the evidence are shown with every verdict;
  - a certainty is never displayed as 1;
  - a random sample of automatically closed cases is sent for audit;
  - approvals given within a few seconds are flagged.
- Against under-trust: each verdict type shows its track record, that is how often past verdicts of
  that kind were confirmed, and overrides are recorded with their eventual outcome.
- Phase 2 would measure the override rate, the share of overrides later shown to be wrong, and
  approval time.
- None of this has been validated with operators.

## 5.4 G4: shared learning (PROPOSED, not implemented)

**Shared between neighbourhoods:**
- fitted noise-model parameters and the measured resolution limit of each site (aggregates only);
- policy settings with their measured trade-offs;
- anonymous failure signatures such as "the gap follows the load";
- operator-confirmed outcomes with their evidence numbers, stripped of meter identifiers.

**Kept local:** every meter reading, customer and meter identifiers, and network topology. We treat
interval consumption as personal data (DESIGN CHOICE).

**Why share:** a new site has no fault-free history. Starting from another site's parameters could
shorten the period before the method is usable. This is a HYPOTHESIS for Phase 2.

**One related measurement exists.** The decision thresholds chosen on the development grid were
applied unchanged to two other grids, and the false-outage rate stayed at 0.00 on both. The noise
parameters are fitted on each grid's own fault-free history, so this is evidence for sharing
thresholds, not parameters.

**Upstream coordinator (design only).** A coordinator that sees several neighbourhoods go silent at
the same moment could merge them into one upstream event instead of many local ones.

## 5.5 Optional hardware demonstrator (PROPOSED, not built)

All Phase 1 evidence is simulated: energy conservation holds in the simulator by construction, and
the meter error and message loss are assumed. If the team reaches the final phase, we propose a small
bench to test the premise on real sensors. It is not required by the brief and comes after the
required items.

**Layout.** A low-voltage DC supply feeds two feeders through relays.
- Each feeder has two small loads standing in for houses, each with its own current-and-voltage
  sensor and a Wi-Fi microcontroller.
- One more sensor on the supply line stands in for the transformer meter.
- All nodes send interval energy to a laptop running the unchanged detector.

**The two events.** Opening a relay cuts power to a feeder, which is a real outage. Switching off a
node's radio leaves it powered, which is a communication failure.

**Hypotheses stated in advance.**
1. On fault-free runs the balance closes within the measured sensor error.
2. The detector separates relay cuts from radio losses.
3. The measured sensor error and message loss are compared with the values assumed in simulation.

**What it cannot show.** Grid scale, alternating-current behaviour, or a neighbourhood of 100
customers. With four loads, every event is far above the resolution limit of Section 6.4.

**Safety.** Low-voltage DC only. Nothing is connected to mains electricity.

**Decision point.** Built only if the operator interface and the version 2 evidence are on schedule
two weeks into Phase 2. **Pending, to be supplied by the team:** parts list with quotes from local
suppliers.

## Placeholders in the proposal (pending, to be supplied by the team)

| Location | Placeholder text in the proposal |
|---|---|
| Section 4.2 | RESOLVED: supervised comparison run as a post-hoc study (`docs/studies/classifier_comparison/README.md`, ledger CLF-01 to CLF-12) |
| Section 4.2 | RESOLVED: figure at `results/figs/pack_5_example_day.png` |
| Section 5.3 | RESOLVED: replaced by the operator console preview `ui/` (decisions 0006 and 0007) |
| Section 5.5 | **STILL PENDING (team):** parts list with quotes from local suppliers, supplier and date; until then the proposal keeps its honest sentence that no prices are given |
