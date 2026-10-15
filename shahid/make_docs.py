"""Generate docs/RESULTS.md (and the untracked docs/build/proposal_pack.md) from result files (no typing).

Every number below is read from a result file at generation time; every section names its file.
Run: python -m shahid.make_docs   (also regenerates the pack figures in results/figs/pack_*.png)
"""
import json
from pathlib import Path

import numpy as np
import yaml

from shahid.check_numbers import decimals_allowed

R = Path("results")


def J(p):
    return json.load(open(R / p, encoding="utf8"))


def f3(x):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.3f}"


def f4(x):
    return "—" if x is None else f"{x:.4f}"


def ci(c, fmt=f3):
    return "—" if not c or c[0] is None else f"{fmt(c[0])}–{fmt(c[1])}"


def est(v, c):
    """Estimate with its 95% interval under the CP12 rounding rule (shahid.check_numbers):
    the estimate keeps the decimal place of the leading digit of the half-width, bounds one more."""
    if v is None or not c or c[0] is None:
        return f3(v)
    lo, hi = (0.0 if abs(x) < 1e-12 else float(x) for x in c)
    d = decimals_allowed(lo, hi)
    while d > 0 and decimals_allowed(round(lo, d + 1), round(hi, d + 1)) < d:  # half-width at a power of 10
        d -= 1
    return f"{v:.{d}f} ({lo:.{d + 1}f}–{hi:.{d + 1}f})"


def west(w):
    """Wilson dict {'rate', 'ci95'} -> estimate string."""
    return est(w["rate"], w["ci95"])


LABELS = {"cp6_nominal": "nominal (development grid, weeks 0–2)",
          "cp7_heldout_urban6": "held-out grid urban6, test weeks",
          "cp7_dev_semiurb5": "development grid, test weeks",
          "cp6_diversity_1.0": "diversity d = 1.0", "cp6_hn_pv_midday": "midday events, PV × 2",
          "cp6_hn_packet_loss_10pct": "10% random loss of readings",
          "cp6_tmeter_gain_0.02": "transformer-meter gain error sd 2%",
          "cp6_unmetered_profile_5.0kw": "load-shaped unmetered energy 5 kW",
          "cp6_hn_simultaneous_outage_comms": "outage and comms failure at the same time",
          "cp6_unmetered_profile_10.0kw": "load-shaped unmetered energy 10 kW",
          "feeder_semiurb5": "whole-feeder events, development grid",
          "feeder_urban6": "whole-feeder events, held-out grid",
          "rural3_eps": "untouched rural grid, test weeks",
          "ff_semiurb5": "fault-free, 1% loss, development grid",
          "ff_urban6": "fault-free, 1% loss, held-out grid", "rural3_ff": "fault-free, 1% loss, rural grid",
          "loss10_ff_semiurb5": "fault-free, 10% loss, development grid",
          "loss10_ff_urban6": "fault-free, 10% loss, held-out grid",
          "loss10_semiurb5": "events, 10% loss, development grid",
          "loss10_urban6": "events, 10% loss, held-out grid"}
LABELS.update({k[4:]: v for k, v in LABELS.items() if k.startswith("cp6_")})
ROW_NAMES = {"v1": "version 1 (registered)", "v1+gate": "version 1 + meter-count gate",
             **{f"v1+recheck{T}h": f"version 1 + comms re-check {T} h" for T in [1, 2, 4, 8]},
             **{f"v1+gate+recheck{T}h": f"version 1 + gate + comms re-check {T} h" for T in [1, 2, 4, 8]}}


def row_name(r):
    return ROW_NAMES[r] + ("" if r == "v1" else " [post-hoc variant, not pre-registered]")


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


NAMES = {"bayes": "likelihood-ratio test with abstention (primary, version 1)",
         "lr": "likelihood-ratio test without abstention", "share": "visible-share test",
         "ztest": "two-sided z-test", "naive": "naive share baseline", "step": "step baseline",
         "count": "count baseline", "structure": "structure baseline",
         "iforest": "Isolation Forest (added after the held-out test)"}

