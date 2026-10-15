"""Supervised-classifier comparison (docs/studies/classifier_comparison/PROTOCOL.md). Post-hoc,
SIMULATED. The frozen detector is not changed: its evidence (detect.evidence_table) is the input.

Run: python -m shahid.classifier_study features   (regenerates per-lead evidence for the protocol's
                                                  families; results/studies/classifier_comparison/features/)
     python -m shahid.classifier_study run        (train, select on validation, test once; summary.json)
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from shahid import detect, evaluate, scenario
from shahid.cp5_compare import inputs_of, split_of
from shahid.records import families, fitted_for, size_class
from shahid.world import grid_meta

OUT = Path("results/studies/classifier_comparison")
FEAT = OUT / "features"
FAMILIES = ["cp5", "ff_semiurb5", "cp7_heldout_urban6", "ff_urban6", "rural3_eps", "rural3_ff",
            "feeder_semiurb5", "feeder_urban6"]
LEADS = 5  # L = 0..4
EV = ["R", "M", "sd_O", "sd_C", "n_intervals", "gap0"]


def extract(name):
    """Per family: one row per silent group with the evidence at every lead, the frozen verdict, and
    the cell-level label; plus the labelled episodes with their matched group (registered rule)."""
    os.environ["SHAHID_SERIAL"] = "1"
    sims, fit_cfg, mode = families()[name]
    fitted, thr = fitted_for(fit_cfg, mode)
    meta = grid_meta(sims[0][1]["world"]["grid"])
    G, E, D = [], [], []
    for seed, cfg in sims:
        sim = scenario.simulate(cfg)
        inp = inputs_of(sim)
        ev = detect.evidence_table(inp, fitted)
        v = detect.decide_table(ev, "bayes", {**fitted, **thr["bayes"]})
        cells = sim["labels"]["cells"]
        out = cells[cells.cause == "OUTAGE"]
        outage_cells = set(zip(out.interval_start, out.meter_id.astype(str)))
        rows = []
        for gi, g in enumerate(ev):
            r = {"family": name, "seed": seed, "gid": gi, "onset": g["onset"], "n_meters": g["n_meters"],
                 "outage_share": sum((g["onset"], m) in outage_cells for m in g["meters"]) / g["n_meters"],
                 "frozen_verdict": v.at[gi, "verdict"], "frozen_latency": int(v.at[gi, "latency_intervals"])}
            for L, e in enumerate(g["evs"]):
                for k in EV:
                    r[f"{k}_{L}"] = e[k]
            rows.append(r)
        gt = pd.DataFrame(rows)
        if len(gt):
            gt["week"] = split_of(gt.onset)
        G.append(gt)
        ep = sim["labels"]["episodes"]
        if "cause" in ep:
            ep = ep[ep.cause.isin(["OUTAGE", "COMMS_FAILURE"])].reset_index(drop=True)
            idx = evaluate.match_episodes(v, ep) if len(v) else np.full(len(ep), -1)
            E.append(pd.DataFrame({"family": name, "seed": seed, "episode_id": ep.episode_id,
                                   "cause": ep.cause, "start": ep.start, "end": ep.end,
                                   "n_meters": ep.n_meters, "gid": idx, "week": split_of(ep.start),
                                   "size_class": [size_class(json.loads(m), meta, None) for m in ep.meters]}))
        D.append({"family": name, "seed": seed, "days": len(inp["trafo"]) / 96,
                  "n_meters_total": len(inp["meters"])})
    FEAT.mkdir(parents=True, exist_ok=True)
    pd.concat(G, ignore_index=True).to_parquet(FEAT / f"{name}__groups.parquet")
    if E:
        pd.concat(E, ignore_index=True).to_parquet(FEAT / f"{name}__episodes.parquet")
    pd.DataFrame(D).to_parquet(FEAT / f"{name}__days.parquet")
    return name


def features():
    todo = [f for f in FAMILIES if not (FEAT / f"{f}__groups.parquet").exists()]
    with ProcessPoolExecutor(max(1, min(2, len(todo)))) as ex:  # heat: at most 2 workers
        for n in ex.map(extract, todo):
            print("done", n, flush=True)



# ---------------------------------------------------------------------------------------------------
# Training, selection and test (protocol sections 3 to 8)
FEATURES = ["R", "M", "sd_O", "sd_C", "n_intervals", "gap0", "n_meters", "hour_sin", "hour_cos",
            "visible_share", "z_outage", "z_comms"]
ABLATED = ["R", "visible_share", "z_outage", "z_comms"]
FEATURES_ABL = [f for f in FEATURES if f not in ABLATED]
FORBIDDEN = {"outage_share", "label", "frozen_verdict", "frozen_latency", "cause", "episode_id"}
DEV = ["cp5", "ff_semiurb5"]
TEST = {"urban6": (["cp7_heldout_urban6", "ff_urban6"], [3]),
        "rural3": (["rural3_eps", "rural3_ff"], [3]),
        "feeder_semiurb5": (["feeder_semiurb5"], [0, 1, 2, 3]),
        "feeder_urban6": (["feeder_urban6"], [0, 1, 2, 3])}
LOWER = [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5]
UPPER = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99]
LIMITS = {"missed": 0.05, "false_outage": 0.05, "ff_per_meter_day": 0.001}
SEED = 2026
K = 2


def feature_frame(g, lead):
    """Observed-evidence features at one lead per row (lead: int or array). Never reads labels."""
    lead = np.broadcast_to(np.asarray(lead), (len(g),))
    pick = lambda k: g[[f"{k}_{L}" for L in range(LEADS)]].to_numpy()[np.arange(len(g)), lead]
    f = pd.DataFrame({k: pick(k) for k in EV}, index=g.index)
    f["n_meters"] = g.n_meters.to_numpy()
    h = (pd.DatetimeIndex(g.onset).hour + pd.DatetimeIndex(g.onset).minute / 60).to_numpy()
    f["hour_sin"], f["hour_cos"] = np.sin(2 * np.pi * h / 24), np.cos(2 * np.pi * h / 24)
    f["visible_share"] = f.R / np.maximum(f.M.abs(), 0.01) * np.sign(f.M.where(f.M != 0, 1))
    f["z_outage"] = f.R / f.sd_O
    f["z_comms"] = (f.R - f.M) / f.sd_C
    assert not (set(f.columns) & FORBIDDEN)
    return f[FEATURES]


def load():
    G = {f: pd.read_parquet(FEAT / f"{f}__groups.parquet") for f in FAMILIES}
    E = {f: pd.read_parquet(FEAT / f"{f}__episodes.parquet") for f in FAMILIES
         if (FEAT / f"{f}__episodes.parquet").exists()}
    D = {f: pd.read_parquet(FEAT / f"{f}__days.parquet") for f in FAMILIES}
    for g in G.values():
        g["label"] = (g.outage_share > 0.5).astype(int)
    return G, E, D


def split_frames(G):
    """Training and validation rows: development network only (cp5, ff_semiurb5)."""
    dev = pd.concat([G[f] for f in DEV], ignore_index=True)
    return dev[dev.week.isin([0, 1])].reset_index(drop=True), dev[dev.week == 2].reset_index(drop=True)


def models():
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    return {
        "logistic_regression": (lambda p, s: make_pipeline(StandardScaler(), LogisticRegression(
            C=p["C"], class_weight="balanced", max_iter=5000)), [{"C": c} for c in [0.01, 0.1, 1, 10]], [0]),
        "gradient_boosting": (lambda p, s: HistGradientBoostingClassifier(
            max_depth=p["max_depth"], learning_rate=p["learning_rate"], max_iter=300, early_stopping=True,
            validation_fraction=0.1, class_weight="balanced", random_state=s),
            [{"max_depth": d, "learning_rate": lr} for d in [3, None] for lr in [0.05, 0.1]], [0, 1, 2]),
        "mlp": (lambda p, s: make_pipeline(StandardScaler(), MLPClassifier(
            hidden_layer_sizes=p["hidden"], alpha=p["alpha"], early_stopping=True, max_iter=500,
            random_state=s)), [{"hidden": h, "alpha": a} for h in [(16,), (32, 16)] for a in [1e-4, 1e-2]],
            [0, 1, 2])}


def oversample(X, y, seed):
    rng = np.random.default_rng(seed)
    pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    small, big = (pos, neg) if len(pos) < len(neg) else (neg, pos)
    idx = np.concatenate([big, small, rng.choice(small, len(big) - len(small), replace=True)])
    return X.iloc[idx], y[idx]


def fit(name, params, seed, X, y):
    m = models()[name][0](params, seed)
    if name == "mlp":
        X, y = oversample(X, y, seed)
    return m.fit(X, y)


def calibrator(p, y):
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression
    if min(y.sum(), len(y) - y.sum()) < 200:
        lr = LogisticRegression().fit(np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))[:, None], y)
        return "platt", lambda q: lr.predict_proba(np.log(np.clip(q, 1e-6, 1 - 1e-6) / (1 - np.clip(q, 1e-6, 1 - 1e-6)))[:, None])[:, 1]
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(p, y)
    return "isotonic", iso.predict


def lead_probs(model, cal, g, cols):
    return np.column_stack([cal(model.predict_proba(feature_frame(g, L)[cols])[:, 1]) for L in range(LEADS)])


def decide(P, lo, up):
    """Sequential band rule over leads; returns verdicts and latency (intervals)."""
    n = len(P)
    verdict = np.full(n, "UNCERTAIN", dtype=object)
    lat = np.full(n, K + LEADS - 1)
    open_ = np.ones(n, bool)
    for L in range(LEADS):
        o = open_ & (P[:, L] >= up)
        c = open_ & (P[:, L] <= lo) & ~o
        verdict[o], verdict[c] = "OUTAGE", "COMMS_FAILURE"
        lat[o | c] = K + L
        open_ &= ~(o | c)
    return verdict, lat


def n_days_in(days, weeks):
    return float(sum(((np.arange(int(round(d))) // 7) % 4 == np.array(weeks)[:, None]).any(0).sum()
                     for d in days))


def evaluate_set(G, E, D, fams, weeks, verdicts):
    """Episode metrics, fault-free rates and latency for one set of families. verdicts: dict family ->
    (verdict array aligned to G[family] rows, latency array)."""
    tabs, ff_k, ff_md, ff_days = [], 0, 0.0, 0.0
    for f in fams:
        v, lat = verdicts[f]
        g = G[f]
        if f in E:
            e = E[f][E[f].week.isin(weeks)].copy()
            key = {(s, i): k for k, (s, i) in enumerate(zip(g.seed, g.gid))}
            idx = [key.get((s, i)) if i >= 0 else None for s, i in zip(e.seed, e.gid)]
            e["verdict"] = [v[k] if k is not None else "MISSED" for k in idx]
            e["latency"] = [lat[k] if k is not None else np.nan for k in idx]
            tabs.append(e)
        else:  # fault-free year: every OUTAGE verdict is false
            m = g.week.isin(weeks).to_numpy()
            ff_k += int((v[m] == "OUTAGE").sum())
            d = n_days_in(D[f].days, weeks)
            ff_days += d
            ff_md += d * float(D[f].n_meters_total.iloc[0])
    res = {}
    if tabs:
        t = pd.concat(tabs, ignore_index=True)
        dec = t.verdict.isin(["OUTAGE", "COMMS_FAILURE"])
        o, c = t[t.cause == "OUTAGE"], t[t.cause == "COMMS_FAILURE"]
        w = lambda k, n: {"rate": k / n if n else None, "ci95": evaluate.wilson(int(k), int(n))}
        res = {"n_outage": len(o), "n_comms": len(c),
               "coverage": w(dec.sum(), len(t)), "outage_recall": w((o.verdict == "OUTAGE").sum(), len(o)),
               "comms_recall": w((c.verdict == "COMMS_FAILURE").sum(), len(c)),
               "false_outage_rate": w((c.verdict == "OUTAGE").sum(), len(c)),
               "missed_outage_rate": w(o.verdict.isin(["COMMS_FAILURE", "MISSED"]).sum(), len(o)),
               "abstention_rate": float((t.verdict == "UNCERTAIN").mean()),
               "accuracy_when_decided": w((t.verdict == t.cause)[dec].sum(), dec.sum()),
               "latency_median_intervals": float(t.latency[dec].median()) if dec.any() else None,
               "_table": t}
    if ff_md:
        res["fault_free"] = {"false_outages": ff_k, "per_meter_day": ff_k / ff_md,
                             "per_transformer_year": ff_k / ff_days * 365.25,
                             "transformer_days": ff_days}
    return res


def feasible(m):
    return (m["missed_outage_rate"]["rate"] <= LIMITS["missed"]
            and m["false_outage_rate"]["rate"] <= LIMITS["false_outage"]
            and m["fault_free"]["per_meter_day"] <= LIMITS["ff_per_meter_day"])


def strip(m):
    return {k: v for k, v in m.items() if not k.startswith("_")}


def bootstrap_diff(ta, tb, n=1000, seed=SEED):
    """Paired bootstrap over episodes (same rows), stratified by cause: a minus b."""
    rng = np.random.default_rng(seed)
    a, b = ta.reset_index(drop=True), tb.reset_index(drop=True)
    strata = [np.flatnonzero(a.cause == c) for c in ["OUTAGE", "COMMS_FAILURE"]]
    stat = {"coverage": lambda t: t.verdict.isin(["OUTAGE", "COMMS_FAILURE"]).mean(),
            "false_outage_rate": lambda t: (t[t.cause == "COMMS_FAILURE"].verdict == "OUTAGE").mean(),
            "missed_outage_rate": lambda t: t[t.cause == "OUTAGE"].verdict.isin(["COMMS_FAILURE", "MISSED"]).mean()}
    out = {}
    for k, fn in stat.items():
        bs = []
        for _ in range(n):
            ix = np.concatenate([s[rng.integers(0, len(s), len(s))] for s in strata])
            bs.append(fn(a.iloc[ix]) - fn(b.iloc[ix]))
        out[k] = {"diff": float(fn(a) - fn(b)), "ci95": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))]}
    return out


def baseline_metrics(name, fams, weeks):
    """The four simple baselines on the same episodes, from the stored records (same simulations)."""
    tabs = []
    for f in fams:
        p = Path(f"results/records/{f}__episodes.parquet")
        if p.exists():
            t = pd.read_parquet(p)
            t = t[(t.method == name) & t.week.isin(weeks)]
            if "cause" in t and len(t):
                tabs.append(t)
    if not tabs:
        return None
    t = pd.concat(tabs, ignore_index=True)
    dec = t.verdict.isin(["OUTAGE", "COMMS_FAILURE"])
    o, c = t[t.cause == "OUTAGE"], t[t.cause == "COMMS_FAILURE"]
    return {"coverage": float(dec.mean()), "outage_recall": float((o.verdict == "OUTAGE").mean()),
            "comms_recall": float((c.verdict == "COMMS_FAILURE").mean()),
            "false_outage_rate": float((c.verdict == "OUTAGE").mean()),
            "missed_outage_rate": float(o.verdict.isin(["COMMS_FAILURE", "MISSED"]).mean()),
            "accuracy_when_decided": float((t.verdict == t.cause)[dec].mean())}


def run():
    import warnings
    from sklearn.metrics import log_loss, roc_auc_score
    from shahid.stamp import stamp, write_json
    warnings.filterwarnings("ignore")
    G, E, D = load()
    tr, va = split_frames(G)
    rng = np.random.default_rng(SEED)
    Ltr, Lva = rng.integers(0, LEADS, len(tr)), rng.integers(0, LEADS, len(va))
    Xtr, Xva = feature_frame(tr, Ltr), feature_frame(va, Lva)
    ytr, yva = tr.label.to_numpy(), va.label.to_numpy()
    test_g = pd.concat([G[f][G[f].week == 3] for f in TEST["urban6"][0]], ignore_index=True)
    Xte = feature_frame(test_g, rng.integers(0, LEADS, len(test_g)))
    yte = test_g.label.to_numpy()
    res = {"stamp": stamp({"features": FEATURES, "ablated": ABLATED, "limits": LIMITS}, "python -m shahid.classifier_study run"),
           "label": "post-hoc, SIMULATED; frozen method unchanged",
           "data": {"train_groups": len(tr), "train_outage": int(ytr.sum()), "val_groups": len(va),
                    "val_outage": int(yva.sum()),
                    "groups_outage_share_20_80": {f: int(((g.outage_share > 0.2) & (g.outage_share < 0.8)).sum())
                                                  for f, g in G.items()},
                    "groups_total": {f: len(g) for f, g in G.items()}},
           "frozen": {}, "baselines": {}, "models": {}}
    # frozen method on every set
    fz = {f: (G[f].frozen_verdict.to_numpy(), G[f].frozen_latency.to_numpy()) for f in G}
    res["frozen"]["validation"] = strip(evaluate_set(G, E, D, DEV, [2], fz))
    frozen_tabs = {}
    for k, (fams, weeks) in TEST.items():
        m = evaluate_set(G, E, D, fams, weeks, fz)
        frozen_tabs[k] = m.get("_table")
        res["frozen"][k] = strip(m)
        res["baselines"][k] = {b: baseline_metrics(b, fams, weeks) for b in ["naive", "step", "count", "structure"]}
    preds = []
    for name, (_, grid, seeds) in models().items():
        for featset, cols in [("full", FEATURES), ("ablation", FEATURES_ABL)]:
            key = f"{name}/{featset}"
            # hyperparameters by validation log-loss (seed 0)
            scores = []
            for p in grid:
                m = fit(name, p, 0, Xtr[cols], ytr)
                scores.append(log_loss(yva, np.clip(m.predict_proba(Xva[cols])[:, 1], 1e-6, 1 - 1e-6)))
            best = grid[int(np.argmin(scores))]
            res["models"][key] = {"params": {k: str(v) for k, v in best.items()},
                                  "val_logloss_grid": [float(s) for s in scores], "seeds": {}}
            for s in seeds:
                m = fit(name, best, s, Xtr[cols], ytr)
                praw = m.predict_proba(Xva[cols])[:, 1]
                cal_kind, cal = calibrator(praw, yva)
                P = {f: lead_probs(m, cal, G[f], cols) for f in G}
                # band selection on validation
                sweep = []
                for lo in LOWER:
                    for up in UPPER:
                        if lo >= up and not (lo == up == 0.5):
                            continue
                        vv = {f: decide(P[f], lo, up) for f in DEV}
                        mv = evaluate_set(G, E, D, DEV, [2], vv)
                        sweep.append((lo, up, mv))
                ok = [x for x in sweep if feasible(x[2])]
                if ok:
                    lo, up, mv = min(ok, key=lambda x: (x[2]["abstention_rate"], x[0], -x[1]))
                else:
                    lo, up, mv = min(sweep, key=lambda x: x[2]["false_outage_rate"]["rate"] + x[2]["missed_outage_rate"]["rate"])
                vt = {f: decide(P[f], lo, up) for f in G}
                r = {"calibration": cal_kind, "band": [lo, up], "feasible_on_validation": bool(ok),
                     "validation": strip(mv)}
                pte_raw = m.predict_proba(Xte[cols])[:, 1]
                ptr_raw = m.predict_proba(Xtr[cols])[:, 1]
                r["fit"] = {"train": {"logloss": float(log_loss(ytr, np.clip(ptr_raw, 1e-6, 1 - 1e-6))),
                                      "auc": float(roc_auc_score(ytr, ptr_raw))},
                            "validation": {"logloss": float(log_loss(yva, np.clip(praw, 1e-6, 1 - 1e-6))),
                                           "auc": float(roc_auc_score(yva, praw))},
                            "test_urban6": {"logloss": float(log_loss(yte, np.clip(pte_raw, 1e-6, 1 - 1e-6))),
                                            "auc": float(roc_auc_score(yte, pte_raw))}}
                for k, (fams, weeks) in TEST.items():
                    mt = evaluate_set(G, E, D, fams, weeks, vt)
                    if k in ("urban6", "rural3") and frozen_tabs[k] is not None:
                        r.setdefault("paired_vs_frozen", {})[k] = bootstrap_diff(mt["_table"], frozen_tabs[k])
                    r[k] = strip(mt)
                # Brier and reliability on urban6 test groups, probability at the decision lead
                tg = pd.concat([G[f][G[f].week == 3].assign(_f=f) for f in TEST["urban6"][0]])
                pf = np.concatenate([P[f][G[f].week.to_numpy() == 3][np.arange((G[f].week == 3).sum()),
                                     vt[f][1][G[f].week.to_numpy() == 3] - K] for f in TEST["urban6"][0]])
                yl = tg.label.to_numpy()
                bins = np.linspace(0, 1, 11)
                r["brier_urban6"] = float(np.mean((pf - yl) ** 2))
                r["reliability_urban6"] = [{"bin": f"{bins[i]:.1f}-{bins[i + 1]:.1f}", "n": int(mk.sum()),
                                            "mean_p": float(pf[mk].mean()) if mk.any() else None,
                                            "frac_outage": float(yl[mk].mean()) if mk.any() else None}
                                           for i in range(10) for mk in [(pf >= bins[i]) & ((pf < bins[i + 1]) | (i == 9))]]
                res["models"][key]["seeds"][str(s)] = r
                for f in ["cp7_heldout_urban6", "rural3_eps"]:
                    w3 = G[f].week.to_numpy() == 3
                    preds.append(pd.DataFrame({"model": key, "seed": s, "family": f, "group_seed": G[f].seed[w3],
                                               "gid": G[f].gid[w3], "verdict": vt[f][0][w3],
                                               "latency": vt[f][1][w3], "label": G[f].label[w3]}))
                print(key, "seed", s, "band", (lo, up), "feasible", bool(ok),
                      "urban6 cov", round(r["urban6"]["coverage"]["rate"], 3),
                      "fo", round(r["urban6"]["false_outage_rate"]["rate"], 3),
                      "miss", round(r["urban6"]["missed_outage_rate"]["rate"], 3), flush=True)
    # explanations
    lr = fit("logistic_regression", {"C": float(res["models"]["logistic_regression/full"]["params"]["C"])}, 0, Xtr, ytr)
    res["explanations"] = {"logistic_regression_coefficients_standardised":
                           dict(zip(FEATURES, map(float, lr[-1].coef_[0])))}
    try:
        import shap
        p = res["models"]["gradient_boosting/full"]["params"]
        hgb = fit("gradient_boosting", {"max_depth": None if p["max_depth"] == "None" else int(p["max_depth"]),
                                        "learning_rate": float(p["learning_rate"])}, 0, Xtr, ytr)
        sample = Xva.sample(min(2000, len(Xva)), random_state=0)
        sv = shap.TreeExplainer(hgb).shap_values(sample)
        res["explanations"]["gradient_boosting_mean_abs_shap"] = dict(zip(FEATURES, map(float, np.abs(sv).mean(0))))
        res["explanations"]["shap_version"] = shap.__version__
    except Exception as e:  # pragma: no cover  (protocol section 8 fallback)
        from sklearn.inspection import permutation_importance
        res["explanations"]["shap_error"] = repr(e)
        pi = permutation_importance(hgb, Xva, yva, scoring="neg_log_loss", n_repeats=5, random_state=0)
        res["explanations"]["gradient_boosting_permutation_importance"] = dict(zip(FEATURES, map(float, pi.importances_mean)))
    # shuffled-label control
    yperm = np.random.default_rng(SEED).permutation(ytr)
    ctrl = {}
    for name, p in [("logistic_regression", {"C": 1}), ("gradient_boosting", {"max_depth": 3, "learning_rate": 0.1})]:
        m = fit(name, p, 0, Xtr, yperm)
        ctrl[name] = {"val_auc": float(roc_auc_score(yva, m.predict_proba(Xva)[:, 1]))}
    res["shuffled_label_control"] = ctrl
    res["hypotheses"] = hypotheses(res)
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", res)
    pd.concat(preds, ignore_index=True).to_parquet(OUT / "test_predictions.parquet")
    figures(res)
    print("written", OUT / "summary.json")


def hypotheses(res):
    fz = res["frozen"]["urban6"]
    b = res["baselines"]["urban6"]
    best_acc = max(b["count"]["accuracy_when_decided"], b["structure"]["accuracy_when_decided"])
    best_err = min(b["count"]["false_outage_rate"] + b["count"]["missed_outage_rate"],
                   b["structure"]["false_outage_rate"] + b["structure"]["missed_outage_rate"])
    out = {"H-A": {}, "H-B": {}, "H-C": {}}
    for key, m in res["models"].items():
        for s, r in m["seeds"].items():
            u, ru = r["urban6"], r["rural3"]
            safe_u = (u["missed_outage_rate"]["rate"] <= LIMITS["missed"] and u["false_outage_rate"]["rate"] <= LIMITS["false_outage"]
                      and u["fault_free"]["per_meter_day"] <= LIMITS["ff_per_meter_day"])
            if key.endswith("/full"):
                beats = safe_u and u["coverage"]["rate"] > fz["coverage"]["rate"]
                out["H-A"][f"{key}/seed{s}"] = {"meets_limits": bool(safe_u), "coverage": u["coverage"]["rate"],
                                                "frozen_coverage": fz["coverage"]["rate"], "beats_frozen": bool(beats)}
                out["H-C"][f"{key}/seed{s}"] = {
                    "holds": bool(ru["false_outage_rate"]["ci95"][1] <= 0.05 and ru["missed_outage_rate"]["ci95"][1] <= 0.05
                                  and ru["fault_free"]["per_meter_day"] <= LIMITS["ff_per_meter_day"]),
                    "false_outage_upper": ru["false_outage_rate"]["ci95"][1], "missed_upper": ru["missed_outage_rate"]["ci95"][1],
                    "ff_per_meter_day": ru["fault_free"]["per_meter_day"]}
            else:
                acc = u["accuracy_when_decided"]["rate"] or 0
                err = u["false_outage_rate"]["rate"] + u["missed_outage_rate"]["rate"]
                holds = (not r["feasible_on_validation"]) or acc <= best_acc or err >= best_err
                out["H-B"][f"{key}/seed{s}"] = {"holds": bool(holds), "feasible_on_validation": r["feasible_on_validation"],
                                                "accuracy": acc, "error_sum": err, "best_structure_accuracy": best_acc,
                                                "best_structure_error_sum": best_err}
    out["H-A_supported"] = not any(v["beats_frozen"] for v in out["H-A"].values())
    out["H-B_supported"] = all(v["holds"] for v in out["H-B"].values())
    out["H-C_supported"] = all(v["holds"] for v in out["H-C"].values())
    return out


def figures(res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 4))
    fz = res["frozen"]["urban6"]
    ax.plot(fz["coverage"]["rate"], fz["false_outage_rate"]["rate"] + fz["missed_outage_rate"]["rate"], "k*", ms=12,
            label="frozen likelihood-ratio test")
    for b, v in res["baselines"]["urban6"].items():
        ax.plot(v["coverage"], v["false_outage_rate"] + v["missed_outage_rate"], "s", color="#999999", ms=5)
        ax.annotate(b, (v["coverage"], v["false_outage_rate"] + v["missed_outage_rate"]), fontsize=6)
    cols = {"logistic_regression": "#1f6fb4", "gradient_boosting": "#d9822b", "mlp": "#3a9a4a"}
    for key, m in res["models"].items():
        name, fs = key.split("/")
        for s, r in m["seeds"].items():
            u = r["urban6"]
            ax.plot(u["coverage"]["rate"], u["false_outage_rate"]["rate"] + u["missed_outage_rate"]["rate"],
                    "o" if fs == "full" else "x", color=cols[name],
                    label=f"{name} ({fs})" if s == "0" else None)
    ax.set(xlabel="coverage (decided / all episodes)", ylabel="false-outage + missed-outage rate",
           title="Held-out urban network, test weeks (SIMULATED)", xlim=(0, 1.02))
    ax.legend(frameon=False, fontsize=6)
    fig.tight_layout()
    fig.savefig(OUT / "coverage_vs_safety.png", dpi=200)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot([0, 1], [0, 1], "k:", lw=0.8)
    for key, m in res["models"].items():
        if not key.endswith("/full"):
            continue
        rel = [x for x in m["seeds"]["0"]["reliability_urban6"] if x["n"]]
        ax.plot([x["mean_p"] for x in rel], [x["frac_outage"] for x in rel], "o-", ms=3, label=key.split("/")[0])
    ax.set(xlabel="predicted outage probability (calibrated)", ylabel="observed outage share",
           title="Reliability, held-out urban test groups (seed 0, SIMULATED)")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "reliability.png", dpi=200)


if __name__ == "__main__":
    {"features": features, "run": run}[sys.argv[1]]()
