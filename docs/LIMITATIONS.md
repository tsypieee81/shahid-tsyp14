# Limitations

Read these before any number in this repository.

1. **All data is simulated.** Every reading, outage and communication failure comes from our
   simulator. Nothing comes from a real utility, and there is no STEG or other Tunisian data.
2. **The simulator and the detector were written by the same team.** The detector may exploit
   regularities of our own simulator that real networks do not have. Held-out evaluation on a
   second grid reduces but does not remove this risk.
3. **Energy conservation holds in the simulator by construction.** The power flow conserves
   energy exactly (verified to about 1e-8 MW). Real networks add effects we do not model: phase
   imbalance, meter clock drift, tariff-register semantics, non-technical losses that change over
   time, and transformer-meter outages.
4. **The load and PV profiles are German benchmark data** (SimBench, 2016, 15-minute). They do
   not represent Tunisian consumption, climate or PV uptake, and we have not reshaped them.
5. **Customer diversity is our own uncalibrated model.** SimBench customers are exact scaled
   copies of a few shapes (`docs/process/findings/01_simbench_reality.md`). We add variation with a knob d whose realistic value is unknown.
   All expected-load errors, and therefore detection rates, depend on it (`docs/RESULTS.md` §0 and §7).
6. **Transformer-level metering in Tunisia is unverified.** The whole method depends on a meter
   on the LV side of the MV/LV transformer. We do not know whether Tunisian substations have one.
   The sensitivity runs (`docs/RESULTS.md` §1, `docs/process/findings/06_detectability.md`) report how results degrade with transformer-meter error.
7. **No hardware, no real-time or deployed operation.** The detector runs offline over simulated
   files, with decision-time semantics emulated from arrival timestamps.
8. **Meter, communication and unmetered-energy parameters are assumptions**, not taken from any
   standard or utility. See `docs/ASSUMPTIONS.md`.
9. **The escalation table (G3) has not been validated with operators.** The knowledge-sharing
   design (G4) is a proposal only.
10. **Silent groups are formed by common onset.** Two simultaneous events in different zones are
    judged as one merged group (measured in the sensitivity runs).
11. **Small silent groups are often undecidable.** When the expected energy of the silent
    customers is small compared with the uncertainty, the balance cannot separate the causes and
    the detector abstains (`docs/RESULTS.md` §1).
12. **Confidently wrong comms verdicts can happen.** In the smoke demo
    (`results/decision_log_demo.jsonl`) a 7-meter outage is called a comms failure with
    probability 0.996. A delayed reading from another meter with unusually high consumption
    inflated the residual. The outage hypothesis's spread (0.13 kWh) is too narrow for such
    heavy-tailed surprises. Under the current escalation table (rule R3) the system would handle
    this alone. On the held-out grid, missed outages were 0.9% (CI 0–2.8%). They are rare, but
    the confidence attached to them is not trustworthy. Upgrade paths, not done: wait for delayed
    readings before deciding, or widen the single-meter uncertainty. Recommended policy change
    (DESIGN CHOICE, not applied to any reported result): require human confirmation for comms
    verdicts on groups of more than a few meters.
13. **Unmetered energy that follows the load shape** (for example non-technical losses) makes
    outages look like comms failures: 12% missed at 5 kW, 24% at 10 kW (sensitivity runs).
14. **Single-meter faults** (gain, bias, noise) are not detectable with the Phase 1 method. The
    stuck-meter rule's perfect score is a simulator artefact and is not reported.
15. **Only one grid is truly held out.** The development grid's test-week result reuses the same
    simulated customers as all development. It is a held-out period and seed result, not held-out
    data (AUDIT.md §4).
16. **Escalation rule R3 (automated handling of confident comms verdicts) is unsafe as written.**
    The demo shows a confident wrong comms verdict, and load-shaped unmetered energy produces
    missed outages without raising abstention (AUDIT.md §10). The team must decide whether to
    require human confirmation before any automated comms handling.
