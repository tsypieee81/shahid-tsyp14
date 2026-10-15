"""CP12: separated policy components under one matching rule, small-group uncertainty, break-even
between wrong verdicts and human reviews, headline ranges. docs/eval_protocol.md addendum D.

Post-processing of existing records only (no simulation, no power flow, detector unchanged).
Every policy row other than plain version 1 is a "post-hoc variant, not pre-registered".
Run: python -m shahid.cp12   (writes results/cp12.json and results/figs/cp12_*.png)
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from shahid import cp11, evaluate  # noqa: E402
from shahid.stamp import stamp, write_json  # noqa: E402

REC = cp11.REC
LABEL = "post-hoc variant, not pre-registered"
GATE_N, GATE_T = 3, 1  # addendum C setting, not re-chosen
TIMEOUTS = [1, 2, 4, 8]
ROWS = ([("v1", False, None), ("v1+gate", True, None)]
        + [(f"v1+recheck{T}h", False, T) for T in TIMEOUTS]
        + [(f"v1+gate+recheck{T}h", True, T) for T in TIMEOUTS])
TYPE = {"uncertain": "uncertain", "watch_timeout": "uncertain",
        "outage_verdict": "outage_awaiting_approval",
        "comms_review": "comms_unconfirmed", "comms_unconfirmed_timeout": "comms_unconfirmed"}
HUMAN_TYPES = ["uncertain", "outage_awaiting_approval", "comms_unconfirmed"]
CATEGORY = {"outage_verdict": "outage_verdict", "comms_auto_closed": "closed_as_comms",
            "comms_confirmed": "closed_as_comms", "watch_resolved_comms": "closed_as_comms",
            "uncertain": "uncertain", "watch_timeout": "uncertain",
            "comms_review": "comms_unconfirmed", "comms_unconfirmed_timeout": "comms_unconfirmed",
            "watch_closed_no_verdict": "closed_no_verdict", "never_detected": "never_detected"}
CATS = ["outage_verdict", "closed_as_comms", "uncertain", "comms_unconfirmed", "closed_no_verdict",
        "never_detected"]
DEV_FF = ["ff_semiurb5"] + [f"ffx_semiurb5_{s}" for s in [451, 452, 453, 454]]
HELD_FF = ["ff_urban6"] + [f"ffx_urban6_{s}" for s in [455, 456, 457, 458]]
OUTCOME_FAMS = {"dev": ("feeder_semiurb5", [0, 1, 2, 3]), "heldout": ("feeder_urban6", [0, 1, 2, 3]),
                "rural": ("rural3_eps", [3])}
ATTN_FAMS = {"cp7_dev_semiurb5": [3], "cp7_heldout_urban6": [3], "feeder_semiurb5": [0, 1, 2, 3],
             "feeder_urban6": [0, 1, 2, 3], "rural3_eps": [3]}
RECHECK_FAMS = {**ATTN_FAMS, "cp6_tmeter_gain_0.02": [0, 1, 2],
                "cp6_unmetered_profile_10.0kw": [0, 1, 2],
                "cp6_hn_simultaneous_outage_comms": [0, 1, 2]}
LOAD_FAMS = {"fault_free": {"1%": ["ff_semiurb5", "ff_urban6", "rural3_ff"],
                            "10%": ["loss10_ff_semiurb5", "loss10_ff_urban6"]},
             "events": {"1%": ["cp7_dev_semiurb5", "cp7_heldout_urban6", "feeder_semiurb5",
                               "feeder_urban6", "rural3_eps"],
                        "10%": ["loss10_semiurb5", "loss10_urban6"]}}
BASELINES = ["naive", "step", "count", "structure", "iforest"]
OTHER_METHODS = ["ztest", "lr", "share", "naive", "step", "count", "structure", "iforest"]
PI = [round(x, 1) for x in np.arange(0.1, 0.91, 0.1)]
SIZE_BINS = [("1", 1, 1), ("2", 2, 2), ("3-5", 3, 5), ("6-20", 6, 20), (">20", 21, 10 ** 6)]
NEAR_ZERO, CLEAR_POS = 0.005, 0.05  # kWh per interval, addendum D
RNG = np.random.default_rng(12)
FIG = Path("results/figs")


def wilson(k, n):
    return {"k": int(k), "n": int(n), "rate": k / n if n else None, "ci95": evaluate.wilson(k, n)}


def per_day(k, d):
    return {"k": int(k), "per_day": k / d, "ci95": cp11.poisson_ci(int(k), d)}


# ------------------------------------------------------------------ policies (addendum D)
def policy(g, gate, T_h):
    """Outcome and human time per group for one policy row."""
    out = pd.Series("", index=g.index, dtype=object)
    ht = pd.Series(np.nan, index=g.index)

    def put(mask, name, t=None):
        out[mask] = name
        if t is not None:
            ht[mask] = t[mask]

    v = g.verdict
    gated = (g.n_meters < GATE_N) if gate else pd.Series(False, index=g.index)
    Tw = GATE_T * 4
    fill_w, silent_w = g.t_fill <= g.tau + Tw, g.t_resume > g.tau + Tw
    put(gated & fill_w, "watch_resolved_comms")
    put(gated & ~fill_w & silent_w, "watch_timeout", g.tau + Tw)
    put(gated & ~fill_w & ~silent_w, "watch_closed_no_verdict")
    ng = ~gated
    put(ng & (v == "OUTAGE"), "outage_verdict", g.tau)
    put(ng & (v == "UNCERTAIN"), "uncertain", g.tau)
    c = ng & (v == "COMMS_FAILURE")
    if T_h is None:  # version 1 escalation table: R3 auto-close, R4 review
        r3 = (g.p_comms.fillna(0) >= 0.95) & (g.n_meters <= 40)
        put(c & r3, "comms_auto_closed")
        put(c & ~r3, "comms_review", g.tau)
    else:
        ok = g.t_fill <= g.tau + T_h * 4
        put(c & ok, "comms_confirmed")
        put(c & ~ok, "comms_unconfirmed_timeout", g.tau + T_h * 4)
    return out, ht


def episode_view(g, eps, out, ht, weeks):
    """Labelled episodes with their policy outcome; match = registered set-overlap rule."""
    e = eps[eps.week.isin(weeks)].copy()
    m = g[g.matched_episode >= 0]
    pos = dict(zip(zip(m.seed, m.matched_episode.astype(int)), m.index))
    idx = [pos.get((s, int(i))) for s, i in zip(e.seed, e.episode_id)]
    e["outcome"] = [out[i] if i is not None else "never_detected" for i in idx]
    e["human_t"] = [ht[i] if i is not None else np.nan for i in idx]
    e["category"] = e.outcome.map(CATEGORY)
    e["start_t"] = ((e.start - cp11.T0) / cp11.STEP).astype(int)
    e["end_t"] = ((e.end - cp11.T0) / cp11.STEP).astype(int)
    e["realtime"] = e.human_t.notna() & (e.human_t < e.end_t)
    e["wait_h"] = (e.human_t - e.start_t) / 4
    return e


def method_view(fam, method, weeks):
    """Episode categories for a non-policy method (verdicts as reported; comms closed)."""
    if method == "iforest":
        t = pd.read_parquet(REC / f"{fam}__iforest_episodes.parquet")
    else:
        t = pd.read_parquet(REC / f"{fam}__episodes.parquet").query("method == @method")
    t = t[t.week.isin(weeks)].copy()
    t["category"] = t.verdict.map({"OUTAGE": "outage_verdict", "COMMS_FAILURE": "closed_as_comms",
                                   "UNCERTAIN": "uncertain", "MISSED": "never_detected"})
    return t


def outcome_table(e):
    res = {}
    for cause, key in [("OUTAGE", "outage"), ("COMMS_FAILURE", "comms")]:
        x = e[e.cause == cause]
        res[key] = {c: wilson((x.category == c).sum(), len(x)) for c in CATS}
    return res


def attention_by_size(e):
    o = e[e.cause == "OUTAGE"]
    res = {"all": wilson((~o.realtime).sum(), len(o))}
    for c, x in o.groupby("size_class"):
        res[c] = wilson((~x.realtime).sum(), len(x))
    return res


def load(g, days, out):
    d = cp11.n_days(days)
    typ = out.map(TYPE)
    res = {t: per_day((typ == t).sum(), d) for t in HUMAN_TYPES}
    res["transformer_days"] = d
    res["watch_timeout_part_of_uncertain"] = int((out == "watch_timeout").sum())
    return res


def false_outages(fams, gate, T_h):
    k = d = 0
    for f in fams:
        g, days = cp11.groups(f)
        out, _ = policy(g, gate, T_h)
        k += int(((out == "outage_verdict") & (g.truth == "COMMS_FAILURE")).sum())
        d += cp11.n_days(days)
    yrs = d / 365.25
    return {"false_outage_verdicts": k, "transformer_years": yrs, "per_year": k / yrs,
            "per_year_ci95": cp11.poisson_ci(k, yrs)}


def sanity():
    """The separated policies reproduce CP11's version 1 and version 1.1 group outcomes."""
    ren = {"comms_recheck_escalated": "comms_unconfirmed_timeout", "watch_escalated": "watch_timeout",
           "watch_closed_gap": "watch_closed_no_verdict"}
    for fam in ["feeder_urban6", "ff_semiurb5", "cp7_heldout_urban6"]:
        g, _ = cp11.groups(fam)
        assert (policy(g, False, None)[0] == cp11.v1_policy(g)[0]).all()
        assert (policy(g, True, 1)[0] == cp11.policy(g, "n", 3, 1)[0].replace(ren)).all()
    return "v1 and gate+recheck1h reproduce CP11 v1_policy and policy(n, 3, 1) on 3 families"


