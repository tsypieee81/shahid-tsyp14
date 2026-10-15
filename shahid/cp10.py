"""CP10 analyses of the FROZEN version 1 method. Post-hoc descriptive analysis, added after CP7.

Reads results/records/* (shahid.records) and a few result files. Nothing is tuned.
Run: python -m shahid.cp10   (writes results/cp10.json and results/figs/cp10_*.png)
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from shahid import evaluate, explain, scenario  # noqa: E402
from shahid.cp5_compare import inputs_of  # noqa: E402
from shahid.detect import arrays  # noqa: E402
from shahid.stamp import stamp, write_json  # noqa: E402

REC = Path("results/records")
LABEL = "post-hoc descriptive analysis, added after CP7"
PRIMARY = "bayes"  # = lr_band (likelihood-ratio test with two-sided abstention band)
METHODS = ["bayes", "lr", "share", "ztest", "naive", "step", "count", "structure"]
SIZE_BINS = [0, 1, 2, 5, 10, 20, 40, 200]
RNG = np.random.default_rng(10)
BOOT = 500


def ep(fam):
    return pd.read_parquet(REC / f"{fam}__episodes.parquet")


def gr(fam):
    g = pd.read_parquet(REC / f"{fam}__groups.parquet")
    meta = g[g.method == "_meta"]
    days = {int(r.seed): float(r.verdict.split("=")[1]) for r in meta.itertuples()}
    return g[g.method != "_meta"], days


def cluster_boot(df, stat, n=BOOT):
    """Bootstrap over (seed, day) clusters; returns 95% interval of stat(df)."""
    key = df.seed.astype(str) + "_" + pd.to_datetime(df.start if "start" in df else df.onset).dt.date.astype(str)
    groups = {k: idx for k, idx in df.groupby(key).groups.items()}
    keys = list(groups)
    vals = []
    for _ in range(n):
        pick = RNG.choice(len(keys), len(keys), replace=True)
        sample = df.loc[np.concatenate([groups[keys[i]] for i in pick])]
        vals.append(stat(sample))
    vals = np.array(vals, float)
    vals = vals[np.isfinite(vals)]
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))] if len(vals) else [None, None]


# ------------------------------------------------------------------ Task 0: rule R3
def r3_harm():
    table = explain.load_escalation()
    out = {}
    fams = [f.name.split("__")[0] for f in REC.glob("*__episodes.parquet")]
    for fam in sorted(fams):
        t = ep(fam)
        b = t[(t.method == PRIMARY) & (t.cause == "OUTAGE")]
        if fam.startswith("cp7"):
            b = b[b.week == 3]
        elif fam == "cp5":
            b = b[b.week == 2]
        elif fam.startswith("cp6"):
            b = b[b.week != 3]
        auto = (b.verdict == "COMMS_FAILURE") & (b.p_comms >= 0.95) & (b.n_meters <= 40)
        out[fam] = {"outage_episodes": len(b), "outages_auto_closed_by_R3": int(auto.sum()),
                    "share": float(auto.mean()) if len(b) else None}
    _ = table
    return out


# ------------------------------------------------------------------ Task 1: operator load
TABLE = explain.load_escalation()


def route(v, p, n):
    rec = {"cause": v, "probability": None if p != p else (1 - p if v == "OUTAGE" else p),
           "evidence": {"n_meters": int(n)}}
    if v not in ("OUTAGE", "COMMS_FAILURE"):
        rec["probability"] = None
    return explain.escalate(rec, TABLE)


def operator_load(fams):
    out = {}
    for fam in fams:
        if not (REC / f"{fam}__groups.parquet").exists():
            continue
        g, days = gr(fam)
        n_days = sum(days.values())
        res = {}
        for m in METHODS:
            x = g[g.method == m].copy()
            if not len(x):
                continue
            hb = [route(v, p, n) for v, p, n in zip(x.verdict, x.p_comms if "p_comms" in x else
                                                   [np.nan] * len(x), x.n_meters)]
            x["human"] = [h["handled_by"] == "HUMAN" for h in hb]
            x["day"] = x.seed.astype(str) + "_" + pd.to_datetime(x.onset).dt.date.astype(str)
            per_day = lambda s: float(s.sum() / n_days)
            r = {"transformer_days": n_days, "groups_per_day": len(x) / n_days}
            for k, mask in {"outage": x.verdict == "OUTAGE", "comms": x.verdict == "COMMS_FAILURE",
                            "uncertain": x.verdict == "UNCERTAIN",
                            "human_uncertain": x.human & (x.verdict == "UNCERTAIN"),
                            "human_outage_approval": x.human & (x.verdict == "OUTAGE"),
                            "human_comms_review": x.human & (x.verdict == "COMMS_FAILURE"),
                            "human_total": x.human}.items():
                r[f"{k}_per_day"] = per_day(mask)
                # interval: bootstrap over days (days without groups count as zero)
                cnt = mask.groupby(x.day).sum()
                full = np.zeros(int(round(n_days)))
                full[:len(cnt)] = cnt.to_numpy()
                bs = [RNG.choice(full, len(full)).mean() for _ in range(BOOT)]
                r[f"{k}_per_day_ci95"] = [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))]
            r["by_size_per_day"] = {
                str(k): {"groups": len(y) / n_days,
                         "uncertain": float((y.verdict == "UNCERTAIN").sum() / n_days),
                         "outage": float((y.verdict == "OUTAGE").sum() / n_days),
                         "human": float(y.human.sum() / n_days)}
                for k, y in x.groupby(pd.cut(x.n_meters, SIZE_BINS), observed=True)}
            res[m] = r
        out[fam] = res
    return out


def outage_outcomes(fams):
    out = {}
    for fam in fams:
        if not (REC / f"{fam}__episodes.parquet").exists():
            continue
        t = ep(fam)
        o = t[(t.method == PRIMARY) & (t.cause == "OUTAGE")]
        out[fam] = {"n": len(o), **{k: int((o.verdict == v).sum()) for k, v in
                                   [("outage_verdict", "OUTAGE"), ("comms_verdict", "COMMS_FAILURE"),
                                    ("abstained_escalated", "UNCERTAIN"),
                                    ("never_detected", "MISSED")]}}
    return out


# ------------------------------------------------------------------ Task 2: base rates
def poisson_ci(k, exposure):
    lo = stats.chi2.ppf(0.025, 2 * k) / 2 if k else 0.0
    hi = stats.chi2.ppf(0.975, 2 * k + 2) / 2
    return [lo / exposure, hi / exposure]


def base_rates():
    out = {}
    for fam in ["ff_semiurb5", "ff_urban6"]:
        g, days = gr(fam)
        b = g[(g.method == PRIMARY)]
        for weeks, name in [([3], "test_weeks"), ([2, 3], "weeks_not_used_for_fitting")]:
            x = b[b.week.isin(weeks)]
            per_seed = sum(((np.arange(int(round(d))) // 7) % 4 == w).sum() for w in weeks
                           for d in days.values())
            n_days = float(per_seed)  # exact count of days in those week classes, all seeds
            fo = x[x.verdict == "OUTAGE"]
            years = n_days / 365.25
            out[f"{fam}/{name}"] = {
                "false_outage_verdicts": len(fo), "transformer_years": years,
                "per_transformer_year": len(fo) / years,
                "per_transformer_year_ci95": poisson_ci(len(fo), years),
                "silent_set_sizes": fo.n_meters.value_counts().sort_index().to_dict()}
    return out


def ppv_curve(rates, recall):
    """P(real outage | OUTAGE verdict) vs assumed real outage frequency f (free parameter)."""
    fa = rates["ff_urban6/test_weeks"]["per_transformer_year"]
    fa_hi = rates["ff_urban6/test_weeks"]["per_transformer_year_ci95"][1]
    f = np.logspace(-2, 2, 81)
    return {"f_per_transformer_year": f.tolist(),
            "ppv": (f * recall / (f * recall + fa)).tolist(),
            "ppv_with_fa_upper": (f * recall / (f * recall + fa_hi)).tolist(),
            "fa_per_year": fa, "fa_upper": fa_hi, "outage_recall_used": recall,
            "note": "comms-failure events add c x false-outage rate to the denominator; the "
                    "held-out false-outage rate was 0/155, so this term is omitted"}


# ------------------------------------------------------------------ Task 3: boundary
def axes_of(t, typ):
    m = t.M.abs()
    sd_load = np.sqrt(np.clip(t.sd_C ** 2 - t.sd_O ** 2, 0, None))
    return {"share": m / (typ * t.n_intervals), "kwh": m, "snr": m / sd_load.replace(0, np.nan)}


def fast_boot(tt, n=200):
    """Cluster bootstrap over (seed, day) of the logistic x90, on numpy arrays."""
    key = tt.seed.astype(str) + "_" + pd.to_datetime(tt.start).dt.date.astype(str)
    codes, uniq = pd.factorize(key)
    members = [np.flatnonzero(codes == k) for k in range(len(uniq))]
    x, y = tt._x.to_numpy(), tt._y.to_numpy()
    vals = []
    for _ in range(n):
        idx = np.concatenate([members[i] for i in RNG.integers(0, len(members), len(members))])
        v = x90(x[idx], y[idx])[0]
        vals.append(np.nan if v is None else v)
    vals = np.array(vals, float)
    vals = vals[np.isfinite(vals)]
    if len(vals) < n * 0.8:  # fit undefined in many resamples: report as unstable
        return [None, None]
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


def x90(x, y):
    ok = np.isfinite(x) & (x > 0)
    x, y = np.log(x[ok]), y[ok]
    if y.min() == y.max() or len(y) < 20:
        return None, None
    lr = LogisticRegression(C=1e6).fit(x.reshape(-1, 1), y)
    b0, b1 = lr.intercept_[0], lr.coef_[0, 0]
    lg = float(np.exp((np.log(9) - b0) / b1)) if b1 > 0 else None
    iso = IsotonicRegression(increasing=True, out_of_bounds="clip").fit(x, y)
    xs = np.sort(x)
    hit = xs[iso.predict(xs) >= 0.9]
    return lg, (float(np.exp(hit[0])) if len(hit) else None)


def boundary(fam, typ, weeks):
    t = ep(fam)
    t = t[(t.method == PRIMARY) & t.week.isin(weeks)].dropna(subset=["M"]).reset_index(drop=True)
    res = {}
    for name, x in axes_of(t, typ).items():
        y = (t.verdict == t.cause).to_numpy().astype(int)
        lg, iso = x90(x.to_numpy(float), y)
        tt = t.assign(_x=x.to_numpy(float), _y=y)
        ci = fast_boot(tt, n=200)
        res[name] = {"x90_logistic": lg, "x90_isotonic": iso, "x90_ci95": ci, "n": len(t)}
    return res


def typical_T(grid):
    base = scenario.simulate(scenario.merge(scenario.load_cfg("configs/baseline.yaml"),
                                            {"world": {"grid": grid}}))
    return float(np.mean(np.abs(base["observed"]["transformer"].energy_kwh)))


# ------------------------------------------------------------------ Task 4: size classes
def size_tables(fams):
    out = {}
    for fam, weeks in fams:
        if not (REC / f"{fam}__episodes.parquet").exists():
            continue
        t = ep(fam)
        t = t[t.week.isin(weeks)]
        p = t[t.method == PRIMARY]
        out[fam] = {"weeks": weeks,
                    "size_distribution": p.groupby(["cause", "size_class"]).size().unstack(0)
                    .fillna(0).astype(int).to_dict(),
                    "n_meters_distribution": p.groupby(pd.cut(p.n_meters, SIZE_BINS), observed=True)
                    .size().rename(index=str).to_dict(),
                    "by_class": {}}
        for m in ["bayes", "ztest", "share", "naive"]:
            x = t[t.method == m]
            out[fam]["by_class"][m] = {c: {**{k: v for k, v in evaluate.rates(y).items()},
                                           "coverage": 1 - evaluate.rates(y)["abstention_rate"]}
                                       for c, y in x.groupby("size_class")}
    return out


# ------------------------------------------------------------------ Task 5
def safety_table():
    r = json.load(open("results/cp5_compare.json"))["results_val"]
    lim = {"fault_free_false_outage_per_meter_day": 0.001, "missed_outage_rate": 0.05,
           "false_outage_rate": 0.05}
    out = {}
    for m in METHODS:
        rows = r[m].get("sweep") or [r[m]]
        ok = [s for s in rows if all(np.nan_to_num(s[k], nan=1) <= v for k, v in lim.items())]
        out[m] = {"settings_tried": len(rows),
                  "max_coverage_meeting_constraints": max((1 - s["abstention_rate"] for s in ok),
                                                          default=None),
                  "min_fault_free_false_outage_per_meter_day":
                      min(s["fault_free_false_outage_per_meter_day"] for s in rows)}
    p = Path("results/iforest.json")
    if p.exists():
        f = json.load(open(p))
        out["iforest (added after CP7)"] = {
            "settings_tried": len(f["validation_sweep"]),
            "max_coverage_meeting_constraints": None if f["validation"]["false_outage_rate"] > 0.05
            or f["validation"]["missed_outage_rate"] > 0.05 else 1.0,
            "note": "no abstention; see iforest.json"}
    return out


def paired_coverage():
    t = ep("cp7_heldout_urban6")
    t = t[t.week == 3]
    w = t.pivot_table(index=["seed", "episode_id"], columns="method", values="verdict",
                      aggfunc="first")
    cov = w.isin(["OUTAGE", "COMMS_FAILURE"]).astype(float)
    start = t.drop_duplicates(["seed", "episode_id"]).set_index(["seed", "episode_id"]).start
    cov = cov.join(start).reset_index()
    out = {}
    for a, b in [("bayes", "ztest"), ("bayes", "share"), ("ztest", "share")]:
        d = cov[a] - cov[b]
        out[f"{a}-{b}"] = {"coverage_difference": float(d.mean()),
                           "ci95": cluster_boot(cov.assign(_d=d), lambda s: s._d.mean())}
    return out


# ------------------------------------------------------------------ Task 7
def diversity_range():
    out = {}
    for c in ["diversity_0.0", "diversity_0.25", "nominal", "diversity_1.0"]:
        r = json.load(open(f"results/cp6/{c}.json"))["methods"][PRIMARY]
        out[c] = {"coverage": 1 - r["abstention_rate"], "outage_recall": r["outage_recall"],
                  "comms_recall": r["comms_recall"], "missed": r["missed_outage_rate"],
                  "false_outage": r["false_outage_rate"]}
    keys = ["coverage", "outage_recall", "comms_recall", "missed", "false_outage"]
    out["range"] = {k: [min(v[k] for v in out.values()), max(v[k] for v in out.values())]
                    for k in keys}
    return out


# ------------------------------------------------------------------ Task 8
def gap_diagnostic():
    cfgs = {"nominal": {}, "tmeter_gain_sd2pct": {"seed": 441, "tmeter": {"gain_sd": 0.02,
                                                                            "noise_rel_sd": 0.01}},
            "unmetered_profile_5kw": {"seed": 442, "world": {"unmetered": {"kind": "profile",
                                                                            "kw": 5.0}}}}
    out = {}
    for name, over in cfgs.items():
        sim = scenario.simulate(scenario.merge(scenario.load_cfg("configs/baseline.yaml"), over))
        index, meters, E, A, T = arrays(inputs_of(sim))
        full = np.isfinite(E).all(1)
        load = np.nansum(E, 1)
        gap = np.where(full, T - load, np.nan)
        s = pd.Series(gap)
        base = s.rolling(96, min_periods=10).median().shift(1).to_numpy()
        lbase = pd.Series(np.where(full, load, np.nan)).rolling(96, min_periods=10).median().shift(1)
        e1 = gap - base
        dl = load - lbase.to_numpy()
        wk = (np.arange(len(T)) // 672) % 4
        tr = np.isfinite(e1) & np.isfinite(dl) & np.isin(wk, [0, 1])
        va = np.isfinite(e1) & np.isfinite(dl) & (wk == 2)
        b = float(np.sum(e1[tr] * dl[tr]) / np.sum(dl[tr] ** 2))
        e2 = e1 - b * dl
        g = sim["truth"]
        out[name] = {"trafo_gain_drawn_once_per_scenario": True,
                     "implied_trafo_gain": float(sim["observed"]["transformer"].energy_kwh.sum()
                                                 / g["trafo_true_kwh"].sum()),
                     "corr_residual_vs_load_change_train": float(np.corrcoef(e1[tr], dl[tr])[0, 1]),
                     "corr_residual_vs_load_train": float(np.corrcoef(e1[tr], load[tr])[0, 1]),
                     "slope_per_kwh_load_change": b,
                     "residual_sd_constant_baseline_val": float(np.std(e1[va])),
                     "residual_sd_load_dependent_val": float(np.std(e2[va])),
                     "reduction": float(1 - np.std(e2[va]) / np.std(e1[va]))}
    return out


# ------------------------------------------------------------------ figures
def figures(res, typ):
    out = Path("results/figs")
    f = res["ppv"]
    fig, ax = plt.subplots(figsize=(5.5, 3.8))
    ax.plot(f["f_per_transformer_year"], f["ppv"], label="false-alarm rate: point estimate")
    ax.plot(f["f_per_transformer_year"], f["ppv_with_fa_upper"], "--",
            label="false-alarm rate: upper 95% bound")
    ax.set(xscale="log", ylim=(0, 1), xlabel="assumed real outages per transformer-year (free parameter)",
           ylabel="P(real outage | outage verdict)",
           title=f"Base-rate effect, held-out grid ({LABEL})")
    ax.legend(frameon=False, fontsize=8)
    ax.title.set_fontsize(8)
    fig.tight_layout()
    fig.savefig(out / "cp10_ppv.png", dpi=150)
    # boundary curves (nominal + held-out), logistic fits per axis
    fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
    for col, (fam, weeks, grid) in zip(["#1f6fb4", "#d9822b"],
                                       [("cp6_nominal", [0, 1, 2], "dev"),
                                        ("cp7_heldout_urban6", [3], "held")]):
        t = ep(fam)
        t = t[(t.method == PRIMARY) & t.week.isin(weeks)].dropna(subset=["M"])
        for ax, (name, x) in zip(axes, axes_of(t, typ[grid]).items()):
            x = x.to_numpy(float)
            y = (t.verdict == t.cause).to_numpy().astype(int)
            ok = np.isfinite(x) & (x > 0)
            bins = np.quantile(x[ok], np.linspace(0, 1, 9))
            mids, rate = [], []
            for lo, hi in zip(bins[:-1], bins[1:]):
                m = ok & (x >= lo) & (x <= hi)
                mids.append(np.sqrt(lo * hi))
                rate.append(y[m].mean())
            ax.plot(mids, rate, "o", color=col, label=f"{fam} (binned)")
            lr = LogisticRegression(C=1e6).fit(np.log(x[ok]).reshape(-1, 1), y[ok])
            xs = np.logspace(np.log10(x[ok].min()), np.log10(x[ok].max()), 100)
            ax.plot(xs, lr.predict_proba(np.log(xs).reshape(-1, 1))[:, 1], color=col)
            ax.set(xscale="log", ylim=(0, 1), xlabel={"share": "silent share of transformer energy",
                                                      "kwh": "expected silent energy (kWh)",
                                                      "snr": "signal / predictive sd"}[name],
                   ylabel="P(correct cause)")
            ax.axhline(0.9, color="k", lw=0.6, ls=":")
    axes[0].legend(frameon=False, fontsize=7)
    fig.suptitle(f"Correct-cause probability vs three axes ({LABEL})", fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "cp10_boundary_axes.png", dpi=150)


def main():
    typ = {"dev": typical_T("1-LV-semiurb5--0-sw"), "held": typical_T("1-LV-urban6--0-sw")}
    res = {"stamp": stamp({"boot": BOOT, "size_bins": SIZE_BINS}, "python -m shahid.cp10"),
           "label": LABEL, "typical_transformer_kwh_per_interval": typ}
    res["r3"] = r3_harm()
    load_fams = ["ff_semiurb5", "ff_urban6", "loss10_ff_semiurb5", "loss10_ff_urban6",
                 "cp7_dev_semiurb5", "cp7_heldout_urban6", "loss10_semiurb5", "loss10_urban6"]
    res["operator_load"] = operator_load(load_fams)
    res["outage_outcomes"] = outage_outcomes(["cp5", "cp6_nominal", "cp7_dev_semiurb5",
                                              "cp7_heldout_urban6", "loss10_semiurb5",
                                              "loss10_urban6", "feeder_semiurb5", "feeder_urban6",
                                              "cp6_hn_packet_loss_10pct"])
    res["base_rates"] = base_rates()
    rec = json.load(open("results/cp7_heldout.json"))["targets"]["heldout_urban6"]["results"]
    res["ppv"] = ppv_curve(res["base_rates"], rec[PRIMARY]["outage_recall"])
    res["boundary"] = {}
    for f in sorted(REC.glob("cp6_*__episodes.parquet")):
        fam = f.name.split("__")[0]
        res["boundary"][fam] = boundary(fam, typ["dev"], [0, 1, 2])
    res["boundary"]["cp7_heldout_urban6"] = boundary("cp7_heldout_urban6", typ["held"], [3])
    res["boundary"]["cp7_dev_semiurb5"] = boundary("cp7_dev_semiurb5", typ["dev"], [3])
    cons = {}
    for axis in ["share", "kwh", "snr"]:
        v = [b[axis]["x90_logistic"] for k, b in res["boundary"].items()
             if b[axis]["x90_logistic"] and not k.endswith(("10.0kw", "simultaneous_outage_comms"))]
        cons[axis] = {"n_cells": len(v), "sd_log10_x90": float(np.std(np.log10(v))),
                      "heldout_vs_dev_ratio": (res["boundary"]["cp7_heldout_urban6"][axis]["x90_logistic"] or np.nan)
                      / (res["boundary"]["cp7_dev_semiurb5"][axis]["x90_logistic"] or np.nan)}
    res["boundary_axis_consistency"] = cons
    res["size_classes"] = size_tables([("cp5", [2]), ("cp6_nominal", [0, 1, 2]),
                                       ("cp7_dev_semiurb5", [3]), ("cp7_heldout_urban6", [3]),
                                       ("feeder_semiurb5", [0, 1, 2, 3]),
                                       ("feeder_urban6", [0, 1, 2, 3])])
    res["safety_table_cp5_validation"] = safety_table()
    res["paired_coverage_heldout"] = paired_coverage()
    res["diversity_range"] = diversity_range()
    res["gap_diagnostic"] = gap_diagnostic()
    figures(res, typ)
    write_json("results/cp10.json", res)
    print(json.dumps({k: res[k] for k in ["r3", "outage_outcomes", "base_rates",
                                          "boundary_axis_consistency", "paired_coverage_heldout",
                                          "diversity_range", "gap_diagnostic"]}, indent=1,
                     default=str)[:9000])


if __name__ == "__main__":
    main()
