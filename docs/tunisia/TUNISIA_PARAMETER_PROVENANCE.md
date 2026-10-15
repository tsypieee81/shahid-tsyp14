# Parameter provenance for a Tunisia-oriented scenario layer

Version 1, 2026-10-10, branch `tunisia-study`. Evidence IDs (E, N, T, P, L, U) refer to
`TUNISIA_EVIDENCE_REVIEW.md`.

**Provenance classes:**
- **SIMBENCH:** taken from the German SimBench benchmark (REUSED).
- **PUBLIC-TN:** derived from a cited public Tunisian source.
- **ASSUMPTION:** chosen by us, not measured.
- **DESIGN CHOICE:** a method or protocol setting.
- **UNKNOWN-TN:** no Tunisian evidence found.

**"Configurable today"** says whether the existing simulator exposes the parameter in
`configs/*.yaml` without code changes.

## Network and load

| Parameter | Current value | Provenance | Tunisian evidence | Proposed Tunisia sensitivity range (all ASSUMPTION unless marked) | Configurable today |
|---|---|---|---|---|---|
| LV network topology, impedances | SimBench `1-LV-semiurb5`, `urban6`, `rural3` | SIMBENCH | T1–T2: 230/400 V, mostly overhead Al twisted cable ≤ 70 mm²; no public feeder data. T5 has a 33-node Sfax network (impedances only, no customer count) | Use the existing three SimBench grids; flag as German topology | yes (`world.grid`) |
| Customers per transformer | 104 (semiurb5), 118 (rural3) | SIMBENCH | N3: national average about 53 per MV/LV substation (INFERRED); urban distribution UNKNOWN-TN | about 25–120. **Smaller networks need a subsetting option that does not exist yet** | no (grid choice only) |
| Load shapes | about 10 SimBench household shapes, scaled | SIMBENCH | L1: no public Tunisian interval data; L2: summer afternoon AC peak (secondary) | No reshaping to "look Tunisian" (project rule). A labelled sensitivity season split (summer weeks vs winter weeks) uses the existing year | partly (week selection in evaluation) |
| Customer diversity d | 0.5 nominal, swept 0–1 | ASSUMPTION (A-DIV) | UNKNOWN-TN | 0–1 (already swept, CP6) | yes (`world.diversity`) |
| PV scale | 1.0 × SimBench PV; swept 0–3 | SIMBENCH × ASSUMPTION | P1–P3: national PV share of customers on the order of 2% (INFERRED); clustering unknown; T3: ≤ 6 kWc single-phase | 0 (no PV), 1, 2 × SimBench; separately report midday-only events | yes (`world.pv_scale`) |
| PV metering | net at the customer meter | DESIGN CHOICE | T4: bidirectional meter at the customer (PUBLIC-TN), consistent with net metering | keep | — |
| Unmetered energy (losses, public lighting, theft) | none nominal; constant or load-shaped 1–10 kW cells | ASSUMPTION | E3/E7: loss and fraud reduction are stated programme goals; magnitude per LV network UNKNOWN-TN | constant 0–5 kW; load-shaped 0–10 kW (already cells) | yes (`world.unmetered`) |
| Transformer loading | from SimBench loads | SIMBENCH | UNKNOWN-TN | covered indirectly by grid choice and PV scale | no |

## Measurement

| Parameter | Current value | Provenance | Tunisian evidence | Proposed range | Configurable today |
|---|---|---|---|---|---|
| Customer meter gain sd / noise / resolution | 0.5% / 0.2% / 1 Wh | ASSUMPTION (A-METERERR) | UNKNOWN-TN (meter class not published) | gain 0–1%, noise ×0–10 (CP6 cells) | yes (`meter.*`) |
| **Transformer-side meter exists** | assumed yes | ASSUMPTION | **U3: no evidence** of MV/LV substation metering | modes: available / delayed / unavailable (`TUNISIA_FEASIBILITY.md`) | **no** (always present) |
| Transformer meter gain sd / noise / resolution | 0.2% / 0.1% / 10 Wh | ASSUMPTION (A-TMETERERR) | UNKNOWN-TN | gain 0–2% (CP6 cells) | yes (`tmeter.*`) |
| **Transformer series latency** | zero (always known at decision time) | ASSUMPTION (A-LATENCY) | U4 UNKNOWN-TN | 0, 1 h, 1 day | **no** |

