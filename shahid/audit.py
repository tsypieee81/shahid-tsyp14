"""Audit analysis from existing result files only (no simulation, no tuning).

1. Same-episode comparison of every method with coverage = 1 - abstention next to every metric
   (CP5 validation at frozen thresholds, CP6 nominal, CP7 held-out and dev-test).
2. Risk-coverage tradeoff from the CP5 validation threshold sweeps (all settings, not only chosen).
3. Detectability boundary from CP6 episode files: by silent-energy share and by silent-meter count,
   for the nominal cell and for diversity / noise / transformer-meter / unmetered cells.
4. Unmetered-energy sensitivity incl. calibration (Brier score of P(comms)).
Run: python -m shahid.audit   (writes results/audit.json, results/figs/audit_*.png)
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from shahid import evaluate  # noqa: E402
from shahid.cp5_compare import primary_method  # noqa: E402
from shahid.figures import COLORS  # noqa: E402
from shahid.stamp import stamp, write_json  # noqa: E402

METHODS = ["bayes", "lr", "share", "ztest", "naive", "step", "count", "structure"]
BINS = [0, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 1.0]
SIZE_BINS = [0, 1, 2, 5, 10, 20, 40]
KEYS = ["n_outage", "n_comms", "coverage", "accuracy_when_decided", "outage_recall",
        "comms_recall", "false_outage_rate", "missed_outage_rate", "balanced_correct"]


def with_coverage(r):
    r = dict(r)
    r["coverage"] = 1 - r["abstention_rate"]
    return {k: r[k] for k in KEYS} | {k: r[k] for k in r if "fault_free" in k and "ci" not in k}


def tables():
    cp5 = json.load(open("results/cp5_compare.json"))["results_val"]
    cp7 = json.load(open("results/cp7_heldout.json"))["targets"]
    cp6 = {m: r for m, r in json.load(open("results/cp6/nominal.json"))["methods"].items()}
    return {"cp5_validation": {m: with_coverage(cp5[m]) for m in METHODS},
            "cp6_nominal": {m: with_coverage(cp6[m]) for m in METHODS},
            "cp7_heldout_urban6": {m: with_coverage(cp7["heldout_urban6"]["results"][m]) for m in METHODS},
            "cp7_dev_semiurb5_test": {m: with_coverage(cp7["dev_semiurb5"]["results"][m]) for m in METHODS}}


def risk_coverage():
    """Every swept threshold setting on CP5 validation: coverage vs errors."""
    r = json.load(open("results/cp5_compare.json"))["results_val"]
    out = {}
    for m in ["bayes", "lr", "share", "ztest"]:
        out[m] = [{"setting": {k: s[k] for k in s if k in ("abstain_band", "llr_threshold",
                                                           "share_threshold", "z_crit",
                                                           "min_expected_kwh")},
                   "coverage": 1 - s["abstention_rate"],
                   "selective_risk": 1 - s["accuracy_when_decided"]
                   if s["accuracy_when_decided"] == s["accuracy_when_decided"] else None,
                   "false_outage_rate": s["false_outage_rate"],
                   "missed_outage_rate": s["missed_outage_rate"],
                   "balanced_correct": s["balanced_correct"],
                   "fault_free_per_meter_day": s["fault_free_false_outage_per_meter_day"]}
                  for s in r[m]["sweep"]]
    for b in ["naive", "step", "count", "structure"]:
        s = r[b]
        out[b] = [{"coverage": 1 - s["abstention_rate"],
                   "selective_risk": 1 - s["accuracy_when_decided"],
                   "false_outage_rate": s["false_outage_rate"],
                   "missed_outage_rate": s["missed_outage_rate"],
                   "balanced_correct": s["balanced_correct"],
                   "fault_free_per_meter_day": s["fault_free_false_outage_per_meter_day"]}]
    return out


def binned(t, col, bins):
    rows = []
    for k, g in t.groupby(pd.cut(t[col], bins), observed=True):
        n = len(g)
        ok = int((g.verdict == g.cause).sum())
        wrong = int(((g.verdict != g.cause) & (g.verdict != "UNCERTAIN")).sum())
        rows.append({"bin": str(k), "lo": float(k.left), "hi": float(k.right), "n": n,
                     "correct": ok / n, "correct_ci95": evaluate.wilson(ok, n),
                     "wrong": wrong / n, "wrong_ci95": evaluate.wilson(wrong, n),
                     "abstain": float((g.verdict == "UNCERTAIN").mean())})
    return rows


def boundary(rows, need=0.9, max_wrong=0.02):
    """Smallest bin edge above which every bin is correct >= need with wrong <= max_wrong."""
    edge = None
    for r in reversed(rows):
        if r["correct"] >= need and r["wrong"] <= max_wrong:
            edge = r["lo"]
        else:
            break
    return edge


def detectability(primary):
    out = {}
    for f in sorted(Path("results/cp6").glob("*_episodes.parquet")):
        cell = f.stem.replace("_episodes", "")
        t = pd.read_parquet(f)
        frac = t[t.method == primary].set_index(["seed", "episode_id"]).silent_load_fraction.abs()
        t = t.join(frac.rename("frac"), on=["seed", "episode_id"])
        b = t[t.method == primary]
        out[cell] = {"by_share": binned(b.dropna(subset=["frac"]), "frac", BINS),
                     "by_meters": binned(b, "n_meters", SIZE_BINS),
                     "unbinned_missed_groups": int(b.frac.isna().sum())}
        out[cell]["boundary_share"] = boundary(out[cell]["by_share"])
        p = b.dropna(subset=["p_comms"])
        out[cell]["brier"] = float(((p.p_comms - (p.cause == "COMMS_FAILURE")) ** 2).mean())
        out[cell]["n_with_probability"] = len(p)
        n = {m: t[t.method == m] for m in ["naive"]}
        out[cell]["naive_by_share"] = binned(n["naive"].dropna(subset=["frac"]), "frac", BINS)
    return out


def figures(tab, rc, det, primary):
    out = Path("results/figs")
    # 1. risk-coverage (CP5 validation sweeps)
    fig, ax = plt.subplots(1, 3, figsize=(14, 3.9))
    for m, pts in rc.items():
        cov = [p["coverage"] for p in pts]
        mk = "o" if m in ("bayes", "lr", "share", "ztest") else "s"
        kw = dict(color=COLORS[m], label=m, ls="none", marker=mk, ms=4 if mk == "o" else 8)
        ax[0].plot(cov, [p["selective_risk"] for p in pts], **kw)
        ax[1].plot(cov, [p["false_outage_rate"] for p in pts], **kw)
        ax[2].plot(cov, [p["missed_outage_rate"] for p in pts], **kw)
    for a, y in zip(ax, ["error rate when deciding", "false-outage rate (comms called outage)",
                         "missed-outage rate"]):
        a.set(xlabel="coverage = 1 - abstention", ylabel=y, xlim=(0, 1.02), ylim=(0, None))
    ax[0].legend(frameon=False, fontsize=8, ncol=2)
    fig.suptitle("Coverage vs errors, every threshold setting swept on CP5 validation weeks", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "audit_risk_coverage.png", dpi=150)
    # 2. publication detectability figure: stacked outcome by silent share (nominal) + cells
    nom = det["nominal"]["by_share"]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    x = np.arange(len(nom))
    c = np.array([r["correct"] for r in nom]); w = np.array([r["wrong"] for r in nom])
    a = np.array([r["abstain"] for r in nom])
    ax[0].bar(x, c, color="#1f6fb4", label="correct cause")
    ax[0].bar(x, a, bottom=c, color="#cccccc", label="abstained (to human)")
    ax[0].bar(x, w, bottom=c + a, color="#c44e52", label="wrong cause")
    ax[0].set_xticks(x, [f"{r['lo']*100:g}–{r['hi']*100:g}%\nn={r['n']}" for r in nom], fontsize=8)
    ax[0].set(ylabel="share of episodes", ylim=(0, 1),
              xlabel="silent customers' expected energy / typical transformer energy",
              title=f"Detectability, nominal ({primary}, frozen thresholds)")
    ax[0].legend(frameon=False, fontsize=8, loc="upper left")
    for cell, col in [("diversity_0.0", "#7fb3e0"), ("nominal", "#1f6fb4"),
                      ("diversity_1.0", "#0b3c66"), ("tmeter_gain_0.02", "#d9822b"),
                      ("unmetered_profile_5.0kw", "#c44e52"), ("meter_noise_x10", "#3a9a4a")]:
        if cell in det:
            rows = det[cell]["by_share"]
            ax[1].plot([np.sqrt(r["lo"] * r["hi"]) if r["lo"] > 0 else r["hi"] / 2 for r in rows],
                       [r["correct"] for r in rows], "o-", color=col, label=cell, ms=4)
    ax[1].set(xscale="log", ylim=(0, 1.02), ylabel="correct-cause rate",
              xlabel="silent customers' expected energy / typical transformer energy",
              title="Boundary shifts with the assumptions")
    ax[1].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(out / "audit_detectability.png", dpi=150)


def main():
    primary = primary_method()
    tab, rc, det = tables(), risk_coverage(), detectability(primary)
    unmet = {c: {"brier": det[c]["brier"], "boundary_share": det[c]["boundary_share"]}
             for c in det if c.startswith("unmetered") or c == "nominal"}
    cells = {c: json.load(open(f"results/cp6/{c}.json"))["methods"][primary]
             for c in unmet}
    for c in unmet:
        r = cells[c]
        unmet[c].update({"coverage": 1 - r["abstention_rate"],
                         "false_outage_rate": r["false_outage_rate"],
                         "missed_outage_rate": r["missed_outage_rate"],
                         "accuracy_when_decided": r["accuracy_when_decided"]})
    figures(tab, rc, det, primary)
    write_json("results/audit.json", {"stamp": stamp({"bins": BINS, "size_bins": SIZE_BINS},
                                                     "python -m shahid.audit"),
                                      "primary": primary, "same_episode_tables": tab,
                                      "risk_coverage_cp5": rc, "detectability": det,
                                      "unmetered_sensitivity": unmet})
    for name, t in tab.items():
        print("==", name)
        for m, r in t.items():
            print(f"  {m:9s}", " ".join(f"{k[:12]}={r[k]:.3f}" for k in KEYS[2:]),
                  f"ff={r.get('fault_free_false_outage_per_meter_day', float('nan')):.4f}")
    print("boundaries", {c: d["boundary_share"] for c, d in det.items()})
    print("unmetered", json.dumps(unmet, indent=0))


if __name__ == "__main__":
    main()
