"""Protocol 01 (and 04 with --split): size-dependent prior (P1a), learned combination (P1b), selection
on development validation by rule v3, escalating-gate policy rows. Version 1 untouched.

Run: python -m shahid.p1_prior [--split]
  writes results/p1/p1_dev.json and results/p1/p1_params.json  (--split: p15_dev.json, p15_params.json)
Needs the development cache (python -m shahid.p2cache).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from shahid import p2eval as E
from shahid.p2cache import load
from shahid.stamp import stamp, write_json

OUT = Path("results/p1")
BANDS = [0.005, 0.01, 0.02, 0.03, 0.05, 0.1, 0.2]
EVENT_SEEDS = [("cp5", s) for s in (101, 102, 103)]
FF = [("ff_semiurb5", 1)]
FEEDER = [("feeder_semiurb5", s) for s in (401, 402)]
TRAIN, VAL = [0, 1], [2]
T0 = pd.Timestamp("2016-01-01")


def groups_of(keys, mode):
    items = []
    for fam, s in keys:
        it = load(fam, s)
        it["groups"] = it["groups"][it["groups"]["mode"] == mode].reset_index(drop=True)
        items.append(it)
    return items


def training_rows(items):
    g = pd.concat([it["groups"] for it in items], ignore_index=True)
    return g[g.week.isin(TRAIN) & g.truth.isin(["OUTAGE", "COMMS_FAILURE"])].reset_index(drop=True)


def fit_prior(tr):
    """P1a: P(comms | size bin), Laplace +1/+1, on training groups."""
    b = E.size_bin(tr.n_meters.to_numpy())
    c = (tr.truth == "COMMS_FAILURE").to_numpy()
    return [float((c[b == k].sum() + 1) / ((b == k).sum() + 2)) for k in range(len(E.SIZE_BINS))]


def prior_post(pi):
    pi = np.array(pi)

    def f(g, L):
        p = pi[E.size_bin(g.n_meters.to_numpy())]
        return E.sigmoid(E.llr(g, L) + np.log(p / (1 - p)))
    return f


def feats(g, L):
    x = np.clip(E.llr(g, L), -50, 50)
    ln = np.log(g.n_meters.to_numpy())
    return np.column_stack([x, ln, x * ln])


def fit_lr(tr):
    """P1b: logistic regression of the true cause on [llr, log n, llr*log n], one row per group and lead."""
    X = np.vstack([feats(tr, L) for L in range(E.L_MAX + 1)])
    y = np.tile((tr.truth == "COMMS_FAILURE").to_numpy(), E.L_MAX + 1)
    m = LogisticRegression(C=1.0, max_iter=1000).fit(X, y)
    return {"coef": m.coef_[0].tolist(), "intercept": float(m.intercept_[0])}


def lr_post(par):
    w, b = np.array(par["coef"]), par["intercept"]
    return lambda g, L: E.sigmoid(feats(g, L) @ w + b)


def evaluate_val(events, ffs, post, band):
    tabs = [E.episode_tab(it, it["groups"], E.decide(it["groups"], post, band), VAL) for it in events]
    tab = pd.concat(tabs, ignore_index=True)
    ff = E.fault_free(ffs, [E.decide(it["groups"], post, band) for it in ffs], VAL)
    return tab, ff


def sweep(events, ffs, post):
    rows = []
    for b in BANDS:
        tab, ff = evaluate_val(events, ffs, post, b)
        r = E.summarise(tab)
        rows.append({"band": b, **{k: r[k] for k in ("missed_outage_rate", "false_outage_rate", "abstention_rate",
                                                       "outage_recall", "comms_recall", "accuracy_when_decided")},
                     "ff_per_meter_day": ff["per_meter_day"], "ff_per_transformer_year": ff["per_transformer_year"],
                     "ff_k": ff["k"], "feasible": bool(E.feasible(r, ff))})
    ok = [r for r in rows if r["feasible"]]
    return rows, (min(ok, key=lambda r: r["abstention_rate"]) if ok else None)


def gate_rows(feeders, ffs, cands):
    """Escalating-gate policy rows (protocol 01) on development data, all weeks; descriptive."""
    out = {}
    for name, post, band, gate, esc in cands:
        lost = n_out = no_rt = 0
        for it in feeders:
            g = it["groups"]
            d = E.decide(g, post, band)
            o, ht = E.policy(g, d, gate, esc)
            ep = it["episodes"]
            pos = dict(zip(g.matched_episode[g.matched_episode >= 0].astype(int), g.index[g.matched_episode >= 0]))
            for e in ep[ep.cause == "OUTAGE"].itertuples():
                n_out += 1
                i = pos.get(int(e.episode_id))
                end = (e.end - T0) / pd.Timedelta(minutes=15)
                lost += i is not None and o[i] == "watch_closed_no_verdict"
                no_rt += i is None or not (ht[i] < end)
        items, days, fo = 0, 0.0, 0
        for it in ffs:
            g = it["groups"]
            d = E.decide(g, post, band)
            o, _ = E.policy(g, d, gate, esc)
            items += int(np.isin(o, list(E.HUMAN)).sum())
            fo += int((o == "outage_verdict").sum())
            days += len(it["row_weeks"]) / 96
        out[name] = {"whole_feeder_outages": n_out, "closed_no_verdict": int(lost),
                     "without_real_time_attention": int(no_rt), "human_items_per_transformer_day": items / days,
                     "false_outage_verdicts_per_transformer_year": fo / days * 365}
    return out


def main(argv):
    mode = "split" if "--split" in argv else "v1"
    tag = "p15" if mode == "split" else "p1"
    OUT.mkdir(parents=True, exist_ok=True)
    events, ffs = groups_of(EVENT_SEEDS, mode), groups_of(FF, mode)
    tr = training_rows(events + ffs)
    pi, lr = fit_prior(tr), fit_lr(tr)
    cands = {"P1a": prior_post(pi), "P1b": lr_post(lr)}
    res = {"stamp": stamp({"protocol": "docs/process/protocols/01_p1_size_prior.md", "mode": mode,
                           "bands": BANDS, "train_weeks": TRAIN, "val_weeks": VAL},
                          f"python -m shahid.p1_prior{' --split' if mode == 'split' else ''}"),
           "label": "development, selection data", "mode": mode, "n_training_groups": len(tr),
           "prior_by_size_bin": dict(zip([f"{a}-{b}" for a, b in E.SIZE_BINS], pi)), "lr": lr}
    v1rows, v1best = sweep(events, ffs, E.v1_posterior)
    res["v1_at_frozen_band"] = next(r for r in v1rows if r["band"] == 0.03)
    chosen = {}
    for k, post in cands.items():
        rows, best = sweep(events, ffs, post)
        res[k] = {"sweep": rows, "chosen": best}
        if best:
            chosen[k] = best
    if chosen:
        pick = min(chosen, key=lambda k: (chosen[k]["abstention_rate"], k != "P1a"))
        res["frozen"] = {"candidate": pick, "band": chosen[pick]["band"]}
    else:
        res["frozen"] = None
        print("no feasible P1 candidate: recommend version 1", flush=True)
    if mode == "v1":  # the gate is a policy layer: its v1 rows are reported even when no P1 is frozen
        rows = [("v1", E.v1_posterior, 0.03, False, False), ("v1+gate-close", E.v1_posterior, 0.03, True, False),
                ("v1+gate-escalate", E.v1_posterior, 0.03, True, True)]
        if res["frozen"]:
            fb = res["frozen"]
            post = cands[fb["candidate"]]
            rows += [("P1", post, fb["band"], False, False), ("P1+gate-escalate", post, fb["band"], True, True)]
        res["gate_rows_dev_all_weeks"] = gate_rows(groups_of(FEEDER, mode), ffs, rows)
    write_json(OUT / f"{tag}_dev.json", res)
    write_json(OUT / f"{tag}_params.json", {"stamp": res["stamp"], "mode": mode, "frozen": res["frozen"],
                                            "prior_by_size_bin": pi, "lr": lr})
    print(json.dumps({"frozen": res["frozen"], "v1": res["v1_at_frozen_band"]}, default=str), flush=True)
    for k in cands:
        print(k, res[k]["chosen"], flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
