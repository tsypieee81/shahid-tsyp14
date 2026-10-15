"""Regenerate every figure from result files (no simulation). Run: python -m shahid.figures"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from shahid import evaluate  # noqa: E402

OUT = Path("results/figs")
COLORS = {"bayes": "#1f6fb4", "lr": "#d9822b", "share": "#3a9a4a", "ztest": "#8e5ea2",
          "naive": "#7f7f7f", "step": "#b5b5b5", "count": "#c44e52", "structure": "#e8a0a0",
          "median": "#7f7f7f", "mean": "#b5b5b5", "transfer": "#3a9a4a", "anchored": "#1f6fb4",
          "ratio": "#c44e52"}


def cp4():
    d = json.load(open("results/cp4_expected_load.json"))["by_d"]
    sizes = [1, 2, 5, 10, 20, 50]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for ax, dv in zip(axes, ["0.0", "0.5"]):
        for m in ["median", "mean", "transfer", "anchored"]:
            y = [d[dv][f"H14/random_{k}"]["val"][m]["rel_err_vs_group"] for k in sizes]
            ax.plot(sizes, y, "o-", label=m, color=COLORS[m])
        ax.set(xscale="log", xlabel="silent group size (meters)", title=f"diversity d = {dv}")
        ax.set_xticks(sizes, [str(s) for s in sizes])
    axes[0].set_ylabel("abs error / group energy (validation)")
    axes[1].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "cp4_expected_load.png", dpi=130)


def curve(ax, tab, col, bins, method, label=None):
    t = tab[tab.method == method].dropna(subset=[col])
    cut = pd.cut(t[col], bins)
    xs, ok, lo, hi, ab = [], [], [], [], []
    for k, g in t.groupby(cut, observed=True):
        if len(g) < 5:
            continue
        n_ok = int((g.verdict == g.cause).sum())
        w = evaluate.wilson(n_ok, len(g))
        xs.append(k.mid)
        ok.append(n_ok / len(g))
        lo.append(w[0])
        hi.append(w[1])
        ab.append(float((g.verdict == "UNCERTAIN").mean()))
    c = COLORS.get(method, "k")
    ax.plot(xs, ok, "o-", color=c, label=label or method)
    ax.fill_between(xs, lo, hi, color=c, alpha=0.15)
    return xs, ab


def cp6():
    p = Path("results/cp6/nominal_episodes.parquet")
    if not p.exists():
        return
    tab = pd.read_parquet(p)
    from shahid.cp5_compare import primary_method
    main_m = primary_method()
    bins = [0, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 1.0]
    fig, axes = plt.subplots(1, 3, figsize=(14, 3.9))
    # silent_load_fraction exists only for physics methods; use the primary method's value
    frac = tab[tab.method == main_m].set_index(["seed", "episode_id"]).silent_load_fraction
    tab = tab.join(frac.abs().rename("frac"), on=["seed", "episode_id"])
    xl = "|expected silent energy| / typical transformer energy"
    for m in [main_m, "naive", "step", "count"]:
        curve(axes[0], tab, "frac", bins, m)
        t = tab[tab.method == m].dropna(subset=["frac"])
        g = t.groupby(pd.cut(t.frac, bins), observed=True)
        mids = [k.mid for k, _ in g]
        wrong = [float(((x.verdict != x.cause) & (x.verdict != "UNCERTAIN")).mean()) for _, x in g]
        axes[1].plot(mids, wrong, "o-", color=COLORS[m], label=m)
        if m in (main_m, "naive"):
            axes[2].plot(mids, [float((x.verdict == "UNCERTAIN").mean()) for _, x in g], "o-",
                         color=COLORS[m], label=m)
    axes[0].set(xscale="log", xlabel=xl, ylabel="correct-cause rate (95% CI)", ylim=(0, 1),
                title="Correct cause")
    axes[1].set(xscale="log", xlabel=xl, ylabel="wrong-cause rate (incl. missed)", ylim=(0, 1),
                title="Wrong cause")
    axes[2].set(xscale="log", xlabel=xl, ylabel="abstention rate", ylim=(0, 1),
                title="Abstention (sent to a human)")
    for ax in axes:
        ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "cp6_detectability.png", dpi=130)
    # robustness summary across cells
    rows = []
    for f in sorted(Path("results/cp6").glob("*.json")):
        r = json.load(open(f))["methods"].get(main_m)
        if r:
            rows.append((f.stem, r["balanced_correct"], *r["ci95"]["balanced_correct"],
                         r["abstention_rate"], r["missed_outage_rate"]))
    if rows:
        df = pd.DataFrame(rows, columns=["cell", "bal", "lo", "hi", "abst", "miss"])
        fig, ax = plt.subplots(figsize=(8, 0.28 * len(df) + 1))
        y = np.arange(len(df))
        ax.errorbar(df.bal, y, xerr=[df.bal - df.lo, df.hi - df.bal], fmt="o", color=COLORS[main_m],
                    label="balanced correct-cause (95% CI)")
        ax.plot(df.abst, y, "s", color="#999", label="abstention")
        ax.plot(df.miss, y, "x", color="#c44e52", label="missed outage")
        ax.set_yticks(y, df.cell, fontsize=8)
        ax.set(xlim=(0, 1), title=f"Robustness cells ({main_m}, frozen thresholds)")
        ax.legend(frameon=False, fontsize=8, loc="lower right")
        fig.tight_layout()
        fig.savefig(OUT / "cp6_robustness.png", dpi=130)


def cp7():
    p = Path("results/cp7_heldout.json")
    if not p.exists():
        return
    d = json.load(open(p))["targets"]
    fig, ax = plt.subplots(figsize=(4.2, 4))
    for name, t in d.items():
        rel = t["results"].get("bayes", {}).get("reliability", [])
        if rel:
            ax.plot([r["mean_p"] for r in rel], [r["frac_comms"] for r in rel], "o-", label=name)
    ax.plot([0, 1], [0, 1], "k:", lw=1)
    ax.set(xlabel="predicted P(comms failure)", ylabel="observed fraction comms failure",
           title="Reliability (test weeks)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "cp7_reliability.png", dpi=130)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cp4()
    cp6()
    cp7()


if __name__ == "__main__":
    main()
