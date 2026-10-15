# SHAHID demo video: storyboard

Length 4:51 (narration measured by the build), 1920×1080, 30 fps, H.264 + AAC. One neutral synthetic
voice, no music. Everything shown is SIMULATED. Every number on screen or in the narration is listed with
its source under its scene and again in the source index at the end.

**Source types.** A number may come from:
- a **ledger row** in `docs/CLAIMS_LEDGER.md` (cited by its id, for example C7-01);
- a **stamped result file** (cited by its path), read by the scene at render time where possible;
- a **paper reference**: a press fact cited in the paper's Section I, shown with its reference numbers
  ([1], [2], [4]–[6]) small on screen. Only the context scene uses this type.

Nothing else may be shown or spoken.

**Shot types.** **MANIM**: animation rendered by Manim Community Edition. **CONSOLE**: recorded live from
`streamlit run ui/app.py` with Playwright, page only. **CARD**: a styled card animated in Manim from
real command output.

The narration text lives in [narration.py](narration.py); the build reads it for the voice, the beat
timings and the subtitles. The script below is a copy of it.

## Arc and timing

| # | Scene class | Time (measured) | Type | Words | Purpose |
|---|---|---|---|---|---|
| 1 | `S01Hook` | 0:00.0–0:14.6 | MANIM | 33 | the question |
| 2 | `S02Context` | 0:14.2–0:47.8 | MANIM + CARD | 70 | why it matters in Tunisia; two opposite responses |
| 3 | `S03Idea` | 0:47.4–1:54.6 | MANIM | 146 | the witness, two hypotheses, the probability, the band |
| 4 | `S04Console` | 1:54.2–2:45.8 | CONSOLE | 120 | the working console |
| 5 | `S05Results` | 2:45.4–3:29.0 | MANIM | 97 | held-out result, baselines, where it fails |
| 6 | `S06Governance` | 3:28.6–4:10.2 | MANIM | 90 | the honest twist, what it may do alone, trust devices |
| 7 | `S07Impact` | 4:09.8–4:39.9 | MANIM + CARD | 66 | district cost, prerequisite |
| 8 | `S08Work` | 4:39.6–4:51.2 | CARD | 22 | how we work; closing title |
| | | | | **644** | |

Scenes overlap by the 0.4 s crossfade. Each beat lasts 0.3 s of lead-in, its sentences with 0.35 s
between them, and 0.5 s of air. A scene whose animation outruns its narration stops the build.

**Decisions taken at storyboard approval.**
1. **Worked example.** The 8-meter case in `results/decision_log_demo.jsonl` (line 1) is the documented
   wrong verdict of ledger C9-01: the true cause was an outage (`docs/LIMITATIONS.md` item 12). The
   centrepiece teaches with the **34-meter case on line 2**, which C9-01 records as correct. The 8-meter
   case is a short honest twist (about 10 s, 9.8 s of speech) that opens the governance scene.
2. **Never p = 1.0 on screen.** The 34-meter case is shown as "p > 0.999": recomputed from the logged
   evidence with the detector's own formula, p = 0.99998 (the log rounds it to 1.0).
3. **Context facts** come from the paper's press references and are shown with them.
4. **No LaTeX.** All symbols are Unicode text.

---

## Scene 1: Hook (MANIM)

| Visual | On-screen text | Narration |
|---|---|---|
| A transformer draws itself; five feeders grow out of it; 54 meters pop onto them and pulse as they report. 34 meters on feeders 2–4 fade to grey rings, one by one; an amber dashed box and a "?" mark them. | `18:00 · 34 meters silent` · `illustration` (corner) · SIMULATED tag | Every fifteen minutes, smart meters report what their customers used. At six in the evening, thirty-four of them go silent at once. Did those customers lose power, or did only their data stop? |

Sources: 34 meters, onset 18:00: `results/decision_log_demo.jsonl` line 2 (`record.evidence.n_meters`,
`record.onset`), C9-01. 15-minute readings: `docs/data_contract.md`, CAD-4. The network is an
illustration, labelled as such.

## Scene 2: Context (MANIM + CARD)