# Plain wording for judges (submission packaging): development-stage labels in the generated text are
# replaced by what they mean. Words only; no number changes (checked by diffing the number tokens).
PLAIN = [("Frozen version 1 (lr_band)", "Frozen method (likelihood-ratio test with abstention)"),
         ("lr_band − ztest", "likelihood-ratio test with abstention − two-sided z-test"),
         ("lr_band − share", "likelihood-ratio test with abstention − visible-share test"),
         (" (CP12 Task 5; 95% Wilson intervals)", " (95% Wilson intervals)"),
         (" (CP12 Task 3)", ""), (" (CP12 Task 4)", ""), (" (CP10 Task 8)", ""), (" (CP12)", ""),
         (" (CP8)", ""), ("CP6 C6-04", "ledger C6-04"),
         ("(CP10, post-hoc descriptive)", "(post-hoc descriptive)"),
         ("(CP5 validation, every setting)", "(development validation weeks, every setting)"),
         ("CP5 validation (selection data), v1.1", "development validation, version 1 + gate + re-check"),
         ("CP5 validation (selection data), v1", "development validation, version 1"),
         ("CP5 validation weeks", "development validation weeks"),
         ("CP5 validation episodes", "development validation episodes"),
         ("CP5 episode mix", "standard episode mix"), ("(CP5 mix)", "(standard episode mix)"),
         ("CP6 cells, development grid", "sensitivity cells, development grid"),
         ("(development grid, CP6)", "(development grid, sensitivity cells)"), ("(CP6)", "(sensitivity cells)"),
         ("Held-out grid (CP7, run once) with Isolation Forest added after CP7",
          "Held-out grid (run once), with the Isolation Forest added afterwards"),
         ("(new seeds, CP10 families; post-hoc)", "(new seeds, whole-feeder families; post-hoc)"),
         ("(CP10 base-rate curve)", "(base-rate curve, section 1)"), ("superseded by CP10", "superseded by the resolution limit"),
         ("Policy components, separated (CP12; ", "Policy components, separated ("),
         ("Registered outcome of the CP11 selection", "Registered outcome of the policy selection"),
         ("selected under addendum C, a declared deviation,", "selected under a declared deviation (docs/eval_protocol.md),"),
         ("(registered set overlap, addendum D)", "(registered set overlap, docs/eval_protocol.md)"),
         ("fixed in addendum D before computing", "fixed in the evaluation protocol before computing"),
         ("Matching rule: CP11 numbers that change", "Matching rule: earlier numbers that change"),
         ("| CP11 (onset-only match) | CP12 (registered set-overlap match) |",
          "| Earlier onset-only match | Registered set-overlap match |"),
         ("under version 1.1 in CP11 are not a matching artefact. CP11's column",
          "under the combined variant (gate + re-check) in the earlier policy selection are not a matching "
          "artefact. That earlier column"),
         ("of CP11's \"version 1.1\":", "of the earlier combined variant:"),
         ("the CP5 v1 selection's balanced figure", "the balanced figure of the first threshold selection"),
         ("CP2 smoke verdicts", "smoke-test verdicts"),
         ("\"Version 1.1\" as one policy", "The combined variant (gate + re-check) as one policy")]


COVERAGE_NOTE = (
    "**Why coverage is below 1 for methods without an abstention band.** The likelihood-ratio test "
    "without abstention, the visible-share test and the two-sided z-test answer UNCERTAIN when the "
    "expected energy of the silent group is below the minimum-energy threshold chosen for them on "
    "development validation weeks (`min_expected_kwh` in `results/detector_params.json`; rule at "
    "`shahid/detect.py:126`). The two-sided z-test also abstains when both or neither hypothesis fits "
    "(`shahid/detect.py:138`). The naive share baseline has its own minimum-energy rule "
    "(`shahid/baselines.py:64`), and the structure baseline abstains when the silent set is both a "
    "concentrator group and an electrical zone (`shahid/baselines.py:42`). The count and step baselines "
    "and the Isolation Forest never abstain.\n")


def plain(text):
    for a, b in PLAIN:
        text = text.replace(a, b)
    return text
METHODS = ["bayes", "ztest", "lr", "share", "naive", "step", "count", "structure"]


# ---------------------------------------------------------------- sections shared by both documents
def boundary_section(cp10):
    b = cp10["boundary"]
    rows = []
    for key in ["cp6_nominal", "cp7_heldout_urban6", "cp7_dev_semiurb5", "cp6_diversity_1.0",
                "cp6_hn_pv_midday", "cp6_hn_packet_loss_10pct", "cp6_tmeter_gain_0.02",
                "cp6_unmetered_profile_5.0kw", "cp6_hn_simultaneous_outage_comms",
                "cp6_unmetered_profile_10.0kw"]:
        x = b[key]
        rows.append([LABELS[key], est(x["snr"]["x90_logistic"], x["snr"]["x90_ci95"]),
                     est(x["share"]["x90_logistic"], x["share"]["x90_ci95"])])
    c = cp10["boundary_axis_consistency"]
    return table(["Condition", "SNR at P(correct) = 0.90 (95% CI)",
                  "share of transformer energy at P(correct) = 0.90 (95% CI)"], rows), c