# ------------------------------------------------------------------ Task 1
def task1():
    """Matching rule D vs CP11 onset-only: recompute the published CP11 attention numbers."""
    sel = json.load(open("results/cp11_select.json"))
    e11 = json.load(open("results/cp11_eval.json"))
    res = {"select_cp5_week2": {}, "outage_attention": {}, "feeder_never_detected": {}}
    g, _ = cp11.groups("cp5")
    eps = cp11.episodes("cp5")
    for name, (gate, T), old in [("v1", (False, None), sel["v1_reference"]["v1"]),
                                 ("v1.1", (True, 1), sel["chosen"])]:
        e = episode_view(g, eps, *policy(g, gate, T), [2])
        a = cp11.attention_summary(e[e.cause == "OUTAGE"])
        new = {"branch_feeder_no_realtime": a["branch_feeder_no_realtime"],
               "single_no_realtime": a["single"]["no_realtime_attention"],
               "all_no_realtime": a["all"]["no_realtime_attention"]}
        oldv = {"branch_feeder_no_realtime": old["branch_feeder_no_realtime"],
                "single_no_realtime": old["single"]["no_realtime_attention"] if name == "v1"
                else old["single_no_realtime"],
                "all_no_realtime": old["all"]["no_realtime_attention"] if name == "v1"
                else old["all_no_realtime"]}
        res["select_cp5_week2"][name] = {"cp11": oldv, "rule_D": new}
    for fam, att in e11["outage_attention"].items():
        g, _ = cp11.groups(fam)
        eps = cp11.episodes(fam)
        w = att["weeks"]
        a1 = episode_view(g, eps, *policy(g, False, None), w)
        a2 = episode_view(g, eps, *policy(g, True, 1), w)
        o = lambda a: a[a.cause == "OUTAGE"]
        closed = (o(a1).category == "closed_as_comms").to_numpy()
        caught = o(a2)[closed]
        res["outage_attention"][fam] = {
            "cp11": {"v1_no_realtime": att["v1"]["all"]["no_realtime_attention"],
                     "v11_no_realtime": att["v1.1"]["all"]["no_realtime_attention"],
                     "r3_v1_auto_closed": att["r3_v1_auto_closed"], "r3_v11_caught": att["r3_v11_caught"],
                     "r3_v11_caught_realtime": att["r3_v11_caught_realtime"]},
            "rule_D": {"v1_no_realtime": float((~o(a1).realtime).mean()),
                       "v11_no_realtime": float((~o(a2).realtime).mean()),
                       "r3_v1_auto_closed": int(closed.sum()),
                       "r3_v11_caught": int(caught.human_t.notna().sum()),
                       "r3_v11_caught_realtime": int(caught.realtime.sum())}}
    # whole-feeder "never detected" 0.006 -> 0.051: the specific episodes
    for fam in ["feeder_semiurb5", "feeder_urban6"]:
        g, _ = cp11.groups(fam)
        e = episode_view(g, cp11.episodes(fam), *policy(g, True, 1), [0, 1, 2, 3])
        o = e[e.cause == "OUTAGE"]
        lst = o[o.outcome.isin(["watch_closed_no_verdict", "watch_resolved_comms", "never_detected"])]
        res["feeder_never_detected"][fam] = {
            "n_outages": len(o),
            "cp11_column": "never_detected + watch_closed_gap + watch_resolved_comms",
            "counts_rule_D": lst.outcome.value_counts().to_dict(),
            "episodes": [{"seed": int(r.seed), "episode_id": int(r.episode_id), "start": str(r.start),
                          "n_meters": int(r.n_meters), "duration_h": (r.end_t - r.start_t) / 4,
                          "v1_verdict": r.verdict, "outcome": r.outcome} for r in lst.itertuples()]}
    return res