| Beat | Visual | On-screen text | Narration |
|---|---|---|---|
| 2a | A 5×9 grid of squares, each 10,000 meters (the 450,000 of the first phase); 8 squares fill blue (80,000). | `STEG is rolling out smart meters` · `80,000 LV meters by end of March 2026` · `450,000 first phase` · source line | Tunisia's utility, STEG, is rolling out smart meters: about 80,000 low-voltage meters in pilot zones by the end of March 2026, in a first phase of 450,000. |
| 2b | Four districts of houses; each goes dark in turn while the previous one comes back. | `summer 2026: rotating power cuts` · source line | That summer, during a heatwave, its network went through rotating power cuts. |
| 2c | Split screen: red "Outage / send a crew", a truck drives in; blue "Data lost / no crew", a faded truck is crossed out. | `Outage · send a crew` / `Data lost · no crew` | So when a group of meters goes quiet, someone must choose quickly between two causes with opposite answers. An outage needs a crew. A communication failure needs no crew at all. |

Sources (paper references, shown small): 80,000 LV meters by end of March 2026 and a first phase of
450,000: paper refs [1] africanmanager2026compteurs and [2] webdo2026compteurs. Rotating cuts during the
summer 2026 heatwave: refs [4] newarab2026heatwave, [5] africanmanager2026heat, [6] webdo2026delestages.

## Scene 3: The idea (MANIM), the centrepiece

| Beat | Visual | On-screen text | Narration |
|---|---|---|---|
| 3a witness | The network returns with the 34 silent meters; energy particles still flow down every feeder. A kWh meter appears under the transformer; a halo pulses. | `the transformer meter: the witness` | Here is the idea. All the energy these customers use passes through one transformer, and a meter on its low-voltage side keeps counting. That meter is our witness. |
| 3b two numbers | Two bars grow at the right: M (dashed) to 4.32, R (blue) to 3.93, with live numbers. | `M expected` · `R witness sees` · `kWh, 2 readings` | From the silent customers' own history, we expect them to use M: here, 4.32 kilowatt-hours over two readings. The witness still sees R, energy that no reporting meter accounts for: 3.93. |
| 3c two worlds | The network fades. The R bar drains to near zero beside a red line, then rises to M beside a blue line. | `If power was cut: R ≈ 0` / `If only data was lost: R ≈ M` | If the power had been cut, R would be close to zero. If only the data stopped, R would be close to M. |
| 3d curves | The bars become a kWh axis. A red Student-t curve at 0 (spread 0.16) and a blue one at 4.32 (spread 0.68) draw themselves; a dashed marker drops at R = 3.93; a red dot sits flat on the axis, a blue dot high on its curve. | `spread if outage 0.16 · if data lost 0.68` | Each cause predicts a curve, with a spread learned from the transformer's fault-free days. At 3.93, an outage is almost impossible; a communication failure is just what we would expect. |
| 3e probability | The two dots fly into `p = blue / (blue + red)`; the value counts up to `> 0.999`. A probability scale appears with the band 0.03–0.97 shaded amber; the needle sits at the blue end. | `p > 0.999` · `between 0.03 and 0.97: a person decides` | Comparing the two heights gives a probability: communication failure, above 0.999. And the system decides only when the probability falls outside a narrow band at either end. Anything in between goes to a person. |

Sources: M 4.32, R 3.93, spreads 0.16 and 0.68, 2 readings, 34 meters: `results/decision_log_demo.jsonl`
line 2, C9-01 ("34-meter comms failure correct (probability 1.0)"). **p > 0.999**: recomputed from those
logged values with `shahid/detect.py` `score()` (Student-t, prior 0.5): 0.99998; the log rounds it to 1.0.
Curve shape, 4 degrees of freedom: `results/detector_params.json` (`fitted.t_df`). Band 0.03:
`results/detector_params.json` (`thresholds.bayes.abstain_band`).

## Scene 4: Working console (CONSOLE)

Recorded live by `build.py console`: Playwright at 1920×1080, page video only (no browser chrome), a
cursor ring, presentation mode on, scenario `showcase`, operator log reset to genesis before the take.
Overlay chips on the empty part of the top bar: `SIMULATED` and `CONSTRUCTED DEMONSTRATION DAY`; a
"Working console" lower-third for 2.8 s.

