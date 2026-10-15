# SHAHID and Tunisia: architecture, immutable baseline, deployment feasibility, plan

Version 1, 2026-10-10, branch `tunisia-study` (from `phase1` at a477271, tagged
`phase1-frozen-cp12`). This is the section 1 deliverable of the Tunisia brief. **No code or result
has been changed.**

**Scope of this inspection (honest).** I read:
- the simulator, observation and detector code paths that each deployment mode touches:
  `shahid/world.py`, `observe.py`, `scenario.py`, `detect.py`, `records.py`, `cp11.py`, `cp12.py`;
- all configs, the ledger, `ASSUMPTIONS.md`, `LIMITATIONS.md` and the generated documents.

This is not a fresh line-by-line audit of every module. Earlier audits (CP10–CP12) are documented,
but a document saying something was audited is not evidence that it is correct.

## 1. Architecture summary (as implemented)

```
SimBench LV grid (REUSED) ─► world.py: per-customer diversity (d), PV scale, unmetered energy,
                              AC power flow per interval (pandapower), cached truth
events (outages = line openings, re-solved) ─► truth/: meter energy, transformer energy
observe.py: meter/transformer errors, quantisation; per-reading arrival time
            (random loss, delay, concentrator failure with backlog); outage meters never send
            ─► observed/ (readings with arrival_ts, transformer series) + context/ (meters, zones)
detect.py (reads observed + context only; test-enforced):
   silent_groups(arrival, K=2) ─► evidence(): anchored expected energy M, residual R =
   T − Σ reported − gap0 − other-missing, sd_O, sd_C ─► Student-t LR with abstention band
   ─► verdict OUTAGE / COMMS_FAILURE / UNCERTAIN, sequential over L = 0..4
baselines.py, iforest.py (comparators) ─► evaluate.py (registered set-overlap matching)
explain.py (record, template text, hash-chained log, escalation table)
records.py / cp10–cp12.py (post-hoc analyses on stored records) ─► make_docs / make_pack
```

**Code facts that matter for Tunisia:**
- **The transformer series has no arrival time.** `detect.arrays` treats every transformer
  interval as known at decision time (assumption A-LATENCY). A delayed or missing transformer feed
  cannot be represented without new code.
- **"Silent" means "not arrived by onset + K intervals".** With batch delivery (for example a daily
  upload), every meter would look silent between batches, so the current detector would produce
  whole-network silent groups. Real-time diagnosis is undefined in that mode.
- **The interval is hard-wired at 15 min.** There are 96 slots per day and 672 intervals per week
  in the history and split logic.

## 2. Results that must remain immutable

These are everything committed on `phase1` up to tag `phase1-frozen-cp12` (a477271):
- `results/*.json`, including `detector_params.json`, the CP7 held-out results, CP10–CP12 and the
  reproducibility checks;
- `results/cp6/*`, `results/records/*`, `results/figs/*`, `dataset/*`;
- the ledger entries C1 to CP12-T5;
- `docs/results_for_proposal.md` and `docs/proposal_pack.md`, which are only regenerated from
  those files.

Any Tunisia result goes to new files under `results/tunisia/` with its own ledger IDs (TN-*). The
frozen version 1 detector is used as is. A candidate method change, if any, is a separately named
version evaluated under a new protocol addendum.

## 3. Deployment-feasibility matrix