## Communication and timing

| Parameter | Current value | Provenance | Tunisian evidence | Proposed range | Configurable today |
|---|---|---|---|---|---|
| **Customer reporting interval** | 15 min | DESIGN CHOICE (SimBench resolution) | **U1 UNKNOWN-TN** | 15 min, 30 min, 60 min (aggregation of the 15-min truth) | **no** |
| **Delivery cadence** | each reading individually, near real time | ASSUMPTION (A-LATENCY) | U4 UNKNOWN-TN ("temps réel" in press only) | near real time; batches every 4 h; daily batch | **no** (only random delays) |
| Random missing readings | 1% | ASSUMPTION (A-COMMS) | UNKNOWN-TN | 1%, 5%, 10% | yes (`comms.p_missing`) |
| Delayed readings | 3%, Geometric mean 4 intervals | ASSUMPTION (A-COMMS) | UNKNOWN-TN | 3–10% | yes |
| Store-and-forward after a link failure | yes (backlog) | ASSUMPTION (A-COMMS) | U2 UNKNOWN-TN | on / off | yes (`comms.backlog`) |
| Concentrator layout | one per feeder | ASSUMPTION | U2 UNKNOWN-TN | aligned / random (CP6 cell) | yes |
| Comms-failure duration | 1–4 h uniform | ASSUMPTION (A-COMMS-DURATION) | UNKNOWN-TN | 1–4 h; add 4–24 h | yes (`generator.duration_steps`) |
| Last-gasp messages | off | DESIGN CHOICE | U4 UNKNOWN-TN | off (headline never depends on it) | yes |

## Events

| Parameter | Current value | Provenance | Tunisian evidence | Proposed range | Configurable today |
|---|---|---|---|---|---|
| Event rate | about 1 per transformer-day | DESIGN CHOICE (A-PREVALENCE, evaluation mix) | N4 is an energy indicator, not a frequency; UNKNOWN-TN | keep for evaluation; report base-rate curves (CP10) | yes |
| Outage size and location | single lines opened, zones 1–40 meters | ASSUMPTION (A-ZONES-REAL) | UNKNOWN-TN | keep | yes (`generator.zone_sizes`) |
| Outage duration | 1–4 h uniform | ASSUMPTION | UNKNOWN-TN | 1–4 h; add 4–12 h | yes |
| Outage / comms mix | 0.4 / 0.6 | DESIGN CHOICE | UNKNOWN-TN | 0.1–0.9 handled by reweighting (CP12 Task 4) | yes |
| Simultaneous outage and comms | CP6 cell | ASSUMPTION | UNKNOWN-TN | 0 and 1 cell | yes |

## Detector (frozen version 1; not a Tunisia parameter)

K = 2, L_max = 4, 14-day history, 1-day gap baseline, Student-t df 4, abstention band 0.03, and
prior 0.5 are DESIGN CHOICES fitted or chosen on development data (`results/detector_params.json`).
They are **not** re-tuned for any Tunisia scenario. Per-grid refits of the gap and estimator noise
on fault-free training weeks are part of the frozen procedure (CP7).

## Summary

- **Tunisia-specific today: nothing in the simulator.**
  - Public Tunisian sources support only three things: 230/400 V overhead LV networks (T1–T2), net
    bidirectional metering for prosumers (T4), and a national average of about 53 customers per
    substation (N3, inferred).
  - Every load, topology and timing input is German benchmark data or an assumption.
- **The three inputs that decide whether SHAHID works at all are UNKNOWN for Tunisia and not
  configurable today:**
  1. whether a transformer-side meter exists (U3);
  2. the reporting interval (U1);
  3. the delivery cadence (U4).