# ------------------------------------------------------------------ Task 2
def comms_durations():
    res = {}
    for fam in ["cp5", "feeder_urban6", "rural3_eps"]:
        e = cp11.episodes(fam)
        h = ((e[e.cause == "COMMS_FAILURE"].end - e[e.cause == "COMMS_FAILURE"].start)
             / pd.Timedelta(hours=1)).to_numpy()
        res[fam] = {"n": len(h), "min_h": float(h.min()), "max_h": float(h.max()),
                    "quantiles_h": {str(q): float(np.quantile(h, q)) for q in [0.1, 0.5, 0.9]},
                    "share_longer_than_h": {str(T): float((h > T).mean()) for T in TIMEOUTS}}
    res["source"] = ("simulation config: comms-failure episodes last a uniform 4-16 intervals "
                     "(1-4 h); configs/cp5_episodes.yaml and shahid/records.py feeder_events")
    return res


def task2():
    res = {}
    for name, gate, T in ROWS:
        r = {"label": "version 1 (registered)" if name == "v1" else LABEL, "gate": gate,
             "recheck_timeout_h": T}
        r["outcomes"] = {}
        for k, (fam, w) in OUTCOME_FAMS.items():
            g, _ = cp11.groups(fam)
            r["outcomes"][k] = outcome_table(episode_view(g, cp11.episodes(fam), *policy(g, gate, T), w))
        r["load"] = {}
        for kind, by_loss in LOAD_FAMS.items():
            for loss, fams in by_loss.items():
                for fam in fams:
                    g, days = cp11.groups(fam)
                    r["load"][f"{kind}/{loss}/{fam}"] = load(g, days, policy(g, gate, T)[0])
        r["false_outage_per_year"] = {"semiurb5": false_outages(DEV_FF, gate, T),
                                      "urban6": false_outages(HELD_FF, gate, T),
                                      "rural3": false_outages(["rural3_ff"], gate, T)}
        r["no_realtime_attention"] = {}
        for fam, w in ATTN_FAMS.items():
            g, _ = cp11.groups(fam)
            r["no_realtime_attention"][fam] = attention_by_size(
                episode_view(g, cp11.episodes(fam), *policy(g, gate, T), w))
        if T is not None:
            r["recheck"] = {}
            for fam, w in RECHECK_FAMS.items():
                g, _ = cp11.groups(fam)
                eps = cp11.episodes(fam)
                e1 = episode_view(g, eps, *policy(g, False, None), w)
                e2 = episode_view(g, eps, *policy(g, gate, T), w)
                c = e2[e2.cause == "COMMS_FAILURE"]
                closed = ((e1.cause == "OUTAGE") & (e1.category == "closed_as_comms")).to_numpy()
                caught = e2[closed]
                wait = caught.wait_h.dropna()
                r["recheck"][fam] = {
                    "comms_needing_human_confirmation": wilson((c.category == "comms_unconfirmed").sum(), len(c)),
                    "outages_v1_closed_as_comms": int(closed.sum()),
                    "of_which_caught": int(caught.human_t.notna().sum()),
                    "caught_in_real_time": int(caught.realtime.sum()),
                    "wait_h_quantiles": {str(q): float(wait.quantile(q)) for q in [0.1, 0.5, 0.9]}
                    if len(wait) else None}
        res[name] = r
    return res


