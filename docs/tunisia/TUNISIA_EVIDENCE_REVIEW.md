# Tunisia evidence review (SHAHID, branch `tunisia-study`)

Status: **evidence review, version 1 of 2026-10-10.** Every source below was accessed on
2026-10-10. Nothing here is STEG data obtained by the team. All of it is public, and most of it is
not a primary technical specification.

How to read the labels:
- **CONFIRMED (primary):** stated by STEG, ANME, AFD or a peer-reviewed paper, on the page cited.
- **CONFIRMED (secondary):** stated in a news article citing STEG or TAP. Treat as indicative only;
  the figures in these articles disagree with each other.
- **INFERRED:** our reasoning from confirmed facts, with the arithmetic shown.
- **UNKNOWN:** searched for and not found.

## 1. STEG smart metering and Smart Grid programme

| # | Statement | Label | Source |
|---|---|---|---|
| E1 | Programme phase 1 (3 years from 2021) deploys AMI for LV and MV electricity and LP gas: smart meters, telecom infrastructure and services, and a secure information system (SI-AMI). Phase 2 (to 2030) adds national meter rollout and "SCADA DMS". | CONFIRMED (primary) | STEG, "Programme Smart Grid", https://www.steg.com.tn/fr/page/programme-smart-grid |
| E2 | Step 1 zones: Sfax city and Kerkennah; part of Sousse city and part of Sidi Bouzid; part of Kram and part of Béja. 340,000 LV electricity meters, 140,000 LP gas meters, and 25,000 MV and large-customer meters nationwide. | CONFIRMED (primary) | same page |
| E3 | AFD sovereign loan of €120 M (2018), €1 M grant and €1.5 M facilities. Contracts signed 27 June 2022. Lots awarded to Siemens, Sagemcom, SIAME, Efluid and CGI. Technologies "non captives". Phase 2 (2026–2030) is generalisation. | CONFIRMED (primary) | AFD press release, https://www.afd.fr/fr/actualites/communique-de-presse/compteurs-electriques-intelligents-tunisie ; AFD project page https://www.afd.fr/en/carte-des-projets/supporting-smart-grids-improve-energy-performance |
| E4 | A 500,000-meter pilot went into operation in May 2025. The meter data management system (Siemens GridscaleX MDM) is in production for meter-to-cash, licensed for 5.5 million meters, with support to 2035. | CONFIRMED (vendor case study, not STEG) | Siemens Advanta, https://www.siemens-advanta.com/cases/steg-smart-grid-project-in-tunisia |
| E5 | By end of March 2026 about 80,000 LV meters were installed in pilot zones (Sfax, Kerkennah, Sousse, Béja). Target: 500,000 by end of 2026; general rollout from 2027; about 5 million by 2035. | CONFIRMED (secondary) | Managers.tn, 2026-03-31, https://managers.tn/2026/03/31/le-compteur-intelligent-de-la-steg-ce-que-change-pour-les-tunisiens/ ; Business News, 2026-04-01, https://businessnews.com.tn/2026/04/01/smart-grid-la-steg-deploie-des-compteurs-intelligents-pour-plus-defficacite-de-transparence-et-des-factures-reelles/1394594/ |
| E6 | Counts conflict across sources: 340,000 LV (STEG page) vs 450,000 (Business News) vs about 510,000 electricity and gas (AFD) vs 500,000 pilot (Siemens). The first tender (3 Dec 2020) slipped. Earlier LV meter tenders were declared unsuccessful twice. | CONFIRMED (secondary) | as E1–E5; Tuniscope, https://www.tuniscope.com/article/350446/business/economie/la-steg-declare-infructueux-pour-la-2eme-fois-l-appel-d-offres-pour-des-compteurs-basse-tension-150411 |
| E7 | Stated purposes: real-consumption billing instead of estimated bimonthly billing, loss and fraud detection, remote monitoring of the network, remote detection of faults and anomalies ("détection à distance des pannes"). | CONFIRMED (secondary) | Business News, as E5 |

**UNKNOWN after search:**
- **U1:** the **interval at which LV meters record and report** (15 min, 30 min, hourly, daily). News says "en temps réel" without a figure.
- **U2:** the **communication technology** (PLC/G3, RF mesh, cellular) and whether **data concentrators sit in MV/LV substations**.
- **U3:** whether any **transformer-level (MV/LV substation) energy meter** is installed or planned, and whether its series reaches the head-end. No STEG source mentions substation metering, a "compteur de bilan" or substation supervision. "SCADA DMS" is planned only for Period 2.
- **U4:** **outage notification** (last-gasp) capability and reading **latency to the head-end**.
- **U5:** the head-end system vendor, and whether interval data is used beyond billing.

**Consequence for SHAHID:** the method's essential input, a transformer-side energy series aligned in time with customer intervals, is **not evidenced** for any Tunisian deployment. Smart-meter deployment does not imply it (see `TUNISIA_FEASIBILITY.md`).

## 2. Network facts (STEG annual report 2020, primary)

Source: STEG, *Rapport annuel 2020*, p. 29–31, https://www.steg.com.tn/system/files/pdf/Rapport_Annuel_steg_2020_fr.pdf