| Beat | Interaction (scripted) | Narration |
|---|---|---|
| 4a | Situation view at 10:30. "Next event" three times: 13:00, 13:30, 14:15; the replay clock and KPI tiles move. | This is the operator console, replaying a simulated day. It is a preview: no operator has used it yet. |
| 4b | Queues view, tab *Comms unconfirmed*, the 09:45 concentrator failure (20 meters). The evidence card: the cursor rests on expected against visible energy, the probability on its band, the explanation, then "automatic · R3". | A data concentrator fails. The evidence card shows what the witness still sees, the probability against its band, and a plain-language explanation written from the same record. The system opens a data ticket on its own, and nothing more. |
| 4c | Tab *Outages awaiting approval*, the 06:15 outage of the largest feeder; click **Approve**. | When a feeder loses power, the verdict never sends a crew by itself. It waits in its own queue until a person approves. |
| 4d | Tab *Uncertain*, the 12:30 midday group; its card shows the probability inside the band and the reason for not deciding; click **Escalate to supervisor**. | When the evidence is too thin, as here at midday, the system abstains and hands the case over, with the evidence. |
| 4e | Audit view: the approval and the escalation in the hash-chained log; the approval carries the console's fast-approval flag, and a caption appears with it: "Approvals under 5 s are flagged (over-trust check)" (5 s read from `ui/oplog.py` `FAST_SECONDS`); **Verify chain**; open the tamper test, change one digit of a logged value in the copy, **Verify edited copy**: "Verification fails at line 0: the edit is detected". | Every action enters a hash-chained log. Change one character in a copy, and verification fails at that entry. |

Sources: the console reads `results/demo/showcase.json` and `ui/operator_log.jsonl`; showcase events per
`configs/demo_scenarios.yaml`; rule R3: `configs/escalation.yaml`; "no operator has used it": paper
Section VII and `ui/README.md`. The narration speaks no number in this scene. The console shows
probabilities through `fmt_p`, which reads ">0.999" and "<0.001" at the ends, so no rounded "1.000"
appears. The explanation text is the stored record and says "Confidence in this cause: 1.0".

## Scene 5: Results (MANIM)

| Beat | Visual | On-screen text | Narration |
|---|---|---|---|
| 5a | Three numerals: 0.723, 0.000, 0.009; a bar: decided 72.3%, to a person 27.7% (amber). | `held-out urban network · method frozen · evaluated once` | On a held-out urban network, evaluated once with the method frozen, it decided 72 percent of events. Among them: no false outages, and under one percent of outages missed. The rest went to a person. |
| 5b | Coverage (x) against false + missed outages (y): grey squares for the four simple rules, rings for the trained classifiers (one per seed), a blue star for SHAHID at (0.723, 0.009). | `better: right and low` | Simple rules decide everything, but get many wrong. Trained classifiers, under the same safety limits, decided less or erred more. |
| 5c | The plane shrinks left; bars of missed-outage rate: 15-min readings 0.006, 60-min readings 0.245, 10 kW load-shaped unmetered energy 0.241, against a dashed 0.05 limit. | `SIMULATED on German benchmark networks · no Tunisian data tested yet` | It fails where the physics says it should: with hourly readings, or with unmetered energy that follows the load, about a quarter of outages are missed. All of this is simulated, on German benchmark networks. No Tunisian data has been tested yet. |

Sources: 0.723, 0.000, 0.009 and the plane: read at render time from
`results/studies/classifier_comparison/summary.json` (`frozen.urban6`, `baselines.urban6`,
`models.*.seeds.*.urban6`), equal to the registered values of C7-01 (`results/cp7_heldout.json`) as
CLF-03 states; classifiers CLF-04, CLF-05. 72.3% / 27.7% = coverage 0.723 / abstention 0.277 (C7-01).
Baselines (coverage, error): naive (0.871, 0.092), step (1.0, 0.615), count (1.0, 0.826), structure
(0.765, 0.568). 0.006 and 0.245: CAD-4. 0.241: C6-05, AU-04. Limit 0.05: the go/no-go safety limits
(`docs/BUSINESS_CASE.md` §2). "72 percent" = 0.723; "under one percent" = 0.009; "about a quarter" =
0.241 and 0.245.

## Scene 6: The honest twist, governance and trust (MANIM)