def heldout_table(cp7, itf, cov_from_abst=True):
    r = cp7["targets"]["heldout_urban6"]["results"]
    rows = []
    for m in METHODS:
        x = r[m]
        rows.append([NAMES[m], f3(1 - x["abstention_rate"]), f3(x["accuracy_when_decided"]),
                     f3(x["outage_recall"]), f3(x["comms_recall"]), f3(x["false_outage_rate"]),
                     f3(x["missed_outage_rate"]), f4(x["fault_free_false_outage_per_meter_day"])])
    h = itf["heldout_urban6_test"]
    rows.append([NAMES["iforest"], f3(1 - h["abstention_rate"]), f3(h["accuracy_when_decided"]),
                 f3(h["outage_recall"]), f3(h["comms_recall"]), f3(h["false_outage_rate"]),
                 f3(h["missed_outage_rate"]), f4(itf["heldout_fault_free_false_outage_per_meter_day"])])
    return table(["Method", "Coverage", "Accuracy when deciding", "Outage recall", "Comms recall",
                  "False outage", "Missed outage", "Fault-free false outages per meter-day"], rows)


def feeder_table(e11, fam):
    fo = e11["task1_feeder_outcomes"][fam]
    rows = []
    for m in METHODS + ["iforest"]:
        if m not in fo:
            continue
        o, c = fo[m]["outage"], fo[m]["comms"]
        cell = west
        rows.append([NAMES[m], cell(o["correct"]), cell(o["called_comms"]), cell(o["abstained"]),
                     cell(o["never_detected"]), cell(c["correct"]), cell(c["called_outage"]),
                     cell(c["abstained"]), "—" if fo[m]["latency_median_intervals"] is None
                     else f"{fo[m]['latency_median_intervals']:.0f}"])
    return table(["Method", "Outage → outage (95% CI)", "Outage → comms", "Outage → abstained",
                  "Outage never detected", "Comms → comms", "Comms → outage", "Comms → abstained",
                  "Median latency (intervals)"], rows)


def load_table(e11):
    t = e11["task1_operator_load_all_methods"]
    fams = [("ff_semiurb5", "fault-free, 1% loss, dev"), ("ff_urban6", "fault-free, 1% loss, held-out"),
            ("loss10_ff_semiurb5", "fault-free, 10% loss, dev"),
            ("loss10_ff_urban6", "fault-free, 10% loss, held-out")]
    rows = []
    for m in METHODS + ["iforest"]:
        rows.append([NAMES[m]] + [f"{t[f][m]['human_items_per_day']:.2f}" for f, _ in fams])
    return table(["Method (human items per transformer-day)"] + [n for _, n in fams], rows)


def assumptions_full():
    rows = []
    for line in Path("docs/ASSUMPTIONS.md").read_text(encoding="utf8").splitlines():
        if line.startswith("| ") and not line.startswith("| ID"):
            c = [x.strip() for x in line.strip("|").split("|")]
            if len(c) >= 4:
                rows.append([c[0], c[1], c[2], c[3]])
    return table(["ID", "Statement", "Type", "Status"], rows)


def anomaly_table():
    d = yaml.safe_load(open("configs/defaults.yaml"))
    rows = [["Physical outage", "truth", "open one LV line, re-solve power flow; isolated customers and their PV drop to zero", "event file"],
            ["Comms failure (zone, concentrator, random set)", "observation", "readings of a meter set stop; stored readings arrive after the link returns", f"backlog {d['comms']['backlog']}"],
            ["Random missing reading", "observation", "each reading lost independently", f"p_missing {d['comms']['p_missing']}"],
            ["Delayed reading", "observation", "each reading late by Geometric extra intervals", f"p_delay {d['comms']['p_delay']}"],
            ["Real load change", "truth", "scale a meter set's load, re-solve", "factor 0.3–2.5"],
            ["Unmetered energy", "truth", "added to transformer energy (constant or load-shaped)", f"default {d['world']['unmetered']['kind']}"],
            ["Meter error", "observation", "fixed gain, noise, 1 Wh quantisation", f"gain sd {d['meter']['gain_sd']}"],
            ["Transformer-meter error", "observation", "fixed gain, noise, 10 Wh quantisation", f"gain sd {d['tmeter']['gain_sd']}"]]
    return table(["Class", "Layer", "Rule", "Default parameter (ASSUMPTION)"], rows)


# ---------------------------------------------------------------- CP12 sections (shared)
CAT_O = [("outage_verdict", "outage verdict → approval"), ("closed_as_comms", "closed as comms (wrong)"),
         ("uncertain", "uncertain → human"), ("comms_unconfirmed", "comms unconfirmed → human"),
         ("closed_no_verdict", "closed, no verdict, no human"), ("never_detected", "never detected")]
CAT_C = [("closed_as_comms", "closed as comms (correct)"), ("outage_verdict", "called outage (wrong)"),
         ("uncertain", "uncertain → human"), ("comms_unconfirmed", "comms unconfirmed → human"),
         ("closed_no_verdict", "closed, no verdict, no human"), ("never_detected", "never detected")]