| # | Statement (2020 unless noted) | Label |
|---|---|---|
| N1 | LV lines 121,074 km; MV lines 62,115 km; MT-BT transformer substations 79,180 (75,065 in 2018; 78,507 in 2019). | CONFIRMED (primary) |
| N2 | Customers: LV 4,213,725; MV 20,008; HV 21. | CONFIRMED (primary) |
| N3 | **Average LV customers per MV/LV substation ≈ 53** (4,213,725 / 79,180 = 53.2), and about 1.5 km of LV line per substation (121,074 / 79,180). This is a national average mixing dense urban cabins and small rural pole-mounted stations; the distribution is UNKNOWN. | INFERRED (our arithmetic) |
| N4 | LV continuity indicator "Critère B" (energy not distributed relative to installed LV power, expressed in minutes): 176 min (2020), 214 min (2019), 172 min (2018). This is not an outage frequency, and no per-transformer outage frequency is published. | CONFIRMED (primary) |
| N5 | 2023: about 4,494,013 customers in total and 192,881 km of MV + LV lines. | CONFIRMED (primary): https://www.steg.com.tn/fr/page/distribuer |

The SimBench grids used so far (semiurb5: 104 loads; urban6; rural3: 118 loads) are **about twice
the national-average customer count per substation**. Whether they are typical of the urban pilot
zones (Sfax, Sousse) is UNKNOWN.

## 3. LV network configuration and PV connection rules (ANME/STEG/GIZ, primary)

Source: ANME, *Référentiel technique des installations photovoltaïques raccordées au réseau électrique national basse tension*, version 5, validated 31/10/2018 (STEG, ANME, CSPV, GIZ working group), p. 18–20, https://www.anme.tn/sites/default/files/2025-03/referentiel-technique-des-installations-photovoltaiques-raccordees-au-reseau-electrique-national-basse-tension.pdf

| # | Statement | Label |
|---|---|---|
| T1 | LV network 230/400 V ± 10%, 50 Hz; TT earthing; customers single-phase (2-wire) or three-phase (4-wire). | CONFIRMED (primary) |
| T2 | LV lines are mostly overhead self-supporting twisted insulated aluminium cables, max 70 mm² per phase. Underground copper up to 120 mm². Flat-rate subscriptions are 7 kVA (single-phase) and 13 kVA (three-phase). | CONFIRMED (primary) |
| T3 | Residential PV peak ≤ subscribed power; single-phase PV ≤ 6 kWc. STEG impact study above 40 kWc; max 200 kWc three-phase on LV. | CONFIRMED (primary) |
| T4 | A **bidirectional meter** is installed at the existing meter location. The production meter is integrated in the inverter. | CONFIRMED (primary) |
| T5 | A peer-reviewed Sfax-North LV study (STEG network) gives 33 nodes, 230/400 V, and MV supply at 10/15/30 kV. It does not give the transformer rating, customer count or time resolution; data are on request. | CONFIRMED (primary, limited): Zdiri et al., *Sci. Rep.* 15:10594 (2025), doi:10.1038/s41598-025-93488-2 |

Consequence: in Tunisia the **customer meter records net energy** for prosumers (T4). PV is already
behind the meter in SHAHID's model (each meter's reading is the net). That is consistent with T4,
but the import/export register split is not modelled.

## 4. PV self-production context

| # | Statement | Label | Source |
|---|---|---|---|
| P1 | PROSOL ELEC (grid-connected residential PV): by end of 2019 about 3,400 households and about 11,298 kWc. | CONFIRMED (primary, dated) | ANME, https://www.anme.tn/fr/project/raccorde-en-bt |
| P2 | Later figures: about 300 MW for about 90,000 families (2024–2026 statements). Figures across years are not reconcilable from public pages. | CONFIRMED (secondary/agency statements, inconsistent) | Managers.tn 2026-08-19, https://managers.tn/2026/08/19/prosol-elec-2026-les-entreprises-passent-elles-a-letape-concrete/ ; ANME news, https://www.anme.tn/fr/news/la-ceremonie-de-signature-dun-accord-de-financement-des-programmes-prosol-et-prosol-elec |
| P3 | National PV penetration per LV feeder: UNKNOWN. If about 90,000 PV homes are spread over about 4.2 M LV customers, the national average is about 2% of customers, but local clustering (e.g. Sfax) is unknown. | INFERRED (order of magnitude only) | P2, N2 |

## 5. Load data and demand patterns

| # | Statement | Label | Source |
|---|---|---|---|
| L1 | No public Tunisian residential interval load dataset was found. STEG load curves are not published online. | UNKNOWN (searched) | searches 2026-10-10 |
| L2 | Summer peak is driven by air conditioning; STEG statements in the press cite about 2.8 M AC units (2024) and an afternoon peak. | CONFIRMED (secondary) | L'Économiste Maghrébin 2026-07-31, https://www.leconomistemaghrebin.com/2026/07/31/40-des-climatiseurs-en-tunisie-non-conformes-et-energivores/ |
| L3 | Nearest regional open dataset: MORED (Moroccan households, 12 households, seconds-level, weeks to months). Its **licence is not verified**; it is not Tunisian. | candidate, licence TODO | https://raw.githubusercontent.com/MOREDataset/MORED/master/README.md ; Energies 13(24):6737, doi:10.3390/en13246737 |

Project rule: profiles must **not** be reshaped "to look Tunisian". Any demand-pattern
variation is a labelled sensitivity scenario, never a claim about Tunisian households.

## 6. Unresolved questions (for STEG, in priority order)

1. Is there, or will there be, an energy meter at the LV side of MV/LV substations in the pilot zones, and does its series reach the head-end with the same interval as customer meters? (U3)
2. Which interval do LV smart meters record (load profile), and how often is it collected: near-real-time, several times a day, or daily batch? (U1, U4)
3. Which communication technology, and are data concentrators per substation? Do concentrators store and forward after an outage of the link (A-COMMS)? (U2)
4. Do meters send power-fail (last-gasp) messages, and are they visible to operators? (U4)
5. Typical customer count, transformer rating and phase mix of urban substations in Sfax and Sousse. (N3)
6. Outage frequency and duration per LV network, and communication-failure statistics from the pilot. (N4 gives only an energy-based indicator.)