| Mode | What SHAHID needs | Evidence it exists in Tunisia | SHAHID today (code fact) | What the study should do |
|---|---|---|---|---|
| A. Transformer + customer interval data, near real time | LV-side energy series per MV/LV substation, aligned with customer intervals; per-reading arrival | U3: **no evidence** of substation metering; U1/U4: interval and latency unknown | Fully supported (all results so far) | Keep as the reference mode, labelled as an assumed deployment |
| B. Transformer series delayed (for example 1 h or 1 day) | as A, plus waiting for the transformer data | U3/U4 unknown | **Not represented.** The detector would use transformer data before it arrives (an implicit leak in that mode) | Add a transformer arrival time; decide only when it has arrived; report the added latency. Test: no decision uses a transformer interval before its arrival |
| C. Transformer series unavailable | — | (possible today: no evidence it exists) | **Not represented**; the method cannot run without it | Return "UNSUPPORTED: no transformer measurement" for every silent group; never fall back to hidden truth. Test it. Only meter-only baselines (count, structure) remain, with their known poor accuracy (CP7) |
| D. Customer readings in batches (every few hours or daily) | arrival-time-aware silence detection | U4 unknown; daily collection is common for billing AMI (not evidenced for STEG) | **Breaks:** between batches every meter looks silent | Detect silence relative to the batch schedule (a meter is silent if it is missing from a batch that arrived). Diagnosis becomes retrospective, so report "real time: unsupported" with the delay equal to the batch period |
| E. Coarser customer interval (30 or 60 min) | the same energy balance at a coarser resolution | U1 unknown | Not configurable (15 min hard-wired) | Aggregate the 15-min truth to 30 or 60 min and refit only on fault-free training weeks. Needs code changes in history and split logic (medium complexity) |
| F. Last-gasp messages | power-fail event per meter | U4 unknown | Option exists, off by default | Keep off for headlines; optional cell only |

**Bottom line:** SHAHID's diagnosis exists only in modes A, B (with added delay) and E (if the
refit works). In mode C it is unsupported. In mode D it is retrospective, not real time. Which mode
applies to STEG is unknown today (evidence review §1, questions 1–3).

## 4. Prioritised plan

Complexity: S < 1 h, M a few hours, L overnight compute. All runs use at most 2 workers.

| # | Work | Scientific value | Complexity | Power flow? | Fits before the 2026-10-13 freeze? |
|---|---|---|---|---|---|
| 1 | **Deployment modes B, C, D** (transformer arrival time, UNSUPPORTED verdict, batch-aware silence) plus truth-leak and unavailable-measurement tests, evaluated on existing event families (observation re-simulation on cached worlds) | high: answers "can it work with what STEG may have" | M | no | yes |
| 2 | **Protocol addendum E** written before any Tunisia number: hypotheses, scenario families (dev / val / held-out), seeds, metrics, success criteria | required for everything below | S | no | yes |
| 3 | **Tunisia-oriented sensitivity suite on existing grids** (`configs/tunisia/*.yaml`, versioned): PV 0/1/2, loss 1/5/10%, comms-failure duration 1–24 h, constant and load-shaped unmetered energy, summer vs winter weeks. All labelled ASSUMPTION, frozen detector, baselines on identical inputs, results by scenario, size and PV condition | medium–high | M–L | outage re-solves only (cached worlds) | partly; the full run is overnight |
| 4 | **Safe abstention fix** (phase 2 candidate 9): a WATCH group whose meters resume without the onset reading is escalated, never closed. Records only | high (removes a known silent-closure flaw) | S | no | yes |
| 5 | **Load-dependent gap candidate** (phase 2 candidate 3): developed on dev weeks, compared with the frozen method, evaluated once on untouched families. A new method version, never replacing version 1 | high, but it is a method change after the freeze | M–L | no (records and observed data) | risky before the freeze |
| 6 | **Coarser reporting interval** (mode E) | medium–high | M–L | no | risky |
| 7 | **Smaller networks** (about 25–60 customers, N3) by feeder subsetting of SimBench grids | medium | L | yes (new worlds) | no: overnight only |
| 8 | Update the proposal to match verified results (supported / unsupported / unresolved claims) | required | S | — | yes, last |

**Recommendation:** do 2 → 1 → 4 → 3 (development and validation families now, held-out overnight)
→ 8 before the freeze. Defer 5, 6 and 7 to Phase 2, or to an overnight run only if the team accepts
a post-freeze method version. None of this makes SHAHID "Tunisian". At most it shows which
Tunisian deployment conditions it needs and survives.