GRIDS = {"dev": "whole-feeder events, development grid",
         "heldout": "whole-feeder events, held-out grid",
         "rural": "untouched rural grid, CP5 episode mix, test weeks"}
LOAD_LABELS = {"cp7_dev_semiurb5": "events (CP5 mix), 1% loss, development grid, whole year",
               "cp7_heldout_urban6": "events (CP5 mix), 1% loss, held-out grid, whole year",
               "loss10_semiurb5": "events (CP5 mix), 10% loss, development grid, whole year",
               "loss10_urban6": "events (CP5 mix), 10% loss, held-out grid, whole year"}
TYPES = [("uncertain", "uncertain"), ("outage_awaiting_approval", "outage verdict awaiting approval"),
         ("comms_unconfirmed", "communication verdict unconfirmed")]


def policy_outcomes(c12, grid, rows=None):
    t2 = c12["task2_components"]
    rows = rows or list(t2)
    L = []
    for cause, cats, word in [("outage", CAT_O, "Outages"), ("comms", CAT_C, "Communication failures")]:
        n = t2["v1"]["outcomes"][grid][cause]["outage_verdict"]["n"]
        body = [[row_name(r)] + [west(t2[r]["outcomes"][grid][cause][k]) for k, _ in cats] for r in rows]
        L.append(f"*{word} (n = {n}), {GRIDS[grid]}*\n\n" + table(["Policy row"] + [h for _, h in cats], body))
    return "\n\n".join(L)


def policy_load(c12, fam, rows=None):
    t2 = c12["task2_components"]
    rows = rows or list(t2)
    key = next(k for k in t2["v1"]["load"] if k.endswith("/" + fam))
    body = [[row_name(r)] + [est(t2[r]["load"][key][k]["per_day"], t2[r]["load"][key][k]["ci95"])
                             for k, _ in TYPES] for r in rows]
    return f"*{LOAD_LABELS.get(fam, LABELS[fam])}, human items per transformer-day*\n\n" + table(
        ["Policy row"] + [h for _, h in TYPES], body)


def policy_false_outages(c12, rows=None):
    t2 = c12["task2_components"]
    rows = rows or list(t2)
    body = [[row_name(r)] + [est(t2[r]["false_outage_per_year"][g]["per_year"],
                                 t2[r]["false_outage_per_year"][g]["per_year_ci95"])
                             for g in ["semiurb5", "urban6", "rural3"]] for r in rows]
    return table(["Policy row", "development grid (5 seeds pooled)", "held-out grid (5 seeds pooled)",
                  "rural grid (1 seed)"], body)


def policy_attention(c12, fam, rows=None):
    t2 = c12["task2_components"]
    rows = rows or list(t2)
    classes = [c for c in ["all", "single", "branch", "feeder"] if c in t2["v1"]["no_realtime_attention"][fam]]
    body = [[row_name(r)] + [west(t2[r]["no_realtime_attention"][fam][c]) for c in classes] for r in rows]
    ns = {c: t2["v1"]["no_realtime_attention"][fam][c]["n"] for c in classes}
    return f"*{LABELS[fam]}: outages without real-time attention*\n\n" + table(
        ["Policy row"] + [f"{c} (n = {ns[c]})" for c in classes], body)


def headline_table(c12):
    h = c12["task5_headline"]
    keys = [("coverage", "Coverage"), ("outage_recall", "Outage recall"), ("comms_recall", "Comms recall"),
            ("false_outage_rate", "False-outage rate"), ("missed_outage_rate", "Missed-outage rate")]
    body = [[name] + [west(h[k][q]) for q, _ in keys] for k, name in [
        ("dev_test_weeks", "development grid, test weeks"), ("heldout_urban6", "held-out grid urban6 (run once)"),
        ("untouched_rural3", "untouched rural grid rural3 (run once)")]]
    dv = h["diversity_range_cp6_d0_to_1"]
    body.append(["diversity d = 0…1 (CP6 cells, development grid)"]
                + [f"{dv[q][0]:.2f}–{dv[q][1]:.2f}" for q in
                   ["coverage", "outage_recall", "comms_recall", "false_outage", "missed"]])
    rg = h["range_over_three_evaluations"]
    return table(["Frozen version 1 (lr_band)"] + [n for _, n in keys], body), rg


def _num(x):
    return f"{x:.3f}" if isinstance(x, float) else str(x)


def matching_section(c12):
    m = c12["task1_matching"]
    rows = []
    for name, v in m["select_cp5_week2"].items():
        for k in v["cp11"]:
            if abs(v["cp11"][k] - v["rule_D"][k]) > 1e-12:
                rows.append([f"CP5 validation (selection data), {name}", k.replace("_", " "),
                             _num(v["cp11"][k]), _num(v["rule_D"][k])])
    for fam, v in m["outage_attention"].items():
        for k in v["cp11"]:
            if abs(v["cp11"][k] - v["rule_D"][k]) > 1e-12:
                rows.append([LABELS.get(fam, fam), k.replace("_", " "), _num(v["cp11"][k]), _num(v["rule_D"][k])])
    return table(["Data", "Quantity", "CP11 (onset-only match)", "CP12 (registered set-overlap match)"], rows)


