# Method

This page describes the frozen detector as the proposal describes it (Sections 1.3 and 4). The
method has not changed since it was frozen. Everything below runs on SIMULATED data.

## The idea

A meter on the low-voltage side of the transformer measures what the whole neighbourhood draws. It
still sees the energy of customers whose data stopped. It no longer sees the energy of customers
who lost power. For each 15-minute interval:

    gap(t) = E_transformer(t) − Σ E_reporting meters(t)

If the silent customers still draw power, the gap grows by about their expected energy. If they
lost power, it does not. The hypothesis (H-core) is that this difference is large enough, relative
to the uncertainty, to decide between the two. Phase 1 tests it in simulation and measures where
it stops working.

## What happens when a group of meters goes silent

1. **Group.** Meters that go silent in the same interval form one silent group.
2. **Expected consumption.** For each silent meter, the system forecasts what the customer would
   have used: the mean of the same 15-minute slot over the previous 14 days, corrected by how far
   the group was from that history just before it went silent. How long the correction lasts, and
   how wide the prediction interval is, are learned from fault-free data.
3. **Normal gap.** The usual gap between the transformer and the reporting meters (line losses,
   unmetered load), its spread and its correlation over time are learned from fault-free history.
4. **Two explanations.** Energy is conserved at the transformer. If the customers still have
   power, the transformer still delivers their expected energy; if not, it does not. Both
   explanations are scored with heavy-tailed (Student-t) likelihoods, which gives a probability
   for each cause. Evidence accumulates interval by interval after the silence starts.
5. **Decide or abstain.** The verdict is OUTAGE or COMMUNICATION FAILURE only when the probability
   is decisive. Otherwise it is UNCERTAIN and goes to a person. The abstention band was chosen on
   development validation data as the setting that abstains least while keeping missed outages at
   or below 5%, false outages at or below 5%, and fault-free false outages at or below 0.001 per
   meter-day (DESIGN CHOICE).
6. **Explain and log.** Each verdict comes with the numbers behind it in kWh (transformer energy,
   reporting meters, expected energy of the silent meters) and a log entry.

These steps make up the four components of the proposal: a **learned consumption model** (step 2),
a **learned noise model** (step 3), **probabilistic reasoning with a physical constraint** (step 4)
and **selective prediction** (step 5).

## What the detector may read

Only what an operator would have: the `observed/` readings with their arrival times and the
`context/` files (which meters share a line section or a data concentrator, installed PV). It never
reads the simulator's `truth/` or `labels/`; a test enforces this (`tests/test_no_leak.py`). The
layout is in [docs/data_contract.md](data_contract.md).

On a new network, only the fault-free quantities in steps 2 and 3 are refitted on that network's
own fault-free weeks. The abstention band and all other settings stay as frozen.

## Names in code and result files

The primary detector is **the likelihood-ratio test with abstention**. In code and result files
it is called `bayes` (`shahid/detect.py`); development records also call it `lr_band`, which is
the same method. The four simple baselines are the naive share, step, count and structure
baselines (`shahid/baselines.py`; `naive`, `step`, `count`, `structure` in result files). The
Isolation Forest is in `shahid/iforest.py`.

## Why not a trained classifier

The proposal (Section 4.2) gives the reasons: no real labels, transfer between networks,
explainability, and data shape. A supervised comparison on the same simulated events was run after
the method was frozen; it is reported in
[docs/studies/classifier_comparison/README.md](studies/classifier_comparison/README.md) and does
not change the method.

## Where the details are

- Evaluation rules: [docs/eval_protocol.md](eval_protocol.md).
- Simulated faults: [docs/anomaly_generation.md](anomaly_generation.md).
- Data layout: [docs/data_contract.md](data_contract.md).
- Assumptions: [docs/ASSUMPTIONS.md](ASSUMPTIONS.md). Limitations: [docs/LIMITATIONS.md](LIMITATIONS.md).
