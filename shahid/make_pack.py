"""Generate docs/build/proposal_pack.md (not tracked) and six print-quality figures from result files (CP11 Task 4,
corrected in CP12 Task 6).

Run: python -m shahid.make_pack   (normally via python -m shahid.make_docs)
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

from shahid import evaluate  # noqa: E402
from shahid.check_numbers import allowlist_tags  # noqa: E402
from shahid.make_docs import (J, LABELS, METHODS, TYPES, anomaly_table,  # noqa: E402
                              assumptions_full, break_even_tables, closed_no_verdict_sizes, est, feeder_table, headline_table,
                              plain, policy_false_outages, policy_load, policy_outcomes, row_name, table)

FIG = Path("results/figs")
DPI = 300
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
COL = {"bayes": "#1f6fb4", "ztest": "#8e5ea2", "lr": "#d9822b", "share": "#3a9a4a",
       "naive": "#7f7f7f", "step": "#b5b5b5", "count": "#c44e52", "structure": "#e8a0a0",
       "iforest": "#000000"}
PACK_ROWS = ["v1", "v1+gate", "v1+recheck1h", "v1+recheck4h", "v1+gate+recheck1h", "v1+gate+recheck4h"]


def fig_snr():
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for fam, weeks, col, lab in [("cp6_nominal", [0, 1, 2], "#1f6fb4", "development grid (CP6 nominal)"),
                                 ("cp7_heldout_urban6", [3], "#d9822b", "held-out grid (CP7)")]:
        t = pd.read_parquet(f"results/records/{fam}__episodes.parquet")
        t = t[(t.method == "bayes") & t.week.isin(weeks)].dropna(subset=["M"])
        sd = np.sqrt(np.clip(t.sd_C ** 2 - t.sd_O ** 2, 0, None))
        x = (t.M.abs() / sd).to_numpy(float)
        y = (t.verdict == t.cause).to_numpy().astype(int)
        ok = np.isfinite(x) & (x > 0)
        q = np.quantile(x[ok], np.linspace(0, 1, 9))
        for lo, hi in zip(q[:-1], q[1:]):
            m = ok & (x >= lo) & (x <= hi)
            ax.plot(np.sqrt(lo * hi), y[m].mean(), "o", color=col, ms=4)
        lr = LogisticRegression(C=1e6).fit(np.log(x[ok]).reshape(-1, 1), y[ok])
        xs = np.logspace(np.log10(x[ok].min()), np.log10(x[ok].max()), 200)
        ax.plot(xs, lr.predict_proba(np.log(xs).reshape(-1, 1))[:, 1], color=col, label=lab)
    ax.axhline(0.9, color="k", lw=0.6, ls=":")
    ax.set(xscale="log", ylim=(0, 1.02), xlabel="signal-to-noise: expected silent energy / predictive sd",
           ylabel="P(correct cause)", title="Resolution limit (lr_band, version 1; simulated events)")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "pack_1_snr_detectability.png", dpi=DPI)


def fig_feeder(e11):
    fo = e11["task1_feeder_outcomes"]["feeder_urban6"]
    ms = [m for m in METHODS + ["iforest"] if m in fo]
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.4), sharey=True)
    for ax, cause, keys, cols in [
            (axes[0], "outage", ["correct", "abstained", "called_comms", "never_detected"],
             ["#1f6fb4", "#cccccc", "#c44e52", "#7f7f7f"]),
            (axes[1], "comms", ["correct", "abstained", "called_outage", "never_detected"],
             ["#1f6fb4", "#cccccc", "#c44e52", "#7f7f7f"])]:
        bottom = np.zeros(len(ms))
        for k, c in zip(keys, cols):
            v = np.array([fo[m][cause][k]["rate"] or 0 for m in ms])
            ax.bar(range(len(ms)), v, bottom=bottom, color=c, label=k.replace("_", " "))
            bottom += v
        ax.set_xticks(range(len(ms)), [m if m != "bayes" else "lr_band" for m in ms], rotation=45,
                      ha="right", fontsize=7)
        ax.set_title(f"whole-feeder {cause} events, held-out grid")
        ax.legend(frameon=False, fontsize=6)
    axes[0].set_ylabel("share of episodes")
    fig.tight_layout()
    fig.savefig(FIG / "pack_2_feeder_outcomes.png", dpi=DPI)


def fig_risk():
    rc = J("audit.json")["risk_coverage_cp5"]
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for m, pts in rc.items():
        mk = "o" if m in ("bayes", "lr", "share", "ztest") else "s"
        ax.plot([p["coverage"] for p in pts], [p["false_outage_rate"] + p["missed_outage_rate"] for p in pts],
                mk, color=COL[m], ms=3 if mk == "o" else 6, ls="none",
                label=m if m != "bayes" else "lr_band")
    ax.set(xlabel="coverage = 1 − abstention", ylabel="false-outage + missed-outage rate",
           title="Coverage vs safety errors (CP5 validation, all settings)", xlim=(0, 1.02))
    ax.legend(frameon=False, fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(FIG / "pack_3_risk_coverage.png", dpi=DPI)


def fig_load(c12):
    """Human items per transformer-day by type (never merged) for the separated policy rows."""
    t2 = c12["task2_components"]
    rows = ["v1", "v1+gate", "v1+recheck1h", "v1+gate+recheck1h"]
    fams = [("ff_urban6", "fault-free\n1% loss"), ("loss10_ff_urban6", "fault-free\n10% loss"),
            ("cp7_heldout_urban6", "events\n1% loss"), ("loss10_urban6", "events\n10% loss")]
    cols = {"uncertain": "#cccccc", "outage_awaiting_approval": "#c44e52", "comms_unconfirmed": "#1f6fb4"}
    w = 0.2
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    for i, r in enumerate(rows):
        bottom = np.zeros(len(fams))
        for k, name in TYPES:
            key = lambda f: next(x for x in t2[r]["load"] if x.endswith("/" + f))
            v = np.array([t2[r]["load"][key(f)][k]["per_day"] for f, _ in fams])
            ax.bar(np.arange(len(fams)) + i * w, v, w, bottom=bottom, color=cols[k], edgecolor="white",
                   lw=0.3, label=name if i == 0 else None)
            bottom += v
        for j, b in enumerate(bottom):
            ax.text(j + i * w, b, ["v1", "gate", "re-chk", "both"][i], ha="center", va="bottom", fontsize=5)
    ax.set_xticks(np.arange(len(fams)) + 1.5 * w, [n for _, n in fams])
    ax.set(yscale="symlog", ylabel="human items per transformer-day",
           title="Operator load by item type, held-out grid (re-check 1 h; post-hoc variants)")
    ax.legend(frameon=False, fontsize=6)
    fig.tight_layout()
    fig.savefig(FIG / "pack_4_operator_load.png", dpi=DPI)


def fig_day():
    """One held-out test-week day: transformer energy, on-time reporting-meter sum, verdicts."""
    from shahid import scenario
    from shahid.cp5_compare import inputs_of
    from shahid.detect import arrays
    cfg = scenario.merge(scenario.load_cfg("configs/cp5_episodes.yaml"),
                         {"seed": 301, "world": {"grid": "1-LV-urban6--0-sw"}})
    sim = scenario.simulate(cfg)
    index, meters, E, A, T = arrays(inputs_of(sim))
    ep = pd.read_parquet("results/records/cp7_heldout_urban6__episodes.parquet")
    ep = ep[(ep.method == "bayes") & (ep.seed == 301) & (ep.week == 3) & (ep.cause == "OUTAGE")
            & (ep.verdict == "OUTAGE") & (ep.n_meters >= 10)].sort_values("start")
    e = ep.iloc[0]
    t0 = int((e.start - pd.Timestamp("2016-01-01")) / pd.Timedelta(minutes=15))
    d0 = t0 // 96 * 96
    w = np.arange(d0, d0 + 96)
    ontime = np.where(A[w] <= np.arange(len(w))[:, None] + d0 + 1, E[w], np.nan)
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.plot(index[w], T[w], label="transformer energy (kWh per 15 min)", color="#1f6fb4")
    ax.plot(index[w], np.nansum(ontime, 1), label="sum of meters that reported on time",
            color="#d9822b")
    ax.axvspan(e.start, e.end, color="#c44e52", alpha=0.15, label=f"outage of {e.n_meters} meters")
    ax.axvline(e.start + pd.Timedelta(minutes=15 * e.latency_intervals), color="k", lw=0.8, ls="--",
               label=f"verdict OUTAGE after {e.latency_intervals:.0f} intervals")
    ax.set(ylabel="kWh per interval", title=f"Example held-out day {e.start.date()} (seed 301)")
    ax.legend(frameon=False, fontsize=6)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIG / "pack_5_example_day.png", dpi=DPI)
    return {"date": str(e.start.date()), "n_meters": int(e.n_meters),
            "latency": float(e.latency_intervals)}


def fig_unmetered():
    u = J("audit.json")["unmetered_sensitivity"]
    kws = [1.0, 2.0, 3.0, 5.0, 10.0]
    get = lambda kw, k: u[f"unmetered_profile_{kw}kw"][k]
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    ax.plot([0] + kws, [u["nominal"]["missed_outage_rate"]] + [get(k, "missed_outage_rate") for k in kws],
            "o-", color="#c44e52", label="missed outages")
    ax.plot([0] + kws, [u["nominal"]["false_outage_rate"]] + [get(k, "false_outage_rate") for k in kws],
            "s-", color="#d9822b", label="false outages")
    ax.plot([0] + kws, [1 - u["nominal"]["coverage"]] + [1 - get(k, "coverage") for k in kws],
            "^-", color="#7f7f7f", label="abstention")
    ax.axhline(0.05, color="k", lw=0.6, ls=":")
    ax.set(xlabel="load-shaped unmetered energy, mean kW (synthetic assumption)", ylabel="rate",
           title="Failure mode: load-proportional gap")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "pack_6_unmetered_failure.png", dpi=DPI)


def failure_table():
    rows = []
    for c in ["tmeter_gain_0.02", "unmetered_profile_5.0kw", "unmetered_profile_10.0kw",
              "hn_simultaneous_outage_comms", "hn_packet_loss_10pct", "hn_pv_midday"]:
        v = json.load(open(f"results/cp6/{c}.json"))["methods"]["bayes"]
        lo, hi = v["ci95"]["abstention_rate"]
        k_miss = round(v["missed_outage_rate"] * v["n_outage"])
        rows.append([LABELS[c], est(1 - v["abstention_rate"], [1 - hi, 1 - lo]),
                     est(v["false_outage_rate"], v["ci95"]["false_outage_rate"]),
                     est(v["missed_outage_rate"], evaluate.wilson(k_miss, v["n_outage"]))])
    return table(["Condition (development grid, CP6)", "Coverage", "False outage", "Missed outage"], rows)


def allowlist_footer():
    counts, _ = allowlist_tags()
    n = sum(counts.values())
    names = {"[date]": "dates", "[identifier]": "identifiers (seeds, status codes, a retracted figure)",
             "[parameter]": "parameters", "[environment]": "environment (versions, disk size)",
             "[derived]": "derived arithmetic on ledger values", "[count]": "counts of design or file sets"}
    parts = ", ".join(f"{counts[k]} {names[k]}" for k in names if counts[k])
    return (f"**Number integrity.** Every number in this pack matches a ledger entry or a cited result "
            f"file at its printed precision (`python -m shahid.check_numbers`, run as a test). {n} numbers "
            f"across all checked documents are allowlisted instead: {parts}. No measured result is on the "
            f"allowlist; the test fails if an entry lacks one of these category tags. **Limit:** the real "
            f"protection is that this pack is generated from result files. The checker catches most "
            f"errors of three or more digits but cannot catch a wrong two-decimal rate: under its "
            f"rounding tolerance every two-decimal number between 0 and 1 matches some ledger value "
            f"(ledger CHK-01).\n")


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    e11, cp10, c12 = J("cp11_eval.json"), J("cp10.json"), J("cp12.json")
    fig_snr()
    fig_feeder(e11)
    fig_risk()
    fig_load(c12)
    day = fig_day()
    fig_unmetered()
    b = cp10["boundary"]
    cons = cp10["boundary_axis_consistency"]
    t2 = c12["task2_components"]
    t3 = c12["task3_small_groups"]
    htab, rg = headline_table(c12)
    _, be, no_, nc_ = break_even_tables(c12, "heldout")
    rc = lambda r, f: t2[r]["recheck"][f]["comms_needing_human_confirmation"]["rate"]
    nv = t2["v1+gate"]["outcomes"]["heldout"]["outage"]["closed_no_verdict"]
    lo_n, hi_n = closed_no_verdict_sizes(c12, ("feeder_urban6",))
    g3 = table(["Policy row", "What happens without a human"], [
        [row_name("v1"), "Communication verdicts with p ≥ 0.95 on at most 40 meters are closed (rule R3). "
                         "Everything else goes to a human."],
        [row_name("v1+gate"), "As version 1, and a silent group of 1–2 meters is held for 1 h. It is closed as "
                              "communication if its first missing reading arrives late, or closed with no verdict "
                              f"if the meters come back without it. The latter loses {nv['k']} of {nv['n']} held-out "
                              "whole-feeder outages, " + (f"feeders of {lo_n}–{hi_n} meters." if lo_n != hi_n
                                                          else f"each a feeder with {lo_n} meter.")],
        [row_name("v1+recheck1h"), "A communication verdict is closed only when the stored reading of the first "
                                   f"silent interval arrives within 1 h; {rc('v1+recheck1h', 'feeder_urban6'):.2f} of "
                                   "genuine held-out feeder communication failures still go to a human."],
        [row_name("v1+recheck4h"), "As above with 4 h; the escalated share falls to "
                                   f"{rc('v1+recheck4h', 'feeder_urban6'):.2f}, but every catch comes after the "
                                   "simulated outage has ended."]])
    L = ["# SHAHID proposal pack (Phase 1)\n",
         "**Generated by `python -m shahid.make_docs` from result files; every number traces to "
         "`docs/CLAIMS_LEDGER.md`.** Sources: `results/cp7_heldout.json`, `results/cp10.json`, "
         "`results/cp11_eval.json`, `results/cp12.json`, `results/iforest.json`, `results/audit.json`, "
         "`results/cp6/*.json`. All data is simulated; read `docs/LIMITATIONS.md`. Estimates are printed "
         "with their 95% interval and rounded so that no value shows more digits than the interval "
         "supports.\n",
         "## Method in one paragraph\n",
         "When a group of smart meters under one transformer stops reporting, SHAHID asks whether the "
         "transformer still delivers the energy those customers would normally use. It predicts the "
         "group's energy from each meter's own same-time history (last 14 days) plus how far the group "
         "was from that history just before it went silent. It compares that prediction with what the "
         "transformer meter shows beyond the meters still reporting. Two hypotheses are scored with a "
         "Student-t likelihood ratio: the energy is still there (communication failure) or it is gone "
         "(outage). If the ratio is not decisive, the detector abstains and hands the case on. This is "
         "statistical inference with parameters fitted from fault-free history. There is no trained "
         "classifier and no neural network. A gradient-boosting forecaster of the expected energy was "
         "tested and brought no benefit at the nominal customer diversity; it was slightly better only "
         "when all customers share identical load shapes (ledger C4-06).\n",
         "## Goal coverage\n",
         table(["Goal", "IMPLEMENTED", "SIMULATED", "PROPOSED / not done"], [
             ["G1 detect and tell grid event from data problem",
              "silent-group diagnosis (outage vs comms vs uncertain), baselines, Isolation Forest",
              "all evaluation data", "single-meter bias, drift and noise are NOT detected (CP8)"],
             ["G2 confidence, explanation, decision log",
              "probability, template explanation tested to contain only record numbers, hash-chained log",
              "demo log", "explanation quality not evaluated with users; mid-range probabilities not shown "
                          "to be calibrated; one confident wrong case documented (a 7-meter outage called "
                          "a communication failure with probability 0.996, ledger C9-01)"],
             ["G3 what the system may do alone", "escalation table; meter-count gate and comms re-check as "
                                                 "separate options (post-hoc variants)",
              "operator load and outcome tables per policy row (below)", "not validated with operators"],
             ["G4 knowledge sharing across nodes", "—", "—", "design note only"]]) + "\n",
         "**G3 in detail: what each policy row does without a human.**\n\n" + g3 + "\n",
         "## Headline: frozen version 1 on three evaluations\n",
         htab + "\n",
         "Any headline sentence must quote the range: coverage "
         f"{rg['coverage'][0]:.2f}–{rg['coverage'][1]:.2f}, outage recall {rg['outage_recall'][0]:.2f}–"
         f"{rg['outage_recall'][1]:.2f}, communication recall {rg['comms_recall'][0]:.2f}–"
         f"{rg['comms_recall'][1]:.2f}, false-outage rate {rg['false_outage_rate'][0]:.2f}–"
         f"{rg['false_outage_rate'][1]:.2f}, missed-outage rate {rg['missed_outage_rate'][0]:.2f}–"
         f"{rg['missed_outage_rate'][1]:.2f} (development test weeks, held-out urban grid, untouched rural "
         "grid).\n",
         "## Whole-feeder events by method (held-out grid, new seeds, post-hoc)\n",
         feeder_table(e11, "feeder_urban6") + "\n",
         "## Policy rows on the same events (post-hoc variants, not pre-registered)\n",
         "Version 1 is the registered result. The other rows separate the two components of CP11's "
         "\"version 1.1\": the meter-count gate (fewer than 3 meters, 1 h WATCH, selected under a declared "
         "deviation) and the provisional communication re-check (timeouts 1–8 h, shown as a trade-off, "
         "not chosen; all timeouts in `docs/RESULTS.md` §6).\n",
         policy_outcomes(c12, "heldout", PACK_ROWS) + "\n",
         "The re-check numbers depend on the simulated duration of communication failures (1–4 h in "
         "every family) and on assumption A-COMMS (meters store and resend readings).\n",
         "## Resolution limit\n",
         "The detector is right with probability 0.90 once the silent group's expected energy is about "
         f"{est(b['cp6_nominal']['snr']['x90_logistic'], b['cp6_nominal']['snr']['x90_ci95'])} times its "
         "predictive standard deviation on the development grid, and "
         f"{est(b['cp7_heldout_urban6']['snr']['x90_logistic'], b['cp7_heldout_urban6']['snr']['x90_ci95'])} "
         "on the held-out grid. As an illustration in share of transformer energy over the decision window: "
         f"{est(b['cp6_nominal']['share']['x90_logistic'], b['cp6_nominal']['share']['x90_ci95'])} "
         "(development) and "
         f"{est(b['cp7_heldout_urban6']['share']['x90_logistic'], b['cp7_heldout_urban6']['share']['x90_ci95'])} "
         "(held-out). The signal-to-noise form is the more portable one (spread of log10 boundary across "
         f"conditions {cons['snr']['sd_log10_x90']:.2f} vs {cons['share']['sd_log10_x90']:.2f}). "
         "**Scope:** this limit is measured on simulated events (outages and communication failures of "
         "branches, feeders and single connections). It does not apply to the 1–2-meter silent groups "
         "that random data loss creates. There, false outage verdicts occur even at high apparent "
         f"signal-to-noise (median {t3['fault_free_dev_validation']['1']['false_outage_snr_median']:.1f} for "
         "single meters). They are rare deep-tail residuals multiplied by thousands of groups a year, a "
         "base-rate effect rather than understated uncertainty (CP12 Task 3).\n",
         "## Known failure modes (version 1, development grid)\n",
         failure_table() + "\n",
         "Load-shaped unmetered energy and transformer-meter gain error share one cause: the gap baseline "
         "is constant while both effects scale with load (CP10 Task 8).\n",
         "## Operator load and false outage verdicts per policy row (post-hoc variants)\n",
         "Human items are of three types and are never merged: uncertain (including WATCH timeouts), "
         "outage verdict awaiting approval, communication verdict unconfirmed.\n",
         policy_load(c12, "ff_urban6", PACK_ROWS) + "\n",
         policy_load(c12, "loss10_ff_urban6", PACK_ROWS) + "\n",
         policy_load(c12, "cp7_heldout_urban6", PACK_ROWS) + "\n",
         "False outage verdicts per transformer-year on fault-free data:\n\n"
         + policy_false_outages(c12, PACK_ROWS) + "\n",
         "## Safety versus human reviews\n",
         f"Held-out whole-feeder events ({no_} outages, {nc_} communication failures). Extra human reviews "
         "per wrong automatic verdict avoided, by share of outages in the event mix (paired bootstrap 95% "
         "interval). The cost of a wrong verdict relative to a review is the operator's choice:\n\n"
         + be + "\n",
         "## Assumptions\n", assumptions_full() + "\n",
         "## Anomaly generation\n", anomaly_table() + "\n",
         "## Figures\n",
         "1. `results/figs/pack_1_snr_detectability.png` — resolution limit on the signal-to-noise axis.\n"
         "2. `results/figs/pack_2_feeder_outcomes.png` — whole-feeder outcomes by method.\n"
         "3. `results/figs/pack_3_risk_coverage.png` — coverage vs safety errors.\n"
         "4. `results/figs/pack_4_operator_load.png` — operator load by item type per policy row.\n"
         f"5. `results/figs/pack_5_example_day.png` — example held-out day {day['date']}.\n"
         "6. `results/figs/pack_6_unmetered_failure.png` — load-shaped unmetered-energy failure.\n",
         allowlist_footer()]
    Path("docs/build").mkdir(parents=True, exist_ok=True)
    Path("docs/build/proposal_pack.md").write_text(plain("\n".join(L)), encoding="utf8")


if __name__ == "__main__":
    main()
