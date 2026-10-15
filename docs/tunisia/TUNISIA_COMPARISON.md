# Tunisia study: comparison with the frozen baseline, claims, Phase 2 plan, verdict

Branch `tunisia-study`. Protocol: `docs/eval_protocol.md` addendum E (committed 37dfb6a before any
number). Results: `results/tunisia/tn_eval.json`, `results/tunisia/tn_safe_gate.json`; full tables
in `docs/tunisia/TUNISIA_RESULTS.md` (generated). Frozen baseline: `results/cp7_heldout.json`,
`results/cp11_eval.json`. Ledger: TN-H1 to TN-H4, TN-LOSS, TN-SAFE.

**Everything below is SIMULATED on German SimBench grids, and every scenario value is an
ASSUMPTION.** Nothing here was measured on STEG equipment or data.

## 1. Comparison with the frozen baseline

The detector is the frozen version 1 throughout. Nothing was tuned. New observation seeds and all
weeks are used, so the figures are not identical to CP7, which used test weeks only.

| Evaluation | Coverage | False-outage rate | Missed-outage rate | Source |
|---|---|---|---|---|
| CP7 held-out urban6, test weeks (frozen result) | 0.723 | 0.000 | 0.009 | `results/cp7_heldout.json` |
| Tunisia study, held-out urban6, nominal, new seeds | 0.672 | 0.000 | 0.000 | TN-H1 |
| CP11 untouched rural3, test weeks (frozen result) | 0.494 | 0.000 | 0.000 | `results/cp11_eval.json` |
| Tunisia study, held-out rural3, nominal, new seeds | 0.503 | 0.000 | 0.007 | `results/tunisia/tn_eval.json` |

The nominal behaviour reproduces on new seeds.

**Transfer by cell** (addendum E rule; validation semiurb5 / held-out urban6 / held-out rural3):

| Cell (ASSUMPTION) | Outcome | Reading |
|---|---|---|
| nominal, pv0, pv2, constant 2 kW unmetered | transfers on all three | PV level and a constant unmetered load do not break the balance |
| comms failures 1–24 h | transfers on two, inconclusive on one | longer failures are tolerated |
| 5% random loss | transfers on urban6 only | missed outages rise |
| 10% random loss | fails on all three (missed 0.177 rural3, 0.097 urban6) | silent groups merge with random-loss meters (TN-LOSS: 47 of 48 missed outages on rural3 have a merged group at the same onset) |
| load-shaped 5 kW unmetered | fails on all three (urban6 false outage 0.059, missed 0.128) | the known constant-gap failure (CP10 Task 8), confirmed on new grids |

Across all families, version 1 transfers in 15 of 24 (TN-H4). On identical events and inputs, the
simple baselines keep the profile seen in CP7: high coverage, many wrong verdicts
(`TUNISIA_RESULTS.md` §2).

## 2. Deployment modes (the decisive Tunisian unknowns)

| Mode | Result | Ledger |
|---|---|---|
| B: transformer data 1 h or 1 day late | verdicts identical; median delay 0.50 h → 1.50 h and 24.50 h | TN-H1 |
| C: no transformer measurement | all energy-balance methods answer UNSUPPORTED (0.997 of episodes; the rest are undetected). The meter-only count baseline still answers, but calls 0.609 of comms failures outages | TN-H2 |
| D: 4-hourly batches | coverage 0.588, outage recall 0.713, false outage 0.024, median delay 2.50 h (held-out urban6) | TN-H3 |
| D: daily batches | outages still found, but retrospectively: median delay 10.25 h, coverage 0.332. Comms failures shorter than the batch never become visible (comms recall 0.081); this is harmless, but it is not real-time diagnosis | TN-H3 |

**Safe abstention** (post-hoc variant). Escalating, instead of closing, groups whose meters resume
without the onset reading does stop silent closures: 17 → 0 of 350 held-out whole-feeder outages.
But it multiplies fault-free human items: 0.03 → 4.90 per transformer-day at 1% loss, 15.5 → 64.3
at 10% (TN-SAFE). A brief outage of a small group and a lost reading look the same, so no policy
on these data separates them cheaply.

## 3. Claims

**Supported by the evidence (simulation):**
- The energy balance stays informative across the PV levels, constant unmetered load and failure
  durations tested, on three SimBench grids, without retuning (TN-H4).
- A delayed transformer feed costs only time, not accuracy (TN-H1).
- Without a transformer measurement the method cannot diagnose, and the implementation says so
  instead of guessing (TN-H2, test-enforced).
- Batch delivery turns diagnosis into a retrospective check with a delay up to the batch period
  (TN-H3).

**Not supported:**
- That SHAHID works on STEG's network or data; that it is "Tunisian"; that it runs in real time
  in a STEG control room.
- That it handles load-shaped unmetered energy or random data loss of 10% (TN-H4).
- That small-group outages can be caught without large operator load (TN-SAFE).
- Zero real-world false alarms: finite simulated samples only bound a rate.

**Unresolved (needs STEG):**
- whether a transformer-side meter exists or is planned (evidence review U3);
- the reporting interval and delivery cadence (U1, U4);
- the communication technology and store-and-forward behaviour (U2);
- the real data-loss level;
- the customer count per urban substation (N3: about 53 on national average, inferred).

## 4. Phase 2 plan (priority order)

1. **Ask STEG the six questions** in the evidence review §6. The transformer-meter question decides
   whether SHAHID is applicable at all.
2. **Merged-group fix:** split silent sets by electrical zone before scoring. This targets the
   10%-loss failure (TN-LOSS) and simultaneous events (phase 2 candidate 5). Develop on development
   data, evaluate once on untouched families.
3. **Load-dependent gap baseline** (phase 2 candidate 3) for the load-shaped unmetered failure,
   developed and evaluated the same way.
4. **Coarser reporting interval** (mode E: 30 and 60 min) once STEG's interval is known.
5. **Smaller networks** (25–60 customers) by feeder subsetting, to match the national average.
6. **A licensed regional or Tunisian load dataset** (the MORED licence must be checked first) to
   replace the uncalibrated diversity knob.

## 5. Critical verdict

- **What is Tunisia-specific in this version?** Only the questions asked and the scenario ranges
  they motivate:
  - 230/400 V overhead LV networks and net metering for prosumers (ANME/STEG reference, 2018);
  - an average of about 53 customers per substation (STEG 2020, inferred);
  - an AMI rollout whose interval, cadence and transformer metering are unpublished.
- **What remains German benchmark data?** All topology, all load and PV profiles, and the
  transformer sizes.
- **Which deployment assumptions are unverified?** A transformer-side energy series, its latency,
  the meter interval and cadence, store-and-forward after link failures, and the data-loss level.
- **Does the detector transfer?** Across PV, constant unmetered load, long comms failures and
  transformer delay, yes (15 of 24 families). Across heavy data loss and load-shaped unmetered
  energy, no. With daily batches, only retrospectively. Without a transformer meter, not at all.
- **What makes it fail?**
  - random loss of 10% (merged silent groups);
  - load-shaped unmetered energy;
  - no transformer measurement;
  - daily batch delivery, for real-time use.
- **Strongest defensible contribution:** a transformer-side energy-balance test that abstains
  instead of guessing. It is evaluated honestly on three grids, under explicit deployment modes, and
  it states the measurements it needs before any utility can use it.
- **Next highest-value action:** obtain STEG's answer on transformer-side metering and the meter
  data cadence (question 1–2). No further simulation changes the applicability verdict until then.