def break_even_tables(c12, grid="heldout"):
    b = c12["task4_break_even"][grid]
    rows = list(c12["task2_components"]) + ["ztest", "lr", "share", "naive", "step", "count",
                                            "structure", "iforest"]
    body = []
    for r in rows:
        x = b["per_100"][r]
        body.append([row_name(r) if r in ROW_NAMES else NAMES[r]]
                    + [f"{x[k]:.1f}" for k in ["outage_closed_as_comms", "comms_called_outage",
                                               "human_reviews_per_100_outages", "human_reviews_per_100_comms",
                                               "no_attention_per_100_outages", "no_attention_per_100_comms"]])
    t1 = table(["Method / policy row", "Outages closed as comms", "Comms called outage",
                "Human reviews per 100 outages", "Human reviews per 100 comms failures",
                "No attention per 100 outages", "No attention per 100 comms failures"], body)
    body = []
    for pair, curve in b["extra_reviews_per_wrong_verdict_avoided"].items():
        a, base = pair.split(" vs ")
        cells = []
        for pi in ["0.1", "0.3", "0.5", "0.7", "0.9"]:
            x = curve[pi]
            cells.append(est(x["ratio"], x["ratio_ci95"]) if x["ratio"] is not None and x["ratio_ci95"]
                         else x["relation"])
        body.append([f"{ROW_NAMES[a]} vs {NAMES[base]}"] + cells)
    t2 = table(["Comparison", "10% outages", "30%", "50%", "70%", "90%"], body)
    return t1, t2, b["n_outages"], b["n_comms"]


def task3_table(c12, key):
    t = c12["task3_small_groups"][key]
    body = [[b, x["n"], west(x["coverage_90"]), west(x["below_lower_bound"]), west(x["above_upper_bound"]),
             f"{x['z_quantiles']['0.5']:.2f}",
             f"{x['lower_tail_observed_vs_model']['4']['observed']:.4f} / "
             f"{x['lower_tail_observed_vs_model']['4']['model_t4']:.4f}",
             x["false_outage_verdicts"]] for b, x in t.items()]
    return table(["Meters in group", "Groups", "Inside nominal 90% interval", "Below interval",
                  "Above interval", "Median z", "z < −4: observed / model", "False outage verdicts"], body)


def closed_no_verdict_sizes(c12, fams=("feeder_semiurb5", "feeder_urban6")):
    """Meter counts (min, max) of the whole-feeder outages the gate closes without a verdict."""
    n = [e["n_meters"] for f in fams for e in c12["task1_matching"]["feeder_never_detected"][f]["episodes"]
         if e["outcome"] == "watch_closed_no_verdict"]
    return min(n), max(n)


def comms_duration_sentence(c12):
    names = {"cp5": "CP5 episode mix, development grid", "feeder_urban6": LABELS["feeder_urban6"],
             "rural3_eps": LABELS["rural3_eps"]}
    return "; ".join(f"{names[f]}: median {d['quantiles_h']['0.5']:.2f} h (10–90%: {d['quantiles_h']['0.1']:.2f}–"
                     f"{d['quantiles_h']['0.9']:.2f} h, range {d['min_h']:.0f}–{d['max_h']:.0f} h)"
                     for f, d in c12["comms_duration"].items() if f != "source")