| Beat | Visual | On-screen text | Narration |
|---|---|---|---|
| 6a twist | The curves return with the 8-meter case: M 2.31, R 1.27, spreads 0.13 and 0.74; `p = 0.996` in blue; a red stamp `TRUE CAUSE: OUTAGE`; an amber arrow at R. | `another simulated case · 8 meters` · `a delayed, heavy reading inflated R` | But confidence is not truth. Another case scored 0.996 for data lost; it was an outage, and one delayed reading had inflated R. |
| 6b rules | Five rule cards R1–R5; R3 alone carries an "automatic, provisional" chip, the others a person icon; a lock beside "crew or customers: always a person". | `escalation table · first matching rule wins` | That is why the rules are written down, as an escalation table. The system may act alone in one way only: flag missing data and open a ticket. Dispatching a crew or contacting customers always needs a person. |
| 6c trust | The table fades; two lists: against over-trust (alternative cause on every verdict, audit sample of automatic closures, very fast approvals flagged), against under-trust (track record per verdict class). | `effect not yet measured with operators` | Against over-trust, every verdict shows its alternative cause, automatic closures are sampled for audit, and very fast approvals are flagged. Against under-trust, each verdict class shows its track record. |

Sources: twist: `results/decision_log_demo.jsonl` line 1 (8 meters, M 2.31, R 1.27, spreads 0.13 and
0.74, p 0.996); true cause outage and the delayed-reading mechanism: C9-01, `docs/LIMITATIONS.md` item 12.
Rules R1–R5 (20 meters, p ≥ 0.95, ≤ 40 meters; R3 provisional): `configs/escalation.yaml`. Trust
devices and "effect not measured": `ui/panels/trust.py`, `docs/BRIEF_COVERAGE.md` Goal 3.

## Scene 7: Impact and deployment (MANIM + CARD)

| Beat | Visual | On-screen text | Narration |
|---|---|---|---|
| 7a | A grid of 149 transformer glyphs; one lights blue; `13.3 s` to score one transformer-year. | `a Douz-sized district: 149 substations` · `one laptop process` | For a district the size of STEG's Douz agency, with 149 substations, computing is cheap: a year of one transformer is scored in about thirteen seconds. |
| 7b | Two bars: `≥ 120,486 TND` (current rules), `≥ 51,046 TND` (escalating gate, not yet wired in). | `operator review: the main cost` · `lower bound per district-year: minimum wage, 5 min per item` | The real cost is people. At minimum wage, reviewing the cases costs at least 120,000 dinars a year; a gate not yet wired in would cut that to about 51,000. |
| 7c | A transformer with its kWh meter, ringed amber. | `prerequisite: an energy meter at each transformer` | And it all needs an energy meter at each transformer. |

Sources, read at render time: 149 substations: `configs/business.yaml`
(`facts.douz_transformer_substations`), BUS-02. 13.3 s = 13.32 s per transformer-year
(`results/business/business.json` `compute.seconds_per_transformer_year`), BUS-04. 120,486.23 and
51,046.66 TND per district-year, rural2 rates, 1% loss, 5 min per item, minimum wage: BUS-06
(`results/business/business.json`); shown rounded down so "≥" stays true. Gate not wired: paper
Section VII, `docs/BUSINESS_CASE.md` §6. Prerequisite: TN-H2.

## Scene 8: How we work (CARD)

| Visual | Narration |
|---|---|
| Four terminal cards with a bare `$` prompt, built from the real output captured at build time: `python -m pytest -q` (62 passed), `python -m shahid.check_numbers` (levels 1–3: 0 unmatched, 0 violations), `python -m shahid.check_tables` (7 tables, 205 numbers, 0 unmatched), and three protocol commits from `git log` as "date · SHAHID Team · title". Then the title `SHAHID — the witness layer`. | Every protocol was committed before its run. Every number traces to a claims ledger, and every check passes. SHAHID: the witness layer. |

Sources: `video/build/cards.json`, written by `build.py cards` from the commands themselves; timings and
paths are stripped. The build stops if a check fails.

---

## Narration script (644 words)

Pronunciation: SHAHID as `ʃəhˈid` (sha-HEED); STEG as one word, `stˈɛɡ`; Douz as `dˈuz`. Numbers are read
as words (`SAY` in narration.py).

