"""CP4: can the energy of a silent meter group be predicted from legitimate information?

Estimators (each uses only observed readings that precede the target day, plus the readings of
the currently reporting meters for the neighbour estimator):
  median   same-slot median of each meter's last H days
  mean     same-slot mean of each meter's last H days, with sd -> prediction interval
  ratio    group's same-slot historical share of the reporting meters' energy x current
           reporting energy (uses the currently reporting meters)
Targets are TRUE energies (evaluation only). Splits by week: week % 4 in {0,1} train,
2 validation, 3 test. CP4 reports train and validation only; the test weeks are untouched.

Run: python -m shahid.cp4_expected_load   (writes results/cp4_expected_load.json, figures)
"""
import numpy as np
import pandas as pd

from shahid import scenario
from shahid.stamp import stamp, write_json
from shahid.world import grid_meta

CFG = {"diversity": [0.0, 0.25, 0.5, 1.0], "history_days": [7, 14, 28], "nominal_H": 14,
       "group_sizes": [1, 2, 5, 10, 20, 50], "groups_per_size": 200, "targets_per_split": 3000,
       "z90": 1.6449, "lead": 2, "ml_groups": ["random_10", "zones"], "seed": 11, "base_config": "configs/baseline.yaml"}


def week_split(rows):
    return (rows // (96 * 7)) % 4


def observed_wide(sim):
    r = sim["observed"]["meter_readings"]
    idx = sim["observed"]["transformer"].interval_start
    ids = sim["context"]["meters"].meter_id
    E = np.full((len(idx), len(ids)), np.nan)
    ti = pd.DatetimeIndex(idx).get_indexer(r.interval_start)
    mi = pd.Index(ids).get_indexer(r.meter_id.astype(str))
    E[ti, mi] = r.energy_kwh.to_numpy()
    return E


def history(E, rows, H):
    h = rows[:, None] - 96 * np.arange(1, H + 1)[None, :]
    return E[h]  # (R, H, N)


def transfer(dev, X, G):
    """Deviation transfer: at each row, fit dev_j = a*w_j + b*pv_j by least squares over the
    meters NOT in the group (reporting), then predict the group's deviation from its own w, pv.
    dev: (R, N) with NaN for missing; X: (R, N, 2). Returns (R, n_groups)."""
    V = np.isfinite(dev)
    y = np.where(V, dev, 0.0)
    Xv = X * V[..., None]
    XX = np.einsum("rja,rjb->rjab", Xv, X)
    Xy = np.einsum("rja,rj->rja", Xv, y)
    A = XX.sum(1)[:, None] - np.einsum("gj,rjab->rgab", G, XX)  # (R, G, 2, 2)
    bvec = Xy.sum(1)[:, None] - np.einsum("gj,rja->rga", G, Xy)
    det = A[..., 0, 0] * A[..., 1, 1] - A[..., 0, 1] * A[..., 1, 0]
    det = np.where(np.abs(det) > 1e-12, det, np.nan)
    ca = (A[..., 1, 1] * bvec[..., 0] - A[..., 0, 1] * bvec[..., 1]) / det
    cb = (A[..., 0, 0] * bvec[..., 1] - A[..., 1, 0] * bvec[..., 0]) / det
    xs = np.einsum("gj,rja->rga", G, X)  # group totals of w and pv
    return ca * xs[..., 0] + cb * xs[..., 1]


def estimates(E, rows, H, G, pv_kw, lead, rho):
    """Per-group predictions for target rows. G: (n_groups, N) 0/1 membership.

    lead: intervals since silence onset (onset = row - lead + 1); the group's last reading
    before onset is at row - lead. rho: persistence of the group deviation over `lead` steps.
    """
    Eh = history(E, rows, H)
    med = np.nanmedian(Eh, 1)  # (R, N)
    mean = np.nanmean(Eh, 1)
    sd = np.nanstd(Eh, 1, ddof=1)
    mu_med = med @ G.T  # (R, n_groups)
    mu_mean = mean @ G.T
    sd_sum = np.sqrt((sd ** 2) @ G.T)  # independence assumption
    # ratio estimator: group share of the other meters' net energy in history, same slot
    hist_tot = np.nansum(Eh, 1)
    g_hist = hist_tot @ G.T
    rest_hist = hist_tot.sum(1, keepdims=True) - g_hist
    now = np.nan_to_num(E[rows])
    rest_now = now.sum(1, keepdims=True) - now @ G.T
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(np.abs(rest_hist) > 1e-6, g_hist / rest_hist * rest_now, mu_med)
    # deviation transfer from reporting meters (scale w = mean |E| in history, and pv_kw)
    w = np.nanmean(np.abs(Eh), 1)
    X = np.stack([w, np.broadcast_to(pv_kw, w.shape)], -1)
    tr = mu_mean + transfer(E[rows] - mean, X, G)
    # anchored: group's own deviation just before onset, decayed
    prev = rows - lead
    mean_prev = np.nanmean(history(E, prev, H), 1)
    dev_prev = np.nan_to_num(E[prev] - mean_prev) @ G.T
    anch = mu_mean + rho * dev_prev
    return {"median": mu_med, "mean": mu_mean, "ratio": ratio, "transfer": tr,
            "anchored": anch}, sd_sum, dev_prev


def features(E, R, H, Gm, pv, rho):
    preds, sd_sum, dev_prev = estimates(E, R, H, Gm, pv, CFG["lead"], 0.0)
    hour = np.broadcast_to(((R // 4) % 24)[:, None], dev_prev.shape)
    X = np.stack([preds["mean"], dev_prev, preds["transfer"] - preds["mean"], sd_sum, hour,
                  np.broadcast_to(Gm @ pv, dev_prev.shape)], -1)
    return X.reshape(-1, X.shape[-1]), (preds["mean"] + rho * dev_prev).ravel()


def ml_test(E, Et, rows, H, Gm, pv, rho, rng):
    """Gradient boosting vs the anchored estimator on the same features (val weeks).

    Trained on TRAIN weeks with the OBSERVED group sum as target (rows where every group meter
    reported). Reports bootstrap 95% CI of the MAE difference (ML - anchored) on validation.
    """
    from sklearn.ensemble import HistGradientBoostingRegressor
    Xtr, _ = features(E, rows["train"], H, Gm, pv, rho)
    obs = E[rows["train"]] @ Gm.T  # NaN if any member missing
    ytr = obs.ravel()
    ok = np.isfinite(ytr) & np.isfinite(Xtr).all(1)
    m = HistGradientBoostingRegressor(max_iter=300, random_state=0).fit(Xtr[ok], ytr[ok])
    Xv, anch = features(E, rows["val"], H, Gm, pv, rho)
    yv = (Et[rows["val"]] @ Gm.T).ravel()
    ok = np.isfinite(Xv).all(1)
    pml = m.predict(Xv[ok])
    e_ml, e_an = np.abs(pml - yv[ok]), np.abs(anch[ok] - yv[ok])
    diff = e_ml - e_an
    boot = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(1000)]
    return {"mae_ml": float(e_ml.mean()), "mae_anchored": float(e_an.mean()),
            "rel_err_ml": float(e_ml.sum() / np.abs(yv[ok]).sum()),
            "rel_err_anchored": float(e_an.sum() / np.abs(yv[ok]).sum()),
            "mae_diff_ci95": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))],
            "n": int(ok.sum())}


