"""Isolation Forest baseline (CP10 Task 6, added after CP7; time-boxed). Origin: REUSED sklearn.

Per silent group (same grouping and decision time as the baselines, K = 2, L = 2), features from
OBSERVED data only:
  log(1 + n_meters), sin/cos hour, transformer step at onset (normalised), naive expected energy
  of the group (same-slot median), naive visible residual (transformer - reporting meters - recent gap)
The forest is fitted on silent groups of the grid's fault-free year, training weeks only (ordinary
data loss = "normal"). Mapping (best effort, chosen on CP5 validation weeks only): a group whose
anomaly score is below the q-quantile of the training scores is called OUTAGE, otherwise
COMMS_FAILURE. q is chosen to maximise the balanced correct-cause rate on validation; the same q is
applied on the held-out grid with a forest refitted on that grid's fault-free training weeks.

Run: python -m shahid.iforest   (writes results/iforest.json)
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score

from shahid import evaluate, scenario
from shahid.cp5_compare import inputs_of, split_of
from shahid.detect import STEP, arrays, silent_groups, slot_history
from shahid.stamp import stamp, write_json

CFG = {"K": 2, "L": 2, "H": 14, "q_grid": [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3],
       "dev": "1-LV-semiurb5--0-sw", "held": "1-LV-urban6--0-sw",
       "val_seeds": [101, 102, 103], "test_seeds": [301, 302, 303], "random_state": 0}
FEATS = ["log_n", "hsin", "hcos", "dT", "mu", "r"]


def features(inputs):
    index, meters, E, A, T = arrays(inputs)
    K, L, H = CFG["K"], CFG["L"], CFG["H"]
    scale = np.convolve(np.abs(T), np.ones(96) / 96, mode="same") + 1e-6
    rows = []
    for t0, group in silent_groups(A, K).items():
        tau = t0 + K + L
        if t0 < 96 * H + 1 or tau > len(T):
            continue
        off = t0 - 96 * H - 1
        known = A[off:tau] <= tau
        Ek = np.where(known, E[off:tau], np.nan)
        t0l = t0 - off
        w = np.arange(t0l, tau - off)
        mu_all = np.nanmedian(slot_history(Ek, w, H), 1)
        mu = np.nansum(mu_all[:, group])
        full = known[t0l - 96:t0l].all(1)
        gaps = (T[off:tau][t0l - 96:t0l] - np.nansum(Ek[t0l - 96:t0l], 1))[full]
        gap0 = np.median(gaps) if full.any() else 0.0
        other = ~known[w]
        other[:, group] = False
        r = (T[off:tau][w] - np.nansum(Ek[w], 1) - gap0
             - np.where(other, np.nan_to_num(mu_all), 0).sum(1)).sum()
        h = index[t0].hour + index[t0].minute / 60
        rows.append({"onset": index[t0], "decided_at": index[0] + STEP * tau,
                     "latency_intervals": tau - t0, "n_meters": len(group),
                     "meters": [meters[g] for g in group], "log_n": np.log1p(len(group)),
                     "hsin": np.sin(2 * np.pi * h / 24), "hcos": np.cos(2 * np.pi * h / 24),
                     "dT": (np.mean(T[t0 - 2:t0]) - T[t0]) / scale[t0], "mu": mu, "r": r})
    return pd.DataFrame(rows)


def fit_forest(grid):
    base = scenario.simulate(scenario.merge(scenario.load_cfg("configs/baseline.yaml"),
                                            {"world": {"grid": grid}}))
    f = features(inputs_of(base))
    train = f[np.isin(split_of(f.onset), [0, 1])]
    forest = IsolationForest(n_estimators=300, random_state=CFG["random_state"]).fit(train[FEATS])
    return forest, forest.score_samples(train[FEATS]), f, base


def verdicts(f, forest, train_scores, q):
    s = forest.score_samples(f[FEATS])
    cut = np.quantile(train_scores, q)
    return f.assign(score=s, verdict=np.where(s < cut, "OUTAGE", "COMMS_FAILURE"),
                    method="iforest", p_comms=np.nan)


def episodes(grid, seeds):
    out = []
    for s in seeds:
        sim = scenario.simulate(scenario.merge(scenario.load_cfg("configs/cp5_episodes.yaml"),
                                               {"seed": s, "world": {"grid": grid}}))
        out.append((s, sim, features(inputs_of(sim))))
    return out


def evaluate_q(eps, forest, ts, q, week):
    tabs = []
    for s, sim, f in eps:
        v = verdicts(f, forest, ts, q)
        t = evaluate.episode_table(v, sim["labels"])
        t = t.assign(seed=s, score=[v.at[i, "score"] if i >= 0 else np.nan for i in t.verdict_row])
        tabs.append(t[split_of(t.start) == week])
    return pd.concat(tabs, ignore_index=True)


def main():
    out = {"stamp": stamp(CFG, "python -m shahid.iforest"),
           "label": "post-hoc baseline, added after CP7 (CP10 Task 6)"}
    forest, ts, ff, base = fit_forest(CFG["dev"])
    val = episodes(CFG["dev"], CFG["val_seeds"])
    sweep = []
    for q in CFG["q_grid"]:
        sweep.append({"q": q, **evaluate.rates(evaluate_q(val, forest, ts, q, 2))})
    best = max(sweep, key=lambda r: r["balanced_correct"])
    out["validation_sweep"] = sweep
    out["chosen_q"] = best["q"]
    vt = evaluate_q(val, forest, ts, best["q"], 2)
    out["validation"] = evaluate.rates(vt)
    # anomaly flagging ability: labelled events vs ordinary data-loss groups (validation weeks)
    ffv = ff[split_of(ff.onset) == 2]
    sc_ff = forest.score_samples(ffv[FEATS])
    sc_ev = vt.score.dropna().to_numpy()
    out["auc_event_vs_ordinary_loss_val"] = float(roc_auc_score(
        np.r_[np.ones(len(sc_ev)), np.zeros(len(sc_ff))], -np.r_[sc_ev, sc_ff]))
    o = vt[vt.cause == "OUTAGE"].score.dropna()
    c = vt[vt.cause == "COMMS_FAILURE"].score.dropna()
    out["auc_outage_vs_comms_val"] = float(roc_auc_score(np.r_[np.ones(len(o)), np.zeros(len(c))],
                                                         -np.r_[o, c]))
    # held-out grid: refit forest on urban6 fault-free training weeks, same q
    f2, ts2, ff2, base2 = fit_forest(CFG["held"])
    held = episodes(CFG["held"], CFG["test_seeds"])
    ht = evaluate_q(held, f2, ts2, best["q"], 3)
    out["heldout_urban6_test"] = evaluate.rates(ht)
    v_ff2 = verdicts(ff2, f2, ts2, best["q"])
    t3 = split_of(v_ff2.onset) == 3
    md = t3.sum() and (split_of(pd.DatetimeIndex(base2["observed"]["transformer"].interval_start)) == 3
                       ).sum() / 96 * len(base2["context"]["meters"])
    out["heldout_fault_free_false_outage_per_meter_day"] = float(
        (v_ff2.verdict[t3] == "OUTAGE").sum() / md)
    write_json("results/iforest.json", out)
    print({k: out[k] for k in ["chosen_q", "auc_event_vs_ordinary_loss_val",
                               "auc_outage_vs_comms_val"]})
    for k in ["validation", "heldout_urban6_test"]:
        r = out[k]
        print(k, {x: round(r[x], 3) for x in ["balanced_correct", "outage_recall", "comms_recall",
                                             "false_outage_rate", "missed_outage_rate"]})


if __name__ == "__main__":
    main()