**1.** Every fifteen minutes, smart meters report what their customers used. At six in the evening,
thirty-four of them go silent at once. Did those customers lose power, or did only their data stop?

**2.** Tunisia's utility, STEG, is rolling out smart meters: about 80,000 low-voltage meters in pilot zones
by the end of March 2026, in a first phase of 450,000. That summer, during a heatwave, its network went
through rotating power cuts. So when a group of meters goes quiet, someone must choose quickly between two
causes with opposite answers. An outage needs a crew. A communication failure needs no crew at all.

**3.** Here is the idea. All the energy these customers use passes through one transformer, and a meter on
its low-voltage side keeps counting. That meter is our witness. From the silent customers' own history, we
expect them to use M: here, 4.32 kilowatt-hours over two readings. The witness still sees R, energy that no
reporting meter accounts for: 3.93. If the power had been cut, R would be close to zero. If only the data
stopped, R would be close to M. Each cause predicts a curve, with a spread learned from the transformer's
fault-free days. At 3.93, an outage is almost impossible; a communication failure is just what we would
expect. Comparing the two heights gives a probability: communication failure, above 0.999. And the system
decides only when the probability falls outside a narrow band at either end. Anything in between goes to a
person.

**4.** This is the operator console, replaying a simulated day. It is a preview: no operator has used it
yet. A data concentrator fails. The evidence card shows what the witness still sees, the probability against
its band, and a plain-language explanation written from the same record. The system opens a data ticket on
its own, and nothing more. When a feeder loses power, the verdict never sends a crew by itself. It waits in
its own queue until a person approves. When the evidence is too thin, as here at midday, the system abstains
and hands the case over, with the evidence. Every action enters a hash-chained log. Change one character in
a copy, and verification fails at that entry.

**5.** On a held-out urban network, evaluated once with the method frozen, it decided 72 percent of events.
Among them: no false outages, and under one percent of outages missed. The rest went to a person. Simple
rules decide everything, but get many wrong. Trained classifiers, under the same safety limits, decided less
or erred more. It fails where the physics says it should: with hourly readings, or with unmetered energy
that follows the load, about a quarter of outages are missed. All of this is simulated, on German benchmark
networks. No Tunisian data has been tested yet.

**6.** But confidence is not truth. Another case scored 0.996 for data lost; it was an outage, and one
delayed reading had inflated R. That is why the rules are written down, as an escalation table. The system
may act alone in one way only: flag missing data and open a ticket. Dispatching a crew or contacting
customers always needs a person. Against over-trust, every verdict shows its alternative cause, automatic
closures are sampled for audit, and very fast approvals are flagged. Against under-trust, each verdict class
shows its track record.

**7.** For a district the size of STEG's Douz agency, with 149 substations, computing is cheap: a year of
one transformer is scored in about thirteen seconds. The real cost is people. At minimum wage, reviewing the
cases costs at least 120,000 dinars a year; a gate not yet wired in would cut that to about 51,000. And it
all needs an energy meter at each transformer.

**8.** Every protocol was committed before its run. Every number traces to a claims ledger, and every check
passes. SHAHID: the witness layer.

---

## Short cut (pitching slot, at most 3:00)

Built by `python video/build.py --cut short` into `build/shahid_demo_short.mp4` (+ `_subtitled.mp4`, `.srt`),
working in `build/short/`. The summary build above is untouched. Narration and scene list: `SHORT` and
`CUTS["short"]` in [cuts.py](cuts.py); voice speed 1.08. Context, the curve walkthrough, governance,
business and work-process scenes are left out. Timecodes: shot list below (measured by the build).

| # | Scene class | Type | Words | Content |
|---|---|---|---|---|
| 1 | `S01Hook` (reused; beat a compressed to fit) | MANIM | 31 | 34 meters go silent at 18:00 |
| 2 | `SIdeaShort` | MANIM | 98 | the witness; M 4.32 against R 3.93 with the two worlds; p > 0.999 on the band |
| 3 | `S04Console` | CONSOLE | 184 | replay to 14:15; comms evidence card; outage approved; 12:30 case escalated; audit view with the fast-approval caption; tamper test |
| 4 | `SResultsShort` | MANIM | 64 | 0.723 / 0.000 / 0.009 and the decided/person bar; one limit: hourly readings |
| 5 | `SCloseShort` | CARD | 26 | prerequisite and title |
| | | | **403** | |

