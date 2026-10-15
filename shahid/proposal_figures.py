"""Tooling: the proposal's data figures as vector PDF at final print size (proposal/figures/).

Same data and computations as the pack figures (shahid/make_pack.py, fig_day, fig_feeder, fig_snr,
fig_unmetered) and the classifier figure (shahid/classifier_study.py, figures); only size, fonts,
colours and labels differ. Reads result files; the example day re-runs the same deterministic
simulation (seed 301) as make_pack.fig_day. The pack PNGs in results/figs/ are not touched.

Run: python -m shahid.proposal_figures
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

from shahid.make_docs import J, METHODS  # noqa: E402

OUT = Path("proposal/figures")
COLW, FULLW = 3.5, 7.16  # IEEEtran column and text width, inches
plt.rcParams.update({"font.family": "STIXGeneral", "mathtext.fontset": "stix", "font.size": 8,
                     "axes.titlesize": 8, "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
                     "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42,
                     "savefig.bbox": "tight", "savefig.pad_inches": 0.02})
SHORT = {"bayes": "SHAHID v1", "ztest": "z-test variant", "lr": "single-threshold LR",
         "share": "share threshold", "naive": "naive", "step": "step", "count": "count",
         "structure": "structure", "iforest": "Isolation Forest"}
BLUE, ORANGE, RED, GREY = "#1f6fb4", "#d9822b", "#c44e52", "#7f7f7f"


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.pdf", metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)


def fig_day():
    """make_pack.fig_day: one held-out test-week day with a decided outage of at least 10 meters."""
    from shahid import scenario
    from shahid.cp5_compare import inputs_of
    from shahid.detect import arrays
    cfg = scenario.merge(scenario.load_cfg("configs/cp5_episodes.yaml"),
                         {"seed": 301, "world": {"grid": "1-LV-urban6--0-sw"}})
    index, meters, E, A, T = arrays(inputs_of(scenario.simulate(cfg)))
    ep = pd.read_parquet("results/records/cp7_heldout_urban6__episodes.parquet")
    ep = ep[(ep.method == "bayes") & (ep.seed == 301) & (ep.week == 3) & (ep.cause == "OUTAGE")
            & (ep.verdict == "OUTAGE") & (ep.n_meters >= 10)].sort_values("start")
    e = ep.iloc[0]
    t0 = int((e.start - pd.Timestamp("2016-01-01")) / pd.Timedelta(minutes=15))
    d0 = t0 // 96 * 96
    w = np.arange(d0, d0 + 96)
    ontime = np.where(A[w] <= np.arange(len(w))[:, None] + d0 + 1, E[w], np.nan)
    fig, ax = plt.subplots(figsize=(FULLW, 2.3))
    ax.plot(index[w], T[w], label="transformer energy", color=BLUE)
    ax.plot(index[w], np.nansum(ontime, 1), label="sum of meters that reported on time", color=ORANGE)
    ax.axvspan(e.start, e.end, color=RED, alpha=0.15, label=f"outage of {e.n_meters} meters (truth)")
    ax.axvline(e.start + pd.Timedelta(minutes=15 * e.latency_intervals), color="k", lw=0.8, ls="--",
               label=f"verdict OUTAGE after {e.latency_intervals:.0f} intervals")
    ax.set(ylabel="kWh per 15 min", xlabel=f"time of day, {e.start.date()} (held-out grid, seed 301)")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=4, borderaxespad=0.2)
    save(fig, "example_day")


def fig_feeder():
    """make_pack.fig_feeder: outcome shares by method, whole-feeder events, held-out grid."""
    fo = J("cp11_eval.json")["task1_feeder_outcomes"]["feeder_urban6"]
    ms = [m for m in METHODS + ["iforest"] if m in fo]
    fig, axes = plt.subplots(1, 2, figsize=(FULLW, 2.5), sharey=True)
    for ax, cause, keys, title in [
            (axes[0], "outage", ["correct", "abstained", "called_comms", "never_detected"], "feeder-level outages"),
            (axes[1], "comms", ["correct", "abstained", "called_outage", "never_detected"],
             "feeder-level communication failures")]:
        bottom = np.zeros(len(ms))
        for k, c in zip(keys, [BLUE, "#cccccc", RED, GREY]):
            v = np.array([fo[m][cause][k]["rate"] or 0 for m in ms])
            ax.bar(range(len(ms)), v, bottom=bottom, color=c, label=k.replace("_", " "))
            bottom += v
        ax.set_xticks(range(len(ms)), [SHORT[m] for m in ms], rotation=40, ha="right")
        ax.set_title(title, pad=2)
    axes[0].set_ylabel("share of events")
    for ax, last in zip(axes, ["called comms", "called outage"]):
        h, lab = ax.get_legend_handles_labels()
        ax.legend(h, lab, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.07), ncol=4,
                  fontsize=6.5, handlelength=1, columnspacing=0.8)
    save(fig, "feeder_outcomes")


def fig_snr():
    """make_pack.fig_snr: P(correct cause) against expected silent energy / predictive sd."""
    fig, ax = plt.subplots(figsize=(COLW, 2.5))
    for fam, weeks, col, lab in [("cp6_nominal", [0, 1, 2], BLUE, "development grid"),
                                 ("cp7_heldout_urban6", [3], ORANGE, "held-out grid")]:
        t = pd.read_parquet(f"results/records/{fam}__episodes.parquet")
        t = t[(t.method == "bayes") & t.week.isin(weeks)].dropna(subset=["M"])
        sd = np.sqrt(np.clip(t.sd_C ** 2 - t.sd_O ** 2, 0, None))
        x = (t.M.abs() / sd).to_numpy(float)
        y = (t.verdict == t.cause).to_numpy().astype(int)
        ok = np.isfinite(x) & (x > 0)
        q = np.quantile(x[ok], np.linspace(0, 1, 9))
        for lo, hi in zip(q[:-1], q[1:]):
            m = ok & (x >= lo) & (x <= hi)
            ax.plot(np.sqrt(lo * hi), y[m].mean(), "o", color=col, ms=3)
        lr = LogisticRegression(C=1e6).fit(np.log(x[ok]).reshape(-1, 1), y[ok])
        xs = np.logspace(np.log10(x[ok].min()), np.log10(x[ok].max()), 200)
        ax.plot(xs, lr.predict_proba(np.log(xs).reshape(-1, 1))[:, 1], color=col, label=lab)
    ax.axhline(0.9, color="k", lw=0.6, ls=":")
    ax.set(xscale="log", ylim=(0, 1.02), xlabel="expected silent energy / its predictive sd",
           ylabel="P(correct cause)")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "snr_detectability")


def fig_unmetered():
    """make_pack.fig_unmetered: rates against load-shaped unmetered energy (development grid)."""
    u = J("audit.json")["unmetered_sensitivity"]
    kws = [1.0, 2.0, 3.0, 5.0, 10.0]
    get = lambda kw, k: u[f"unmetered_profile_{kw}kw"][k]
    fig, ax = plt.subplots(figsize=(COLW, 2.4))
    ax.plot([0] + kws, [u["nominal"]["missed_outage_rate"]] + [get(k, "missed_outage_rate") for k in kws],
            "o-", color=RED, ms=3, label="missed outages")
    ax.plot([0] + kws, [u["nominal"]["false_outage_rate"]] + [get(k, "false_outage_rate") for k in kws],
            "s-", color=ORANGE, ms=3, label="false outages")
    ax.plot([0] + kws, [1 - u["nominal"]["coverage"]] + [1 - get(k, "coverage") for k in kws],
            "^-", color=GREY, ms=3, label="abstention")
    ax.axhline(0.05, color="k", lw=0.6, ls=":")
    ax.set(xlabel="load-shaped unmetered energy, mean kW (assumption)", ylabel="rate")
    ax.legend(frameon=False)
    save(fig, "unmetered_failure")


def fig_classifier():
    """classifier_study.figures (coverage_vs_safety): held-out urban test weeks."""
    res = json.load(open("results/studies/classifier_comparison/summary.json", encoding="utf8"))
    fig, ax = plt.subplots(figsize=(COLW, 2.6))
    err = lambda m: m["false_outage_rate"]["rate"] + m["missed_outage_rate"]["rate"]
    for b, v in res["baselines"]["urban6"].items():
        ax.plot(v["coverage"], v["false_outage_rate"] + v["missed_outage_rate"], "s", color="#999999", ms=4)
        ax.annotate(b, (v["coverage"], v["false_outage_rate"] + v["missed_outage_rate"]), fontsize=6,
                    xytext=(-3, 3), textcoords="offset points", ha="right")
    cols = {"logistic_regression": BLUE, "gradient_boosting": ORANGE, "mlp": "#3a9a4a"}
    names = {"logistic_regression": "logistic regression", "gradient_boosting": "gradient boosting",
             "mlp": "neural network"}
    for key, m in res["models"].items():
        name, fs = key.split("/")
        for s, r in m["seeds"].items():
            ax.plot(r["urban6"]["coverage"]["rate"], err(r["urban6"]), "o" if fs == "full" else "x",
                    color=cols[name], ms=4, label=f"{names[name]}{'' if fs == 'full' else ' (ablation)'}" if s == "0" else None)
    fz = res["frozen"]["urban6"]
    ax.plot(fz["coverage"]["rate"], err(fz), "k*", ms=9, label="SHAHID v1 (frozen)")
    ax.set(xlabel="coverage (decided / all events)", ylabel="false-outage + missed-outage rate", xlim=(0, 1.02))
    ax.legend(frameon=False, fontsize=6, loc="upper left")
    save(fig, "classifier_coverage_safety")


def main():
    for f in [fig_snr, fig_feeder, fig_unmetered, fig_classifier, fig_day]:
        f()
        print("written", f.__name__, flush=True)


if __name__ == "__main__":
    main()
