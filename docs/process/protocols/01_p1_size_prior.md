# Protocol 01 — Priority 1: group-size-dependent prior, learned combination, escalating gate

Registered 2026-10-14, before any code for it exists. Frame: protocol 00. Plan reference: proposal
Table XVII priority 1; Phase 2 candidates 2, 8 and 9 (`docs/process/phase2_candidates.md`).

## Question and motivation
Fault-free false outage verdicts occur on 1–3-meter silent sets at about the model's own tail rate,
multiplied by many tiny groups under a 50/50 prior (CP12 Task 3, LIMITATIONS 24). Does a prior that
depends on group size, or a learned combination of the balance evidence with group size, cut those
false verdicts and the operator load without breaking the safety limits?

## Candidates (module `shahid/p1_prior.py`; version 1 untouched)
Both reuse version 1's evidence (`detect.evidence_table`, frozen nuisance parameters) and its log
likelihood ratio llr at each lead; only the step from llr to a posterior changes.
- **P1a, size prior**: posterior = sigmoid(llr + logit π(n)), where π(n) = P(comms | size bin) with
  bins 1, 2, 3–5, 6–20, > 20 meters, estimated on development training weeks (seeds 101–103 event
  runs and the fault-free year; truth of every detected group from the simulation labels; Laplace
  smoothing +1/+1). ASSUMPTION: these frequencies are the simulator's (1% random loss, about one
  event per day, 40% outages); a utility would estimate them from its own records.
- **P1b, learned combination**: logistic regression of the true cause on [llr, log n, llr·log n],
  fitted on the same training rows (one row per group and lead), L2 penalty C = 1.
- Decision as in version 1: sequential over leads 0–4, abstention band b around the posterior
  (verdict COMMS if posterior ≥ 1 − b, OUTAGE if ≤ b).

## Selection (development validation only)
For P1a and P1b, b ∈ {0.005, 0.01, 0.02, 0.03, 0.05, 0.1, 0.2}, chosen by rule v3 on validation weeks.
The frozen P1 is the feasible one of P1a/P1b with less abstention (tie: P1a, the simpler). Its
parameters are written to `results/p1/p1_params.json` and committed before protocol 05 runs.

## Escalating gate (policy layer)
Meter-count gate of CP12 (groups of fewer than 3 meters wait 1 h in WATCH), with one change: a group
whose meters resume without the onset reading is **escalated to a human as uncertain**, not closed.
It is evaluated with the CP12 policy machinery for v1 and for P1 (rows "v1+gate-close",
"v1+gate-escalate", "P1", "P1+gate-escalate"). Its parameters are not re-chosen.

## Endpoints (confirmatory, protocol 05, rural2 primary)
- **H1a (primary)**: fault-free false outage verdicts per transformer-year, P1 below v1. Supported
  if the upper 95% bound of the Poisson rate ratio P1/v1 is below 1.
- **H1b (safety)**: P1's missed-outage and false-outage rates on test-week episodes ≤ 0.05 (point
  estimates; Wilson intervals reported).
- **H1c (load, secondary)**: uncertain human items per transformer-day on the fault-free year at 1%
  loss, P1 vs v1, with bootstrap interval over days.
- **H1d (gate)**: whole-feeder outages closed with no verdict: 0 under gate-escalate by
  construction; reported cost: extra human items per transformer-day against gate-close.

## Compute ESTIMATE
Development evidence tables for every lead are cached once and shared with protocols 03 and 04
(about 1 h, comparable to `cp5_compare`); fitting and selection minutes. Total ≈ 1.5 h.