### Short-cut narration

**1.** Every fifteen minutes, smart meters report what their customers used. At six in the evening,
thirty-four of them go silent at once. Did those customers lose power, or only their data?

**2.** SHAHID asks the transformer. A meter on its low-voltage side still counts the energy of customers whose
data stopped, but not of customers who lost power. That meter is our witness. From their own history, the
silent customers should use M: 4.32 kilowatt-hours over two readings. The witness still sees R: 3.93. If the
power had been cut, R would be close to zero. Here it is close to M. So the probability of a communication
failure is above 0.999: decided, and no crew is sent. Between 0.03 and 0.97 the system does not decide: a
person does.

**3.** This is the operator console, replaying a simulated day. It is a preview: no operator has used it yet,
and every verdict here comes from stored simulations. A data concentrator fails. The evidence card shows what
the witness still sees, the probability against its band, and a plain-language explanation written from the
same record. On its own, the system may only open a data ticket, and rule R3 marks even that as provisional.
A feeder loses power: thirty-seven meters go dark at once. The outage verdict waits in its own queue: no crew
moves until a person reads the evidence and approves it. At midday, seven meters go quiet and the evidence is
too thin. Its probability, 0.145, sits inside the band. The system abstains, and the case goes to a supervisor
with its evidence, instead of a guess. Every action enters a hash-chained log. That approval came in under
five seconds, so the console flags it for review: a check against over-trust. Change one character in a copy
of the log, and verification fails at that entry: the record cannot be quietly edited.

**4.** On a held-out urban network, evaluated once with the method frozen, it decided 72 percent of events,
with no false outages and under one percent of outages missed. The rest went to a person. One honest limit:
with hourly readings instead of quarter-hourly ones, about a quarter of outages are missed, so it needs
quarter-hour readings. Everything here is simulated, on German benchmark networks.

**5.** In the field, SHAHID also needs an energy meter at each transformer. Every number in this video traces
to our claims ledger. SHAHID: the witness layer.

### Short-cut sources

| Number | Scene | Source |
|---|---|---|
| 15-minute readings; 34 meters; 18:00 | 1 | as in the summary: `docs/data_contract.md`, CAD-4; `results/decision_log_demo.jsonl` line 2, C9-01 |
| M 4.32 kWh over two readings, R 3.93 kWh | 2 | `results/decision_log_demo.jsonl` line 2; C9-01 |
| p > 0.999 (recomputed 0.99998; logged 1.0) | 2 | same line with `shahid/detect.py` `score()` |
| band 0.03–0.97 | 2 | `results/detector_params.json` `thresholds.bayes.abstain_band` |
| rule R3 provisional | 3 | `configs/escalation.yaml` |
| 37 meters (06:15 outage), 7 meters (12:30 group), probability 0.145 | 3 | `results/demo/showcase.json` (`groups[*].n_meters`, `posterior_comms` 0.1448), constructed demonstration day |
| under five seconds, the fast-approval flag | 3 | `ui/oplog.py` `FAST_SECONDS` = 5.0; the take's `ui/operator_log.jsonl` entry (`fast: true`), checked by the build |
| 72 percent (0.723), no false outages (0.000), under one percent missed (0.009), 72.3% / 27.7% | 4 | C7-01; CLF-03; `results/studies/classifier_comparison/summary.json` `frozen.urban6` |
| missed 0.006 at 15-min readings, 0.245 at 60-min ("about a quarter") | 4 | CAD-4 |
| prerequisite: a meter at each transformer | 5 | TN-H2; `docs/BUSINESS_CASE.md` §1 |

On screen in scene 4: `0.723`, `0.000`, `0.009`, `decided 72.3%`, `to a person 27.7%`, `15-min readings
missed 0.006`, `60-min readings missed 0.245`, SIMULATED tag and footnote. Scene 3 is the same live console
capture as the summary (`S04Console`), recorded again with the short cut's beat lengths and steps
`replay, comms, outage, uncertain, audit, tamper`.