17. **Goal 1 is only partly covered.** Biased, drifting or noisy single meters are not detected
    (`docs/process/findings/08_single_meter.md`). The method diagnoses silent groups, not faulty meters.
18. **Both grids are the same size class**: about 100 customers on a 0.63 MVA transformer. Transfer
    to much larger or smaller LV networks is untested.
19. **One simulated world per grid.** All episodes on a grid share one customer-diversity draw. We
    re-ran the nominal cell on three more world seeds to show the spread (`docs/RESULTS.md` §7).
20. **Operator load from ordinary data loss** (`docs/RESULTS.md` §5): most silent groups are small random-loss
    groups that end as "uncertain" and, under the escalation table, reach a human. `docs/RESULTS.md` §5 gives the
    rate per transformer-day.
21. **The method is statistical inference with parameters fitted from fault-free data** (anchored
    expected load, gap noise, Student-t likelihood ratio with an abstention band). There is no trained
    classifier and no neural network; a gradient-boosting forecaster was tested and brought no benefit
    at nominal diversity (ledger C4-06). "AI" in the competition's wording refers to this automated
    statistical decision only. A supervised comparison run after the method was frozen is in
    `docs/studies/classifier_comparison/README.md`; it does not change the method.
**Implementation status of the gate and the re-check.** The meter-count gate and the R3 re-check are evaluated in study code (`shahid/cp12.py`, `shahid/p2eval.py`). Neither is executed by `explain.escalate`. `configs/escalation.yaml` states the R3 re-check only as action text, and the console preview displays it as pending without acting on it. The gate is not in `configs/escalation.yaml`.

22. **The meter-count gate closes some real outages with no verdict and no human**: on
    whole-feeder events, outages of feeders with only 1–3 meters whose power returns within the
    1 h WATCH timeout. Simulated feeders can be that small; whether real ones are is unknown.
23. **The communication re-check is evaluated against simulated failure durations only.** Every
    simulated communication failure lasts 1–4 h, so the re-check's cost and benefit at any timeout
    are properties of that choice and of A-COMMS (meters resend stored readings), not of field data.
24. **False outage verdicts on tiny silent groups are a base-rate effect** (`docs/RESULTS.md` §9): rare
    deep-tail residuals at roughly the rate the model allows, multiplied by thousands of random-loss
    groups a year, decided under a 50/50 prior. The resolution limit (`docs/RESULTS.md` §1) does not cover them.
25. **The number checker is a weak guard for two-decimal rates** (ledger CHK-01). Under its rounding
    tolerance every random two-decimal number between 0 and 1 matches some ledger value, and about a
    third of random three-decimal numbers do. The real protection is that the result documents are
    generated from result files; the checker catches most errors of three or more digits and cannot
    catch a wrong two-decimal rate in a hand-written document.
26. **The operator console is a preview on replayed simulation output** (decisions 0006 and 0007).
    It replays stored simulated days, not live data. Its track record and its evaluation view derive
    from simulated labels standing in for field confirmations. No operator has used it.
27. **A powered meter merged into an outage group can make a confident wrong verdict; net export at
    midday makes this easier** (`docs/process/findings/09_net_export.md`, ledger EXP-01 to EXP-03).
    In the `feeder_outage` replay at 10:00, a meter on an energised feeder went silent at the same
    onset and was merged into the outage group. Its consumption formed the whole residual, and the
    outage was called a comms failure with posterior 0.9992. The group was a net exporter, so the
    comms hypothesis was wide and on the other side of zero. A negative gap at midday on its own is
    expected physics, not an error (showcase day). Candidate remedies are untested.
28. **Known issue: a pandas FutureWarning in `shahid/demo_day.py`.** The voltage pivot
    (`pivot_table` on a categorical meter id) warns that the default of `observed` will change. The
    committed replays are not affected (the table is reindexed to every meter); a future pandas may
    change the behaviour. It was left alone so that the committed results keep their code.