# ------------------------------------------------------------------ Task 3
def size_bin(n):
    for name, lo, hi in SIZE_BINS:
        if lo <= n <= hi:
            return name


def residuals(fams, weeks, truth=None):
    x = []
    for f in fams:
        g, _ = cp11.groups(f)
        g = g[g.week.isin(weeks) & g.M.notna() & (g.sd_C > 0)]
        if truth:
            g = g[(g.truth == truth) & (g.matched_episode >= 0)]
        x.append(g)
    g = pd.concat(x, ignore_index=True)
    g["z"] = (g.R - g.M) / g.sd_C
    g["snr"] = g.M.abs() / np.sqrt(np.clip(g.sd_C ** 2 - g.sd_O ** 2, 0, None)).replace(0, np.nan)
    g["bin"] = g.n_meters.map(size_bin)
    return g


def residual_summary(g, tcrit):
    res = {}
    for name, _, _ in SIZE_BINS:
        x = g[g.bin == name]
        if not len(x):
            continue
        fo = x[x.verdict == "OUTAGE"]
        res[name] = {"n": len(x), "coverage_90": wilson((x.z.abs() < tcrit).sum(), len(x)),
                     "below_lower_bound": wilson((x.z < -tcrit).sum(), len(x)),
                     "above_upper_bound": wilson((x.z > tcrit).sum(), len(x)),
                     "z_quantiles": {str(q): float(x.z.quantile(q)) for q in [0.05, 0.25, 0.5, 0.75, 0.95]},
                     "lower_tail_observed_vs_model": {
                         str(k): {"observed": float((x.z < -k).mean()), "model_t4": float(stats.t.cdf(-k, 4))}
                         for k in [3, 4, 5]},
                     "false_outage_verdicts": len(fo),
                     "false_outage_share": wilson(len(fo), len(x)),
                     "false_outage_M_over_sdO_median": float((fo.M / fo.sd_O).median()) if len(fo) else None,
                     "false_outage_snr_median": float(fo.snr.median()) if len(fo) else None,
                     "false_outage_z_median": float(fo.z.median()) if len(fo) else None}
    return res