---

## Explainer cut (README, no console footage)

Built by `python video/build.py --cut explainer` (working folder `build/explainer/`), with burned-in
subtitles; the `media` step writes the repository copies in `docs/media/`: `shahid_explainer.mp4`
(720p, at most 10 MB), the silent preview loop (R against M, then the verdict; 960 px, at most 4 MB) and
`shahid_explainer_poster.png`. Narration: `EXPLAINER` in [cuts.py](cuts.py); voice speed 1.08. It reuses
`S01Hook`, `S03Idea` (with the curves), `SResultsShort` and `SCloseShort`.

| # | Scene class | Type | Words | Content |
|---|---|---|---|---|
| 1 | `S01Hook` | MANIM | 26 | 34 meters go silent at 18:00 |
| 2 | `S03Idea` | MANIM | 102 | the witness; M 4.32 against R 3.93; the two worlds; the two curves; p > 0.999 and the band |
| 3 | `SResultsShort` | MANIM | 38 | 0.723 / 0.000 / 0.009, decided 72.3%, to a person 27.7%; the hourly-readings line on screen |
| 4 | `SCloseShort` | CARD | 19 | prerequisite and title |
| | | | **185** | |

### Explainer narration

**1.** Every fifteen minutes, smart meters report what their customers used. At six in the evening,
thirty-four go silent at once. Lost power, or only lost data?

**2.** SHAHID asks the transformer. A meter on its low-voltage side keeps counting: that meter is the
witness. From their own history, the silent customers should use M: 4.32 kilowatt-hours over two readings.
The witness still sees R: 3.93. If the power had been cut, R would be close to zero. If only the data was
lost, R would be close to M. Each cause predicts a curve. At 3.93, an outage is almost impossible; lost data
is what we would expect. So the probability of a communication failure is above 0.999. Between 0.03 and
0.97 the system abstains, and a person decides.

**3.** On a held-out urban network, evaluated once, it decided 72 percent of events, with no false outages
and under one percent of outages missed. The rest went to a person. Everything here is simulated, on German
benchmark networks.

**4.** SHAHID needs an energy meter at each transformer. Every number traces to the claims ledger. SHAHID:
the witness layer.

### Explainer sources

| Number | Scene | Source |
|---|---|---|
| 15-minute readings; 34 meters; 18:00 | 1 | `docs/data_contract.md`, CAD-4; `results/decision_log_demo.jsonl` line 2, C9-01 |
| M 4.32 kWh over two readings, R 3.93 kWh; spreads 0.16 / 0.68 on screen | 2 | `results/decision_log_demo.jsonl` line 2; C9-01 |
| curve shape, t-distribution with 4 degrees of freedom | 2 | `results/detector_params.json` `fitted.t_df` |
| p > 0.999 (recomputed 0.99998; logged 1.0) | 2 | same line with `shahid/detect.py` `score()` |
| band 0.03–0.97 | 2 | `results/detector_params.json` `thresholds.bayes.abstain_band` |
| 72 percent (0.723), no false outages (0.000), under one percent missed (0.009), 72.3% / 27.7% | 3 | C7-01; CLF-03; `results/studies/classifier_comparison/summary.json` `frozen.urban6` |
| on screen: 15-min readings missed 0.006, 60-min readings missed 0.245 | 3 | CAD-4 |
| prerequisite: a meter at each transformer | 4 | TN-H2; `docs/BUSINESS_CASE.md` §1 |
| length 88 s (87.9 s measured) | README | `video/build.py --cut explainer`; allowlisted as `[environment]` |

---

## Style sheet

**Palette** (from `ui/theme.py`, so the animation and the console read as one product):

| Token | Hex | Use |
|---|---|---|
| BG | `#0b1220` | frame background |
| CARD / RAISED | `#111a2e` / `#16233a` | cards, rule rows, lower-thirds |
| BORDER / LINE | `#1e293b` / `#334155` | card borders, network lines, axes |
| TEXT / MUTED / FAINT | `#e2e8f0` / `#94a3b8` / `#64748b` | primary text / labels / silent meters, footnotes |
| OUTAGE | `#ef4444` | outage hypothesis and verdict only |
| COMMS | `#3b82f6` | communication-failure hypothesis, reporting meters, SHAHID's own mark |
| UNCERTAIN | `#f59e0b` | abstention band, SIMULATED tag, warnings |
| OK | `#34d399` | only a passing check |

