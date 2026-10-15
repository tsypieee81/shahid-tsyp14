# Business case: deploying SHAHID in one STEG district

**Status.** Every figure here is either a FACT with a public source (`configs/business.yaml`), a
ledger value from SIMULATED evaluations, an ESTIMATE derived from them (ledger BUS-01 to BUS-05), or
a formula where a unit cost has no public source. No price was invented. All money is in Tunisian
dinars (TND). No cost line has a USD source; if one is added, it converts at the Central Bank of
Tunisia interbank average of 3.0085 TND per USD on 8 October 2026 (La Presse, 11 October 2026), stored
once in `configs/business.yaml`. Regenerate with `python -m shahid.business_model`.

**The main result.** In this simulation, compute and storage cost very little. The cost is operator
time. Under the version 1 escalation table, the review load of a district of 149 substations is
121.7 hours per day at 5 minutes per item (BUS-02), which costs at least 120486.23 TND per
district-year (BUS-06). That figure is a floor: it prices each hour at the legal minimum wage of
2.713 TND (Decree No. 67 of 2026, 40-hour regime), without employer charges or the qualification a
grid operator needs, so the real cost is higher. Two things decide whether deployment is
affordable: the meter-count gate, which is not yet wired into the escalation table, and STEG's
real data-loss level.

## 1. Prerequisites

| Prerequisite | Why | Status |
|---|---|---|
| LV energy meter at each transformer, read every 15 min | Without it the method cannot decide: every energy-balance method answers UNSUPPORTED for 0.997 of episodes (TN-H2) | **Required.** A costed hardware line wherever absent; the share of substations without one is unknown (first question to STEG) |
| Head-end export of customer readings with arrival times | The detector needs readings and when they arrived (`docs/data_contract.md`) | adapter to build (integration) |
| Quarter-hour customer readings | Hourly readings are outside the measured envelope: missed-outage rate 0.245 (CAD-4) | to confirm with STEG |
| Zone and topology register | Which customers a line opening isolates (`context/zones`) | from GIS |
| Concentrator mapping | Which meters share a concentrator (`context/meters`) | from the AMI head-end |

## 2. Implementation: one agency-sized pilot district

- **Size.** One district the size of the STEG Douz agency: about 24,400 customers, 149 transformer
  substations, 639 km of LV lines, 17 staff (Managers, 15 July 2026). The per-transformer rates
  below come from simulated grids of 99 and 41 customers and are an ESTIMATE for such a district.
- **Phase A, retrospective replay (no operator).** Run the frozen detector on 90 days of the district's
  historical data. Fit `detect.fit` per transformer on fault-free periods, then compare verdicts
  with the district's outage and AMI-ticket records.
- **Phase B, shadow operation.** Verdicts go to a review queue; no action depends on them.
- **Go/no-go criteria,** taken from the safety limits frozen in Phase 1 (`results/detector_params.json`
  stamp): missed-outage rate at most 0.05; false-outage rate at most 0.05; fault-free false outages at
  most 0.001 per meter-day. Coverage and human items per transformer-day are reported, not
  thresholded: their acceptable level is a STEG decision, taken before the pilot.

## 3. Production

- **Operations.** One process per district; a whole simulated year of one transformer is scored in
  13.36 s on one laptop process (BUS-04). Compute is not a cost driver.
- **Monitoring.** Daily: share of transformers with a current fit, human items per transformer-day,
  fault-free false outages per meter-day (the drift KPI, §4).
- **Audit-log retention.** Decision and operator logs are append-only and hash-chained; one entry is
  about 1603 bytes (BUS-05). The retention period is a legal decision for STEG.
- **Role separation.** The detector annotates data and opens tickets only. Crew dispatch and customer
  contact always need a person (`configs/escalation.yaml`). Whoever maintains thresholds is not the
  person approving verdicts.
- **Data protection.** Interval consumption is personal data. Organic Law 2004-63 applies. A draft
  organic law of 132 articles was heard in parliament on 17 February 2026 and names data
  processing by artificial intelligence (Business News, 18 February 2026). Readings stay inside STEG;
  only fitted, dimensionless parameters may leave a site (`docs/EXTENDED_REPORT.md`, collective defence).

## 4. Continuous training (recalibration)

- **What is trained.** No labelled data is needed. `detect.fit` estimates noise and persistence
  parameters from each transformer's own fault-free readings. The decision thresholds stay frozen.
- **When.** Every 90 days (DESIGN CHOICE) and after every topology change of the feeder.
- **Drift KPI.** The fault-free false-outage rate per meter-day. A rise above the go/no-go limit
  triggers a refit and a review.
- **What it cannot fix.** Load-shaped unmetered energy breaks the balance assumption (TN-H4); a
  refit does not repair it.