def near_zero():
    """Single meters, fault-free development year (dataset/baseline_semiurb5), validation weeks."""
    p = json.load(open("results/detector_params.json"))["fitted"]
    m = pd.read_parquet("dataset/baseline_semiurb5/observed/meter_readings.parquet")
    E = m.pivot_table(index="interval_start", columns="meter_id", values="energy_kwh",
                      observed=False).to_numpy()
    days = E.shape[0] // 96
    D = E[:days * 96].reshape(days, 96, -1)
    H = 14
    mean, sd = np.full_like(D, np.nan), np.full_like(D, np.nan)
    for d in range(H, days):
        mean[d] = np.nanmean(D[d - H:d], 0)
        sd[d] = np.nanstd(D[d - H:d], 0, ddof=1)
    val = ((np.arange(days) // 7) % 4) == 2
    a, mu, s = D[val], mean[val], sd[val] * p["sigma1_mult_by_lead"][0]
    ok = np.isfinite(a) & np.isfinite(mu) & (mu >= CLEAR_POS) & (s > 0)
    emp = float((a[ok] <= NEAR_ZERO).mean())
    model = float(stats.t.cdf((NEAR_ZERO - mu[ok]) / s[ok], p["t_df"]).mean())
    return {"intervals_with_clearly_positive_expectation": int(ok.sum()),
            "share_near_zero_actual": emp, "share_implied_by_model": model,
            "ratio_observed_to_model": emp / model if model else None,
            "thresholds_kwh": {"near_zero": NEAR_ZERO, "clearly_positive": CLEAR_POS},
            "model": "same-slot 14-day mean, sd x sigma1_mult(lead 1), Student-t df 4 (no anchor)"}


def task3():
    p = json.load(open("results/detector_params.json"))["fitted"]
    tcrit = float(stats.t.ppf(0.95, p["t_df"]))
    return {"t_crit_90": tcrit,
            "fault_free_dev_validation": residual_summary(residuals(DEV_FF, [2]), tcrit),
            "fault_free_heldout_validation": residual_summary(residuals(HELD_FF, [2]), tcrit),
            "labelled_comms_cp5_validation": residual_summary(residuals(["cp5"], [2], "COMMS_FAILURE"), tcrit),
            "single_meter_near_zero": near_zero()}


# ------------------------------------------------------------------ Task 4
def indicators(e):
    o, c = e[e.cause == "OUTAGE"], e[e.cause == "COMMS_FAILURE"]
    human = lambda x: x.category.isin(["uncertain", "comms_unconfirmed"]).to_numpy(float)
    return {"wo": (o.category == "closed_as_comms").to_numpy(float),
            "wc": (c.category == "outage_verdict").to_numpy(float),
            "ho": human(o), "hc": human(c),
            "no": o.category.isin(["closed_no_verdict", "never_detected"]).to_numpy(float),
            "nc": c.category.isin(["closed_no_verdict", "never_detected"]).to_numpy(float)}


def task4():
    res = {}
    for k, fam in [("heldout", "feeder_urban6"), ("dev", "feeder_semiurb5")]:
        w = [0, 1, 2, 3]
        g, _ = cp11.groups(fam)
        eps = cp11.episodes(fam).sort_values(["seed", "episode_id"])
        views = {name: episode_view(g, eps, *policy(g, gate, T), w) for name, gate, T in ROWS}
        for m in OTHER_METHODS:
            views[m] = method_view(fam, m, w).sort_values(["seed", "episode_id"])
        keys = list(zip(eps.seed, eps.episode_id))
        for v in views.values():
            assert list(zip(v.seed, v.episode_id)) == keys
        ind = {n: indicators(v) for n, v in views.items()}
        per100 = {n: {"outage_closed_as_comms": 100 * x["wo"].mean(),
                      "comms_called_outage": 100 * x["wc"].mean(),
                      "human_reviews_per_100_outages": 100 * x["ho"].mean(),
                      "human_reviews_per_100_comms": 100 * x["hc"].mean(),
                      "no_attention_per_100_outages": 100 * x["no"].mean(),
                      "no_attention_per_100_comms": 100 * x["nc"].mean()} for n, x in ind.items()}
        no_, nc_ = len(ind["v1"]["wo"]), len(ind["v1"]["wc"])
        boots = [(RNG.integers(0, no_, no_), RNG.integers(0, nc_, nc_)) for _ in range(1000)]
        ratios = {}
        for a in ["v1", "v1+gate"]:
            for b in BASELINES:
                A, B = ind[a], ind[b]
                curve = {}
                for pi in PI + [0.5]:
                    def ratio(io, ic):
                        dh = pi * (A["ho"][io].mean() - B["ho"][io].mean()) + (1 - pi) * (
                            A["hc"][ic].mean() - B["hc"][ic].mean())
                        dw = pi * (B["wo"][io].mean() - A["wo"][io].mean()) + (1 - pi) * (
                            B["wc"][ic].mean() - A["wc"][ic].mean())
                        return dh, dw
                    dh, dw = ratio(slice(None), slice(None))
                    bs = np.array([ratio(io, ic) for io, ic in boots])
                    okb = (bs[:, 1] > 0) & (bs[:, 0] > 0)
                    r = bs[okb, 0] / bs[okb, 1]
                    curve[str(pi)] = {"extra_reviews_per_100": 100 * dh, "wrong_avoided_per_100": 100 * dw,
                                      "ratio": dh / dw if dw > 0 and dh > 0 else None,
                                      "relation": "trade" if dw > 0 and dh > 0 else
                                      "dominates (fewer reviews and fewer wrong verdicts)" if dw >= 0 and dh <= 0
                                      else "dominated" if dw <= 0 and dh >= 0 else "fewer reviews, more wrong verdicts",
                                      "ratio_ci95": [float(np.quantile(r, .025)), float(np.quantile(r, .975))]
                                      if okb.mean() > 0.975 else None,
                                      "share_boot_not_a_trade": float(1 - okb.mean())}
                ratios[f"{a} vs {b}"] = curve
        res[k] = {"family": fam, "n_outages": no_, "n_comms": nc_, "per_100": per100,
                  "extra_reviews_per_wrong_verdict_avoided": ratios}
    res["definitions"] = ("wrong automatic verdict = outage closed as communication + communication "
                          "failure called outage; human review = uncertain + communication verdict "
                          "unconfirmed (outage verdicts awaiting approval excluded); paired bootstrap "
                          "over episodes stratified by cause, 1000 resamples; cost ratio left free")
    return res


# ------------------------------------------------------------------ Task 5
def task5():
    res = {}
    for k, fam in [("dev_test_weeks", "cp7_dev_semiurb5"), ("heldout_urban6", "cp7_heldout_urban6"),
                   ("untouched_rural3", "rural3_eps")]:
        t = cp11.episodes(fam)
        t = t[t.week == 3]
        o, c = t[t.cause == "OUTAGE"], t[t.cause == "COMMS_FAILURE"]
        r = evaluate.rates(t)
        res[k] = {"n_outage": len(o), "n_comms": len(c),
                  "coverage": wilson((t.verdict != "UNCERTAIN").sum(), len(t)),
                  "outage_recall": wilson((o.verdict == "OUTAGE").sum(), len(o)),
                  "comms_recall": wilson((c.verdict == "COMMS_FAILURE").sum(), len(c)),
                  "false_outage_rate": wilson((c.verdict == "OUTAGE").sum(), len(c)),
                  "missed_outage_rate": wilson(o.verdict.isin(["COMMS_FAILURE", "MISSED"]).sum(), len(o)),
                  "accuracy_when_decided": r["accuracy_when_decided"]}
    dv = json.load(open("results/cp10.json"))["diversity_range"]["range"]
    res["diversity_range_cp6_d0_to_1"] = dv
    keys = ["coverage", "outage_recall", "comms_recall", "false_outage_rate", "missed_outage_rate"]
    res["range_over_three_evaluations"] = {
        q: [min(res[k][q]["rate"] for k in ["dev_test_weeks", "heldout_urban6", "untouched_rural3"]),
            max(res[k][q]["rate"] for k in ["dev_test_weeks", "heldout_urban6", "untouched_rural3"])]
        for q in keys}
    return res


# ------------------------------------------------------------------ figure
def fig_tradeoff(t2):
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for gate, mk, lab in [(False, "o-", "re-check only"), (True, "s--", "gate + re-check")]:
        names = [f"v1+{'gate+' if gate else ''}recheck{T}h" for T in TIMEOUTS]
        y = [t2[n]["recheck"]["feeder_urban6"]["comms_needing_human_confirmation"]["rate"] for n in names]
        ax.plot(TIMEOUTS, y, mk, color="#1f6fb4", label=f"comms failures needing a human ({lab})")
    ax.set(xscale="log", xticks=TIMEOUTS, xticklabels=[str(t) for t in TIMEOUTS], ylim=(0, 1.02),
           xlabel="re-check timeout (hours)", ylabel="share of genuine comms failures",
           title="Re-check timeout trade-off (held-out whole-feeder events)")
    ax2 = ax.twinx()
    for gate, mk in [(False, "o-"), (True, "s--")]:
        names = [f"v1+{'gate+' if gate else ''}recheck{T}h" for T in TIMEOUTS]
        y = [t2[n]["no_realtime_attention"]["feeder_urban6"]["all"]["rate"] for n in names]
        ax2.plot(TIMEOUTS, y, mk, color="#c44e52")
    ax2.set_ylabel("outages without real-time attention", color="#c44e52")
    ax2.set_ylim(0, 0.3)
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.legend(frameon=False, fontsize=6, loc="upper right")
    fig.tight_layout()
    fig.savefig(FIG / "cp12_recheck_tradeoff.png", dpi=300)


def main():
    out = {"stamp": stamp({"rows": [r[0] for r in ROWS], "gate": [GATE_N, GATE_T],
                           "timeouts_h": TIMEOUTS}, "python -m shahid.cp12"),
           "label": LABEL, "protocol": "docs/eval_protocol.md addendum D", "sanity": sanity()}
    out["task1_matching"] = task1()
    out["task2_components"] = task2()
    out["comms_duration"] = comms_durations()
    out["task3_small_groups"] = task3()
    out["task4_break_even"] = task4()
    out["task5_headline"] = task5()
    FIG.mkdir(parents=True, exist_ok=True)
    fig_tradeoff(out["task2_components"])
    write_json("results/cp12.json", out)
    print("written results/cp12.json")


if __name__ == "__main__":
    main()