def groups(meta, N, rng):
    out = {}
    for k in CFG["group_sizes"]:
        g = np.zeros((CFG["groups_per_size"], N))
        for i in range(CFG["groups_per_size"]):
            g[i, rng.choice(N, k, replace=False)] = 1
        out[f"random_{k}"] = g
    z = np.zeros((len(meta["zones"]), N))
    for i, ms in enumerate(meta["zones"].values()):
        z[i, sorted(ms)] = 1
    out["zones"] = z
    return out


def summarise(pred, truth_g, T_rows):
    err = pred - truth_g
    return {"mae_kwh": float(np.nanmean(np.abs(err))),
            "rel_err_vs_group": float(np.nansum(np.abs(err)) / np.nansum(np.abs(truth_g))),
            "rel_err_vs_trafo": float(np.nansum(np.abs(err)) / (np.nansum(np.abs(T_rows)) * err.shape[1])),
            "bias_rel": float(np.nansum(err) / np.nansum(np.abs(truth_g)))}


def main():
    rng = np.random.default_rng(CFG["seed"])
    base = scenario.load_cfg(CFG["base_config"])
    out = {"stamp": stamp(CFG, "python -m shahid.cp4_expected_load"), "by_d": {}}
    first_rows = max(CFG["history_days"]) * 96
    meta = grid_meta(base["world"]["grid"])
    N = meta["n_meters"]
    G = groups(meta, N, rng)
    allrows = np.arange(first_rows, base["world"]["days"] * 96)
    split = week_split(allrows)
    rows = {s: np.sort(rng.choice(allrows[np.isin(split, ids)], CFG["targets_per_split"],
                                  replace=False))
            for s, ids in [("train", [0, 1]), ("val", [2])]}
    for d in CFG["diversity"]:
        cfg = scenario.merge(base, {"world": {"diversity": d}})
        sim = scenario.simulate(cfg)
        E = observed_wide(sim)
        Et = sim["truth"]["meter_energy_true"].to_numpy()
        T = sim["observed"]["transformer"].energy_kwh.to_numpy()
        res = {}
        pv = sim["context"]["meters"].pv_kw.to_numpy()
        for H in CFG["history_days"]:
            for gname, Gm in G.items():
                r = {}
                for s in ["train", "val"]:
                    R = rows[s]
                    preds, sd_sum, dev_prev = estimates(E, R, H, Gm, pv, CFG["lead"], 0.0)
                    if s == "train":  # fit persistence on OBSERVED deviations only
                        dev_now = np.nan_to_num(E[R]) @ Gm.T - preds["mean"]
                        r["rho"] = float(np.sum(dev_now * dev_prev) / np.sum(dev_prev ** 2))
                    preds["anchored"] = preds["mean"] + r["rho"] * dev_prev
                    tg = Et[R] @ Gm.T
                    r[s] = {m: summarise(p, tg, T[R]) for m, p in preds.items()}
                    scale = np.where(sd_sum > 0, sd_sum, np.nan)
                    for m in ["mean", "transfer", "anchored"]:
                        z = np.abs(preds[m] - tg) / scale
                        if s == "train":  # conformal multiplier (uses truth on TRAIN weeks only)
                            r[f"conformal_c90_{m}"] = float(np.nanquantile(z, 0.9))
                        else:
                            r[f"val_coverage90_conformal_{m}"] = float(
                                np.nanmean(z <= r[f"conformal_c90_{m}"]))
                            r[f"val_interval_halfwidth_rel_{m}"] = float(
                                np.nansum(r[f"conformal_c90_{m}"] * scale) / np.nansum(np.abs(tg)))
                    if s == "val":
                        r["val_coverage90_gaussian_indep"] = float(
                            np.nanmean(np.abs(preds["mean"] - tg) <= CFG["z90"] * scale))
                        hour = (R // 4) % 24
                        r["val_by_hour_rel_err"] = {m: [
                            float(np.nansum(np.abs(preds[m] - tg)[hour == h])
                                  / np.nansum(np.abs(tg)[hour == h])) for h in range(24)]
                            for m in ["median", "mean", "transfer", "anchored"]}
                if H == CFG["nominal_H"] and gname in CFG["ml_groups"]:
                    r["ml_test"] = ml_test(E, Et, rows, H, Gm, pv, r["rho"], rng)
                res[f"H{H}/{gname}"] = r
        out["by_d"][str(d)] = res
        n = res[f"H{CFG['nominal_H']}/random_10"]["val"]
        print(d, {m: round(v["rel_err_vs_group"], 3) for m, v in n.items()}, flush=True)
    write_json("results/cp4_expected_load.json", out)


if __name__ == "__main__":
    main()