## 5. Integration

| Interface | Direction | Content |
|---|---|---|
| AMI head-end | in | customer readings with arrival times, concentrator mapping |
| Transformer LV meter | in | 15-min energy series |
| GIS | in | line and zone register |
| Outage management or ticketing | out | outage alerts for approval, communication tickets, abstentions with evidence |
| Audit store | out | hash-chained decision and operator logs |

## 6. Deployment cost

**One-off (TND).**

| Line | Amount |
|---|---|
| Transformer LV meters | 149 × share without an LV meter × (meter unit cost + installation) — unit costs unknown |
| Integration (head-end, ticketing, GIS adapters) | integration person-days × engineer day rate — unknown |
| Operator training | pilot operators × training cost per person — unknown |
| Historical replay and calibration (Phase A) | engineer person-days × day rate — unknown |

**Recurring per year (TND).**

| Line | Amount | Size, from the simulation |
|---|---|---|
| **Operator review time (main cost)** | at least 120486.23 TND per district-year under v1 at 5 min per item (BUS-06); hours × operator hourly cost | 44410.7 hours at 5 min per item under v1 (BUS-02) |
| Hosting | 12 × monthly hosting cost | one process; 13.32 s of compute per transformer-year (BUS-04) |
| Storage | stored GB × 12 × price per GB-month | 107.46 MB of readings per 1000 meter-years (BUS-05) |
| Recalibration review | (365 / 90) × review person-days × day rate | — |
| Refresher training | operators × refresher cost | — |

**Operator review time by policy** (hours per day, district of 149 substations, 1% random data loss;
BUS-02):

| Policy | 2 min per item | 5 min per item | 10 min per item |
|---|---|---|---|
| Version 1, rural2 rates | 48.7 | 121.7 | 243.3 |
| Gate that escalates, rural2 rates | 20.6 | 51.5 | 103.1 |
| Gate that closes, rural2 rates | 0.1 | 0.1 | 0.3 |
| Version 1, semiurb4 rates | 20.0 | 50.0 | 100.0 |
| Gate that escalates, semiurb4 rates | 8.9 | 22.2 | 44.4 |

**Operator review cost by policy, lower bound** (at least … TND per district-year; same district,
BUS-06 and BUS-07). Each hour is priced at the legal minimum wage of 2.713 TND, which excludes employer
charges and the qualification of a grid operator, so every figure is a floor, not an estimate of the
real cost.

| Policy | 2 min per item | 5 min per item | 10 min per item |
|---|---|---|---|
| Version 1, rural2 rates | at least 48194.49 | at least 120486.23 | at least 240972.47 |
| Gate that escalates, rural2 rates | at least 20418.66 | at least 51046.66 | at least 102093.31 |
| Gate that closes, rural2 rates | at least 53.75 | at least 134.38 | at least 268.76 |
| Version 1, semiurb4 rates | at least 19807.24 | at least 49518.11 | at least 99036.22 |
| Gate that escalates, semiurb4 rates | at least 8788.29 | at least 21970.72 | at least 43941.45 |

The gate that closes is cheapest, but it lost 16 of 350 whole-feeder outages with no verdict on
development data (P2D-02). The gate that escalates lost none. Neither gate is wired into the escalation
table yet. At 10% random data loss the load rises several-fold (`results/business/business.json`),
so STEG's real data-loss level decides the budget.

## 7. Value

- **Crew time.** Every communication failure that SHAHID calls correctly is a truck roll that is not
  sent. Either gate also avoids 14.46 false outage verdicts per transformer-year on rural2 and 9.973
  on semiurb4 (BUS-03).
- **Service quality.** Outages are confirmed from the transformer side with a median latency of
  2 intervals after the meters go silent (C7-01), with evidence attached for the operator.
- **What does not apply.** Lost-sales arguments do not apply: STEG sold electricity at 290.7 millimes
  per kWh in 2025 against an average production cost of 456.3 millimes (Managers, 29 June 2026), so
  restoring supply sooner does not recover margin. SHAHID does not address theft or non-technical
  losses; the reported network losses of 19.7% are outside its scope.

## 8. To verify with STEG before deployment

1. Which substations have an LV energy meter, its interval, and how fast its data arrive (TN-H1, TN-H2).
2. The customer reading interval and delivery cadence (CAD-4, TN-H3).
3. The communication technology and whether meters store and forward readings after a link failure.
4. The real random data-loss level (it drives operator load, §6).
5. Real outage and communication-failure durations (they set the re-check timeout, CP12-T2b).
6. The loaded operator hourly cost (the minimum wage used here is only a floor), procurement prices for meters and installation, and hosting rules.
7. The acceptable operator load and the audit-log retention period.