**Type.** Inter 4.1 for all text and subtitles; JetBrains Mono 2.304 for terminal cards (both SIL OFL 1.1).
Sizes at 1080p: titles 34–48, body 24–30, labels 22, footnotes and source lines 18 (never below 18).

**Strokes.** Network lines 2; shapes and curves 3; emphasis 4; axes 2 in `LINE`. Fills at 0.15–0.35 opacity.

**Motion** (Manim Community conventions for timing and animation groups): `smooth` for most
moves, `ease_out_cubic` for entrances, `linear` only for the constant energy flow; `run_time` 0.5–2 s;
reveals in `LaggedStart` with `lag_ratio` 0.02–0.3; `ValueTracker` + `always_redraw` for bars, curves,
markers and the needle, updaters cleared when a beat ends; `ReplacementTransform` between states of one
idea, `TransformFromCopy` when the source stays visible. Each beat's animation fills part of its narration
and `hold()` waits out the rest.

**Layout.** Safe margin 0.6 units on every side; labels with `next_to(..., buff ≥ 0.1)`. The SIMULATED tag
(amber outline chip, 18) sits top-right in every results, console and evidence shot. Section lower-thirds:
a blue rule and the section name in 24 MUTED, bottom-left, 2.8 s.

**Transitions and audio.** 0.4 s crossfades between scenes. Voice only; loudness normalised to −16 LUFS
integrated in two passes (ffmpeg `loudnorm`). Subtitles at most two lines.

**Voice.** One neutral synthetic English voice; two candidates were compared before the choice
(`python video/tts.py` writes the samples to `build/voices/`).

## Source index

| Number | Scene | Source |
|---|---|---|
| 34 meters, 18:00 | 1 | `results/decision_log_demo.jsonl` line 2; C9-01 |
| 15-minute readings | 1 | `docs/data_contract.md`; CAD-4 |
| 80,000 LV meters (end of March 2026); 450,000 first phase | 2 | paper refs [1], [2] |
| rotating cuts, summer 2026 | 2 | paper refs [4]–[6] |
| M 4.32 kWh, R 3.93 kWh, spreads 0.16 / 0.68, 2 readings | 3 | `results/decision_log_demo.jsonl` line 2; C9-01 |
| p > 0.999 (0.99998 recomputed; logged 1.0) | 3 | same line, `shahid/detect.py` `score()` |
| t-distribution, 4 degrees of freedom | 3 | `results/detector_params.json` `fitted.t_df` |
| band 0.03 (0.03–0.97) | 3 | `results/detector_params.json` `thresholds.bayes.abstain_band` |
| coverage 0.723, false outage 0.000, missed outage 0.009, abstention 0.277 | 5 | C7-01; CLF-03; `results/studies/classifier_comparison/summary.json` |
| baseline and classifier points | 5 | `results/studies/classifier_comparison/summary.json`; CLF-03 to CLF-05 |
| missed 0.006 (15 min), 0.245 (60 min) | 5 | CAD-4 |
| missed 0.241 (load-shaped unmetered 10 kW) | 5 | C6-05, AU-04 |
| limit 0.05 | 5 | go/no-go limits, `docs/BUSINESS_CASE.md` §2 |
| 8 meters, M 2.31, R 1.27, spreads 0.13 / 0.74, p 0.996, true cause outage | 6 | `results/decision_log_demo.jsonl` line 1; C9-01; `docs/LIMITATIONS.md` item 12 |
| R1–R5: 20 meters, p ≥ 0.95, ≤ 40 meters | 6 | `configs/escalation.yaml` |
| 149 substations, Douz | 7 | `configs/business.yaml`; BUS-02 |
| 13.3 s per transformer-year (13.32) | 7 | BUS-04; `results/business/business.json` |
| ≥ 120,486 and ≥ 51,046 TND per district-year | 7 | BUS-06; `results/business/business.json` |
| 62 passed; 6673, 1162, 1092 checked, 0 unmatched; 7 tables, 205 numbers | 8 | captured at build time (`build/cards.json`) |
