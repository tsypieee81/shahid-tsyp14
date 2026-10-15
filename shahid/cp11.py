"""CP11 analyses: complete CP10 tables, version 1.1 (resolution gate + WATCH + revised R3).

Version 1.1 is post-processing on unchanged version 1 outputs (docs/eval_protocol.md addendum B).
Numbers on pre-existing records are "post-hoc variant, not pre-registered".
Run: python -m shahid.cp11 select     (choose the operating point on development data only)
     python -m shahid.cp11 evaluate   (apply the chosen point everywhere; run after `select`)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score

from shahid import evaluate
from shahid.stamp import stamp, write_json

REC = Path("results/records")
T0 = pd.Timestamp("2016-01-01")
STEP = pd.Timedelta(minutes=15)
PRIMARY = "bayes"  # lr_band
METHODS = ["bayes", "lr", "share", "ztest", "naive", "step", "count", "structure"]
GRID = {"snr": [1, 2, 3, 4, 5, 6], "kwh": [0.25, 0.5, 1, 2, 4], "n": [2, 3, 4, 6]}
TIMEOUTS_H = [1, 2, 4, 6, 8]
RULE = {"max_false_outage_per_year": 4.0, "max_unattended_branch_feeder": 0.02}
LABEL_V11 = ("post-hoc variant, not pre-registered; selected under addendum C (deviation); "
             "addendum B rule found no feasible setting")
RNG = np.random.default_rng(11)


# ------------------------------------------------------------------ loading
def groups(fam, method=PRIMARY):
    g = pd.read_parquet(REC / f"{fam}__groups.parquet")
    meta = g[g.method == "_meta"]
    days = {int(r.seed): float(r.verdict.split("=")[1]) for r in meta.itertuples()}
    g = g[g.method == method].copy()
    tm = pd.read_parquet(REC / f"{fam}__cp11.parquet")
    g = g.merge(tm[["seed", "onset", "t0", "t_fill", "t_resume", "if_score", "if_verdict"]],
                on=["seed", "onset"], how="left")
    g["tau"] = g.t0 + g.latency_intervals
    return g, days


def episodes(fam, method=PRIMARY):
    return pd.read_parquet(REC / f"{fam}__episodes.parquet").query("method == @method")


def n_days(days, weeks=None):
    if weeks is None:
        return float(sum(days.values()))
    return float(sum(((np.arange(int(round(d))) // 7) % 4 == w).sum() for w in weeks
                     for d in days.values()))


def poisson_ci(k, exposure):
    lo = stats.chi2.ppf(0.025, 2 * k) / 2 if k else 0.0
    return [lo / exposure, stats.chi2.ppf(0.975, 2 * k + 2) / 2 / exposure]


# ------------------------------------------------------------------ version 1.1 policy
def gate_value(g, var):
    if var == "snr":
        sd = np.sqrt(np.clip(g.sd_C ** 2 - g.sd_O ** 2, 0, None))
        return g.M.abs() / sd.replace(0, np.nan)
    if var == "kwh":
        return g.M.abs()
    return g.n_meters


def policy(g, var, theta, T_h):
    """Per group: outcome, human (bool), human_time (interval index), final verdict."""
    Tn = T_h * 4
    gated = gate_value(g, var).fillna(0) < theta
    fill_ok = g.t_fill <= g.tau + Tn
    silent_at_T = g.t_resume > g.tau + Tn
    out = pd.Series("", index=g.index)
    human_t = pd.Series(np.nan, index=g.index)
    out[gated & fill_ok] = "watch_resolved_comms"
    m = gated & ~fill_ok & silent_at_T
    out[m], human_t[m] = "watch_escalated", (g.tau + Tn)[m]
    out[gated & ~fill_ok & ~silent_at_T] = "watch_closed_gap"
    v = g.verdict
    m = ~gated & (v == "OUTAGE")
    out[m], human_t[m] = "outage_verdict", g.tau[m]
    m = ~gated & (v == "UNCERTAIN")
    out[m], human_t[m] = "uncertain", g.tau[m]
    m = ~gated & (v == "COMMS_FAILURE") & fill_ok
    out[m] = "comms_confirmed"
    m = ~gated & (v == "COMMS_FAILURE") & ~fill_ok
    out[m], human_t[m] = "comms_recheck_escalated", (g.tau + Tn)[m]
    return out, human_t


def v1_policy(g):
    """Version 1 under the version 1 escalation table: OUTAGE and UNCERTAIN go to a human; COMMS with
    p >= 0.95 and <= 40 meters is closed automatically (R3), other COMMS go to a human (R4)."""
    out = pd.Series("", index=g.index)
    human_t = pd.Series(np.nan, index=g.index)
    v = g.verdict
    out[v == "OUTAGE"], human_t[v == "OUTAGE"] = "outage_verdict", g.tau[v == "OUTAGE"]
    out[v == "UNCERTAIN"], human_t[v == "UNCERTAIN"] = "uncertain", g.tau[v == "UNCERTAIN"]
    r3 = (v == "COMMS_FAILURE") & (g.p_comms.fillna(0) >= 0.95) & (g.n_meters <= 40)
    out[r3] = "comms_auto_closed"
    m = (v == "COMMS_FAILURE") & ~r3
    out[m], human_t[m] = "comms_review", g.tau[m]
    return out, human_t


def load_metrics(g, days, out, human_t, weeks=None):
    sel = g.week.isin(weeks) if weeks else pd.Series(True, index=g.index)
    d = n_days(days, weeks)
    hum = human_t.notna() & sel
    fo = (out == "outage_verdict") & (g.truth == "COMMS_FAILURE") & sel
    return {"transformer_days": d, "human_items_per_day": float(hum.sum() / d),
            "false_outage_verdicts": int(fo.sum()),
            "false_outage_per_year": float(fo.sum() / d * 365.25),
            "false_outage_per_year_ci95": poisson_ci(int(fo.sum()), d / 365.25),
            "by_outcome_per_day": {k: float(((out == k) & sel).sum() / d)
                                   for k in sorted(out[sel].unique())}}


def outage_attention(g, eps, out, human_t, weeks):
    """Per labelled outage: attention time vs episode end. Never-detected = no attention."""
    e = eps[(eps.cause == "OUTAGE") & eps.week.isin(weeks)].copy()
    gi = g.set_index(["seed", "onset"])
    key = list(zip(e.seed, e.start))
    att, oc = [], []
    for k in key:
        if k in gi.index:
            i = gi.index.get_loc(k)
            i = i if isinstance(i, (int, np.integer)) else np.flatnonzero(i)[0]
            att.append(human_t.iloc[i])
            oc.append(out.iloc[i])
        else:
            att.append(np.nan)
            oc.append("never_detected")
    e["outcome"], e["human_t"] = oc, att
    e["start_t"] = ((e.start - T0) / STEP).astype(int)
    e["end_t"] = ((e.end - T0) / STEP).astype(int)
    e["realtime"] = e.human_t.notna() & (e.human_t < e.end_t)
    e["wait_h"] = (e.human_t - e.start_t) / 4
    return e


def episode_outcomes(g, eps, out, weeks):
    """Outcome category of every labelled episode (both causes) under a policy."""
    e = eps[eps.week.isin(weeks)]
    gi = dict(zip(zip(g.seed, g.onset), out))
    oc = [gi.get(k, "never_detected") for k in zip(e.seed, e.start)]
    t = pd.DataFrame({"cause": e.cause.to_numpy(), "outcome": oc})
    return {c: x.outcome.value_counts().to_dict() for c, x in t.groupby("cause")}


def attention_summary(e):
    res = {}
    for c, x in [("all", e)] + list(e.groupby("size_class")):
        res[c] = {"n": len(x), "no_realtime_attention": float((~x.realtime).mean()),
                  "late_attention": float((x.human_t.notna() & ~x.realtime).mean()),
                  "never_attended": float(x.human_t.isna().mean()),
                  "wait_h_median_when_attended": float(x.wait_h.median()) if x.wait_h.notna().any() else None,
                  "outcomes": x.outcome.value_counts().to_dict()}
    bf = e[e.size_class.isin(["branch", "feeder"])]
    res["branch_feeder_no_realtime"] = float((~bf.realtime).mean()) if len(bf) else None
    return res


# ------------------------------------------------------------------ select
def select():
    gff, dff = groups("ff_semiurb5")
    gv, dv = groups("cp5")
    ev = episodes("cp5")
    rows = []
    out1, h1 = v1_policy(gff)
    o1, h1v = v1_policy(gv)
    base = {"v1": {**load_metrics(gff, dff, out1, h1, [0, 1]),
                   **attention_summary(outage_attention(gv, ev, o1, h1v, [2]))}}
    for var, thetas in GRID.items():
        for th in thetas:
            for T in TIMEOUTS_H:
                o, h = policy(gff, var, th, T)
                lm = load_metrics(gff, dff, o, h, [0, 1])
                ov, hv = policy(gv, var, th, T)
                at = attention_summary(outage_attention(gv, ev, ov, hv, [2]))
                rows.append({"var": var, "theta": th, "T_h": T,
                             "human_items_per_day": lm["human_items_per_day"],
                             "false_outage_per_year": lm["false_outage_per_year"],
                             "branch_feeder_no_realtime": at["branch_feeder_no_realtime"],
                             "single_no_realtime": at.get("single", {}).get("no_realtime_attention"),
                             "all_no_realtime": at["all"]["no_realtime_attention"],
                             "wait_h_median": at["all"]["wait_h_median_when_attended"]})
    ok = [r for r in rows if r["false_outage_per_year"] <= RULE["max_false_outage_per_year"]
          and r["branch_feeder_no_realtime"] <= RULE["max_unattended_branch_feeder"]]
    chosen_b = min(ok, key=lambda r: (r["human_items_per_day"], r["T_h"])) if ok else None
    # addendum C (declared deviation): (b') at most 2 points worse than version 1
    v1_bf = base["v1"]["branch_feeder_no_realtime"]
    ok_c = [r for r in rows if r["false_outage_per_year"] <= RULE["max_false_outage_per_year"]
            and r["branch_feeder_no_realtime"] <= v1_bf + RULE["max_unattended_branch_feeder"]]
    chosen = min(ok_c, key=lambda r: (r["human_items_per_day"], r["T_h"])) if ok_c else None
    out = {"stamp": stamp({"grid": GRID, "timeouts_h": TIMEOUTS_H, "rule": RULE},
                          "python -m shahid.cp11 select"),
           "data": "fault-free semiurb5 seed 1 weeks 0-1; CP5 validation episodes week 2",
           "v1_reference": base, "sweep": rows,
           "addendum_B": {"n_feasible": len(ok), "chosen": chosen_b,
                          "outcome": "infeasible: recommend version 1 alone" if not ok else "chosen"},
           "addendum_C_deviation": {"v1_branch_feeder_no_realtime": v1_bf,
                                    "n_feasible": len(ok_c), "chosen": chosen},
           "chosen": chosen}
    write_json("results/cp11_select.json", out)
    print("addendum B feasible", len(ok), "| addendum C feasible", len(ok_c), "chosen", chosen)
    print("v1", {k: base["v1"][k] for k in ["human_items_per_day", "false_outage_per_year"]},
          base["v1"]["branch_feeder_no_realtime"])


# ------------------------------------------------------------------ evaluate
def method_load(fam, weeks=None):
    """Task 1: human items = UNCERTAIN + OUTAGE verdicts per transformer-day, every method + IF."""
    gall = pd.read_parquet(REC / f"{fam}__groups.parquet")
    meta = gall[gall.method == "_meta"]
    days = {int(r.seed): float(r.verdict.split("=")[1]) for r in meta.itertuples()}
    d = n_days(days, weeks)
    res = {}
    for m in METHODS:
        x = gall[gall.method == m]
        if weeks:
            x = x[x.week.isin(weeks)]
        res[m] = {"outage_per_day": float((x.verdict == "OUTAGE").sum() / d),
                  "uncertain_per_day": float((x.verdict == "UNCERTAIN").sum() / d),
                  "human_items_per_day": float(x.verdict.isin(["OUTAGE", "UNCERTAIN"]).sum() / d)}
    tm = pd.read_parquet(REC / f"{fam}__cp11.parquet")
    tm = tm[tm.if_verdict.notna()]
    if weeks:
        tm = tm[((tm.t0 // 672) % 4).isin(weeks)]
    res["iforest"] = {"outage_per_day": float((tm.if_verdict == "OUTAGE").sum() / d),
                      "uncertain_per_day": 0.0,
                      "human_items_per_day": float((tm.if_verdict == "OUTAGE").sum() / d)}
    return res


def feeder_outcomes(fam):
    t = pd.read_parquet(REC / f"{fam}__episodes.parquet")
    p = REC / f"{fam}__iforest_episodes.parquet"
    if p.exists():
        t = pd.concat([t, pd.read_parquet(p)], ignore_index=True)
    res = {}
    for m, x in t.groupby("method"):
        o, c = x[x.cause == "OUTAGE"], x[x.cause == "COMMS_FAILURE"]
        w = lambda k, n: {"rate": k / n if n else None, "ci95": evaluate.wilson(k, n), "k": int(k)}
        res[m] = {"outage": {"n": len(o), "correct": w((o.verdict == "OUTAGE").sum(), len(o)),
                             "called_comms": w((o.verdict == "COMMS_FAILURE").sum(), len(o)),
                             "abstained": w((o.verdict == "UNCERTAIN").sum(), len(o)),
                             "never_detected": w((o.verdict == "MISSED").sum(), len(o))},
                  "comms": {"n": len(c), "correct": w((c.verdict == "COMMS_FAILURE").sum(), len(c)),
                            "called_outage": w((c.verdict == "OUTAGE").sum(), len(c)),
                            "abstained": w((c.verdict == "UNCERTAIN").sum(), len(c)),
                            "never_detected": w((c.verdict == "MISSED").sum(), len(c))},
                  "latency_median_intervals": float(x.latency_intervals.median())
                  if "latency_intervals" in x and x.latency_intervals.notna().any() else None}
    return res


def if_auc():
    g = pd.read_parquet(REC / "cp5__groups.parquet").query("method == 'bayes'")
    tm = pd.read_parquet(REC / "cp5__cp11.parquet")
    e = episodes("cp5")[["seed", "episode_id", "cause", "week"]]
    g = g[g.matched_episode >= 0].merge(tm[["seed", "onset", "if_score"]], on=["seed", "onset"])
    g = g.merge(e, left_on=["seed", "matched_episode"], right_on=["seed", "episode_id"],
                suffixes=("", "_e"))
    v = g[(g.week == 2) & g.if_score.notna()]
    y = (v.cause == "OUTAGE").to_numpy().astype(int)
    s = -v.if_score.to_numpy()  # higher = more anomalous = predicted outage
    auc = roc_auc_score(y, s)
    bs = []
    for _ in range(1000):
        i = RNG.integers(0, len(y), len(y))
        if y[i].min() != y[i].max():
            bs.append(roc_auc_score(y[i], s[i]))
    return {"split": "CP5 validation weeks (week 2), seeds 101-103, matched labelled episodes",
            "direction": "score = -IsolationForest.score_samples (higher = more anomalous), "
                         "positive class = OUTAGE", "n_outage": int(y.sum()),
            "n_comms": int(len(y) - y.sum()), "auc": float(auc),
            "auc_ci95": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))]}


def evaluate_all():
    sel = json.load(open("results/cp11_select.json"))
    ch = sel["chosen"]
    out = {"stamp": stamp({"chosen": ch}, "python -m shahid.cp11 evaluate"), "label": LABEL_V11,
           "chosen": ch}
    # Task 1
    out["task1_operator_load_all_methods"] = {
        f: method_load(f) for f in ["ff_semiurb5", "ff_urban6", "loss10_ff_semiurb5",
                                    "loss10_ff_urban6", "cp7_heldout_urban6", "cp7_dev_semiurb5",
                                    "loss10_semiurb5", "loss10_urban6"]}
    out["task1_feeder_outcomes"] = {f: feeder_outcomes(f) for f in ["feeder_semiurb5", "feeder_urban6"]}
    out["task1_if_auc"] = if_auc()
    if ch is None:
        write_json("results/cp11_eval.json", out)
        print("no feasible gate setting; version 1.1 not evaluated")
        return
    var, th, T = ch["var"], ch["theta"], ch["T_h"]
    ev = {}
    for fam, weeks in [("ff_semiurb5", None), ("ff_urban6", None), ("loss10_ff_semiurb5", None),
                       ("loss10_ff_urban6", None), ("ff_urban6", [3]), ("ff_semiurb5", [3])]:
        g, d = groups(fam)
        a = load_metrics(g, d, *v1_policy(g), weeks)
        b = load_metrics(g, d, *policy(g, var, th, T), weeks)
        ev[f"{fam}{'' if weeks is None else '/test_weeks'}"] = {"v1": a, "v1.1": b}
    for fam in sorted(p.name.split("__")[0] for p in REC.glob("ffx_*__cp11.parquet")):
        g, d = groups(fam)
        ev[fam] = {"v1": load_metrics(g, d, *v1_policy(g)),
                   "v1.1": load_metrics(g, d, *policy(g, var, th, T))}
    out["fault_free_and_load"] = ev
    # operator load on data WITH events (about one labelled event per transformer-day): the
    # selection objective only saw fault-free data, so this is reported separately
    evl = {}
    for fam in ["cp7_heldout_urban6", "cp7_dev_semiurb5", "loss10_semiurb5", "loss10_urban6",
                "feeder_semiurb5", "feeder_urban6"]:
        g, d = groups(fam)
        evl[fam] = {"v1": load_metrics(g, d, *v1_policy(g)),
                    "v1.1": load_metrics(g, d, *policy(g, var, th, T))}
    out["event_data_load"] = evl
    # Step 7: untouched grid rural3 (addendum B), test weeks, run once
    if (REC / "rural3_eps__cp11.parquet").exists() and (REC / "rural3_ff__cp11.parquet").exists():
        r3 = {}
        e = episodes("rural3_eps")
        for m in METHODS:
            em = pd.read_parquet(REC / "rural3_eps__episodes.parquet").query("method == @m")
            r = evaluate.rates(em[em.week == 3])
            r3[m] = {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                     for k, v in r.items()}
        g, d = groups("rural3_eps")
        a1 = outage_attention(g, e, *v1_policy(g), [3])
        a2 = outage_attention(g, e, *policy(g, var, th, T), [3])
        gf, df = groups("rural3_ff")
        r3["_v1_vs_v11"] = {
            "fault_free_v1": load_metrics(gf, df, *v1_policy(gf)),
            "fault_free_v1.1": load_metrics(gf, df, *policy(gf, var, th, T)),
            "events_v1": load_metrics(g, d, *v1_policy(g)),
            "events_v1.1": load_metrics(g, d, *policy(g, var, th, T)),
            "attention_v1": attention_summary(a1), "attention_v1.1": attention_summary(a2),
            "v11_episode_outcomes": episode_outcomes(g, e, policy(g, var, th, T)[0], [3])}
        out["untouched_grid_rural3"] = r3
    # pooled fault-free bound (original + extra observation seeds), per grid
    pooled = {}
    for grid, fams in [("semiurb5", ["ff_semiurb5"] + [f for f in ev if f.startswith("ffx_semiurb5")]),
                       ("urban6", ["ff_urban6"] + [f for f in ev if f.startswith("ffx_urban6")])]:
        for v in ["v1", "v1.1"]:
            k = sum(ev[f][v]["false_outage_verdicts"] for f in fams)
            yrs = sum(ev[f][v]["transformer_days"] for f in fams) / 365.25
            pooled[f"{grid}/{v}"] = {"false_outage_verdicts": k, "transformer_years": yrs,
                                     "per_year": k / yrs, "per_year_ci95": poisson_ci(k, yrs),
                                     "families": fams,
                                     "note": "extra seeds share customers with the original world"}
    out["fault_free_pooled"] = pooled
    # outages: attention and by size class
    att = {}
    for fam, weeks in [("cp7_heldout_urban6", [3]), ("cp7_dev_semiurb5", [3]),
                       ("feeder_semiurb5", [0, 1, 2, 3]), ("feeder_urban6", [0, 1, 2, 3]),
                       ("loss10_semiurb5", [0, 1, 2, 3]), ("loss10_urban6", [0, 1, 2, 3]),
                       ("cp6_nominal", [0, 1, 2]), ("cp6_tmeter_gain_0.02", [0, 1, 2]),
                       ("cp6_unmetered_profile_10.0kw", [0, 1, 2]),
                       ("cp6_hn_simultaneous_outage_comms", [0, 1, 2])]:
        g, d = groups(fam)
        e = episodes(fam)
        a1 = outage_attention(g, e, *v1_policy(g), weeks)
        a2 = outage_attention(g, e, *policy(g, var, th, T), weeks)
        # revised R3: outages version 1 closed automatically
        closed = a1.outcome == "comms_auto_closed"
        caught = a2[closed.to_numpy()]
        o2, _ = policy(g, var, th, T)
        att[fam] = {"weeks": weeks, "v1": attention_summary(a1), "v1.1": attention_summary(a2),
                    "v11_episode_outcomes": episode_outcomes(g, e, o2, weeks),
                    "r3_v1_auto_closed": int(closed.sum()),
                    "r3_v11_caught": int(caught.human_t.notna().sum()),
                    "r3_v11_caught_realtime": int(caught.realtime.sum()),
                    "r3_v11_wait_h": caught.wait_h.dropna().round(2).tolist(),
                    "deferred_wait_h_quantiles": a2[a2.outcome == "watch_escalated"].wait_h
                    .quantile([.1, .5, .9]).round(2).to_dict()}
    out["outage_attention"] = att
    write_json("results/cp11_eval.json", out)
    print(json.dumps({k: out[k] for k in ["chosen", "fault_free_pooled"]}, indent=1, default=str))


if __name__ == "__main__":
    {"select": select, "evaluate": evaluate_all}[sys.argv[1]]()