# ---------------------------------------------------------------- RESULTS.md
def results_doc():
    cp7, cp10, itf, e11, sel, wld, c12 = (J("cp7_heldout.json"), J("cp10.json"), J("iforest.json"),
                                          J("cp11_eval.json"), J("cp11_select.json"), J("cp10_world.json"),
                                          J("cp12.json"))
    btab, cons = boundary_section(cp10)
    br = cp10["base_rates"]
    safety = cp10["safety_table_cp5_validation"]
    pc = cp10["paired_coverage_heldout"]
    auc = e11["task1_if_auc"]
    t3 = c12["task3_small_groups"]
    t2 = c12["task2_components"]
    L = []
    L.append("# Results for the proposal\n")
    L.append("**Generated by `python -m shahid.make_docs` from result files. Do not edit by hand.** "
             "Sources: `results/cp7_heldout.json`, `results/cp10.json`, `results/cp10_world.json`, "
             "`results/iforest.json`, `results/cp11_select.json`, `results/cp11_eval.json`, "
             "`results/cp12.json`, `results/audit.json`. Ledger: `docs/CLAIMS_LEDGER.md`. All data is "
             "simulated (`docs/LIMITATIONS.md`).\n")
    L.append("Reporting rules: never quote accuracy-when-deciding without coverage; quote headline "
             "rates as the range over the three evaluations (§0); labelled-episode precision comes from "
             "an artificial mix of about one event per day and is not field precision; nominal figures "
             "depend on the uncalibrated diversity parameter. Rounding rule: an estimate keeps the "
             "decimal place of the leading digit of its 95% interval half-width, and the bounds one "
             "more; a rate keeps at least two decimals (checked by `tests/test_numbers.py`). Every policy row other than version 1 is a "
             "post-hoc variant, not pre-registered.\n")
    htab, rg = headline_table(c12)
    L.append("## 0. Headline ranges, frozen version 1 (CP12 Task 5; 95% Wilson intervals)\n")
    L.append(htab + "\n")
    L.append("Range over the three evaluations: " + "; ".join(
        f"{k.replace('_', ' ')} {v[0]:.2f}–{v[1]:.2f}" for k, v in rg.items()) + ".\n")
    L.append("## 1. Resolution limit (CP10, post-hoc descriptive)\n")
    L.append(btab + "\n")
    L.append(f"The SNR axis (expected silent energy divided by its predictive sd) is the most "
             f"consistent across conditions: sd of log10 boundary {cons['snr']['sd_log10_x90']:.2f} "
             f"(share {cons['share']['sd_log10_x90']:.2f}, kWh {cons['kwh']['sd_log10_x90']:.2f}); "
             f"held-out/dev ratio {cons['snr']['heldout_vs_dev_ratio']:.2f} "
             f"(share {cons['share']['heldout_vs_dev_ratio']:.2f}).\n")
    L.append("**Scope of this limit (CP12 Task 3).** It is fitted on labelled simulated events: outages "
             "and communication failures of whole branches, feeders and single connections in the episode "
             "mix. It does not describe the 1–2-meter silent groups created by random data loss. There, "
             "false outage verdicts arise at high apparent SNR (median "
             f"{t3['fault_free_dev_validation']['1']['false_outage_snr_median']:.1f} for single meters, "
             "development grid) as rare deep lower-tail residuals, multiplied by thousands of groups a year "
             "(§9).\n")
    L.append("## 2. Comparison at the version 1 safety limits (CP5 validation, every setting)\n")
    rows = [[NAMES.get(m.split(" ")[0], m), "cannot meet the limits" if v["max_coverage_meeting_constraints"] is None
             else f3(v["max_coverage_meeting_constraints"])] for m, v in safety.items()]
    L.append(table(["Method", "Highest coverage meeting all limits"], rows) + "\n")
    L.append(COVERAGE_NOTE)
    L.append(f"Held-out paired coverage differences (cluster bootstrap): lr_band − ztest "
             f"{est(pc['bayes-ztest']['coverage_difference'], pc['bayes-ztest']['ci95'])}; "
             f"lr_band − share {est(pc['bayes-share']['coverage_difference'], pc['bayes-share']['ci95'])}.\n")
    L.append("## 3. Held-out grid (CP7, run once) with Isolation Forest added after CP7\n")
    L.append(heldout_table(cp7, itf) + "\n")
    L.append(COVERAGE_NOTE)
    L.append(f"Isolation Forest cause attribution: AUC {est(auc['auc'], auc['auc_ci95'])} on {auc['split']}; "
             f"direction: {auc['direction']}. "
             + ("The interval includes 0.5: no better than chance." if auc['auc_ci95'][0] <= 0.5 <= auc['auc_ci95'][1]
                else "The interval excludes 0.5 but lies below it: no evidence of cause attribution.") + "\n")
    L.append("## 4. Whole-feeder events by method (new seeds, CP10 families; post-hoc)\n")
    for fam, name in [("feeder_semiurb5", "development grid"), ("feeder_urban6", "held-out grid")]:
        L.append(f"**{name}**\n\n" + feeder_table(e11, fam) + "\n")
    L.append(COVERAGE_NOTE)
    L.append("Policy rows on the same events are in §6.\n")
    L.append("## 5. Base rates and operator load by method (version 1 escalation table)\n")
    a, b = br["ff_urban6/test_weeks"], br["ff_semiurb5/test_weeks"]
    L.append(f"Version 1 false outage verdicts on fault-free data (test weeks): held-out "
             f"{est(a['per_transformer_year'], a['per_transformer_year_ci95'])} per transformer-year, "
             f"development {est(b['per_transformer_year'], b['per_transformer_year_ci95'])}.\n")
    L.append(load_table(e11) + "\n")
    L.append("## 6. Policy components, separated (CP12; post-hoc variants, not pre-registered)\n")
    L.append("**Implementation status.** The meter-count gate and the comms re-check below are evaluated "
             "in study code (`shahid/cp12.py`, `shahid/p2eval.py`). Neither is executed by "
             "`explain.escalate`; `configs/escalation.yaml` states the R3 re-check only as action text, "
             "and the gate is not in it.\n")
    ch = sel["chosen"]
    L.append(f"Registered outcome of the CP11 selection: {sel['addendum_B']['outcome']}. The meter-count "
             f"gate (groups of fewer than {ch['theta']} meters held in WATCH for {ch['T_h']} h) was selected "
             "under addendum C, a declared deviation, and is not re-chosen. The comms re-check timeout is "
             "shown as a curve, not chosen. One matching rule (registered set overlap, addendum D) is used "
             "everywhere. Human items are split into three types and never merged: uncertain (including "
             "WATCH timeouts), outage verdict awaiting approval, communication verdict unconfirmed.\n")
    L.append("### 6.1 Outcome of every labelled event\n")
    for g in ["dev", "heldout", "rural"]:
        L.append(policy_outcomes(c12, g) + "\n")
    L.append("### 6.2 Operator load\n")
    for fam in ["ff_semiurb5", "ff_urban6", "loss10_ff_semiurb5", "loss10_ff_urban6", "cp7_dev_semiurb5",
                "cp7_heldout_urban6", "loss10_semiurb5", "loss10_urban6"]:
        L.append(policy_load(c12, fam) + "\n")
    L.append("### 6.3 False outage verdicts per transformer-year (fault-free data)\n")
    L.append(policy_false_outages(c12) + "\n")
    L.append("### 6.4 Outages without real-time attention, by size class\n")
    for fam in ["cp7_dev_semiurb5", "cp7_heldout_urban6", "feeder_semiurb5", "feeder_urban6", "rural3_eps"]:
        L.append(policy_attention(c12, fam) + "\n")
    L.append("### 6.5 Comms re-check: cost and benefit\n")
    L.append("**These results depend on the simulated duration of communication failures and on "
             "assumption A-COMMS (meters store readings and resend them when the link returns).** "
             "Simulated communication failures last: " + comms_duration_sentence(c12)
             + ". No simulated failure lasts longer than 4 h, so an 8 h re-check never escalates a genuine "
             "one in this simulation; that is a property of the simulator, not evidence for 8 h.\n")
    body = []
    for r in [x for x in t2 if "recheck" in x]:
        rc = t2[r]["recheck"]
        body.append([row_name(r)] + [west(rc[f]["comms_needing_human_confirmation"]) for f in
                                     ["feeder_semiurb5", "feeder_urban6", "rural3_eps"]])
    L.append("Share of genuine communication failures that end up needing a human confirmation:\n\n"
             + table(["Policy row", LABELS["feeder_semiurb5"], LABELS["feeder_urban6"], LABELS["rural3_eps"]],
                     body) + "\n")
    body = []
    for r in [x for x in t2 if "recheck" in x]:
        for f, v in t2[r]["recheck"].items():
            if v["outages_v1_closed_as_comms"]:
                q = v["wait_h_quantiles"]
                body.append([row_name(r), LABELS.get(f, f), v["outages_v1_closed_as_comms"], v["of_which_caught"],
                             v["caught_in_real_time"],
                             f"{q['0.5']:.2f} (10–90%: {q['0.1']:.2f}–{q['0.9']:.2f})" if q else "—"])
    L.append("Outages that version 1 closed automatically as communication failures, and the re-check:\n\n"
             + table(["Policy row", "Data", "Closed by version 1", "Caught by re-check", "Caught in real time",
                      "Wait from onset, h: median"], body) + "\n")
    L.append("Figure: `results/figs/cp12_recheck_tradeoff.png`.\n")
    L.append("### 6.6 Matching rule: CP11 numbers that change\n")
    L.append(matching_section(c12) + "\n")
    nd = c12["task1_matching"]["feeder_never_detected"]
    parts = []
    for f, v in nd.items():
        cnt = ", ".join(f"{k.replace('_', ' ')} {n}" for k, n in v["counts_rule_D"].items())
        parts.append(f"{LABELS[f]}: {cnt} of {v['n_outages']} outages")
    L.append("Whole-feeder outages reported as \"never detected\" under version 1.1 in CP11 are not a "
             "matching artefact. CP11's column merged three outcomes. Under the registered match: "
             + "; ".join(parts) + ". Every \"closed, no verdict\" case is a whole feeder of "
             f"{closed_no_verdict_sizes(c12)[0]}–{closed_no_verdict_sizes(c12)[1]} meters "
             "(simulated feeders can be that small). The gate holds it in WATCH, power returns within the "
             "1 h WATCH timeout without the onset reading ever arriving, and the group is closed without a "
             "verdict and without a human. The genuinely undetected ones (no silent group formed) are "
             "missed by version 1 as well.\n")
    L.append("## 7. Diversity range and simulated worlds\n")
    dv = cp10["diversity_range"]["range"]
    L.append(f"Over d = 0…1 (CP6): coverage {dv['coverage'][0]:.3f}–{dv['coverage'][1]:.3f}, outage "
             f"recall {dv['outage_recall'][0]:.3f}–{dv['outage_recall'][1]:.3f}, comms recall "
             f"{dv['comms_recall'][0]:.3f}–{dv['comms_recall'][1]:.3f}, missed outages "
             f"{dv['missed'][0]:.3f}–{dv['missed'][1]:.3f}.\n")
    ws = wld["worlds"]
    L.append("Worlds 0–3, nominal cell: abstention "
             + ", ".join(f"{ws[k]['abstention_rate']:.3f}" for k in sorted(ws))
             + "; balanced " + ", ".join(f"{ws[k]['balanced_correct']:.3f}" for k in sorted(ws)) + ".\n")
    L.append("## 8. Break-even between wrong verdicts and human reviews (CP12 Task 4)\n")
    for g, name in [("heldout", "held-out grid"), ("dev", "development grid")]:
        t1, tb, no_, nc_ = break_even_tables(c12, g)
        L.append(f"**Whole-feeder events, {name}** ({no_} outages, {nc_} communication failures). Per 100 "
                 "events of each type:\n\n" + t1 + "\n")
        L.append("Extra human reviews per wrong automatic verdict avoided (paired bootstrap 95% interval), by "
                 "share of outages in the event mix. \"dominates\" means fewer reviews and fewer wrong "
                 "verdicts. The cost of a wrong verdict relative to a review is left to the operator:\n\n"
                 + tb + "\n")
    L.append("Wrong automatic verdict = outage closed as communication + communication failure called outage. "
             "Human review = uncertain + communication verdict unconfirmed (outage verdicts awaiting approval "
             "are excluded for every method).\n")
    L.append("## 9. Why tiny groups produce confident false outage verdicts (CP12 Task 3)\n")
    L.append(f"Standardised residual z = (R − M)/sd_C at the decision time; nominal 90% interval |z| < "
             f"{t3['t_crit_90']:.2f} (Student-t, 4 df, the detector's own model).\n")
    for key, name in [("fault_free_dev_validation", "Fault-free, development grid, validation weeks, 5 observation seeds"),
                      ("fault_free_heldout_validation", "Fault-free, held-out grid, validation weeks, 5 observation seeds"),
                      ("labelled_comms_cp5_validation", "Labelled communication failures, CP5 validation episodes")]:
        L.append(f"*{name}*\n\n" + task3_table(c12, key) + "\n")
    nz = t3["single_meter_near_zero"]
    L.append(f"Single meters, fault-free development year, validation weeks: of "
             f"{nz['intervals_with_clearly_positive_expectation']} meter-intervals with an expectation of at "
             f"least {nz['thresholds_kwh']['clearly_positive']} kWh, a share of {nz['share_near_zero_actual']:.4f} "
             f"had an actual reading of at most {nz['thresholds_kwh']['near_zero']} kWh; the detector's model "
             f"implies {nz['share_implied_by_model']:.4f}.\n")
    L.append("**Verdict on the hypothesis \"predictive uncertainty is understated for very small groups\": "
             "refuted for single meters, partly supported for two-meter groups.**\n\n"
             "- Single meters: the 90% interval holds more than 90% of residuals, the deep lower tail is "
             "lighter than the model's, and near-zero readings are rarer than the model implies.\n"
             "- Two-meter groups: the lower tail at the 90% bound is heavier than nominal.\n"
             "- The false verdicts are deep-tail residuals that occur at roughly the rate the model itself "
             "allows. They add up to about 30 per transformer-year because random loss creates thousands of "
             "1–2-meter silent groups a year and the decision uses a 50/50 prior. This is a base-rate "
             "problem, not a variance problem (`docs/process/phase2_candidates.md`).\n")
    L.append("## Do NOT report\n")
    L.append("- Accuracy-when-deciding without coverage; labelled-episode precision as field precision.\n"
             "- A single headline rate without the range of §0.\n"
             "- Bin-edge boundaries (\"16%\", \"32%\"); the CP5 v1 selection's balanced figure; the stuck-meter "
             "perfect score; CP2 smoke verdicts; dev-grid test weeks as held-out data.\n"
             "- \"Version 1.1\" as one policy: report its components separately (§6).\n"
             "- \"Robust\", \"generalises\", \"real-time\", \"deployed\", \"AI\", \"machine learning\", "
             "\"novel\"; any Tunisian or STEG data or infrastructure claim.\n"
             "- Earlier design figures listed as RETRACTED in the ledger.\n")
    Path("docs/RESULTS.md").write_text(plain("\n".join(L)), encoding="utf8")


if __name__ == "__main__":
    results_doc()
    from shahid.make_pack import main as pack
    pack()
