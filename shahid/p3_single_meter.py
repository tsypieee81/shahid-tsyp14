"""Protocol 06: single-meter faults and falsified readings for meters that STILL report (goal G1).

D1 neighbour voltage: u_i(t) = V_i(t) - median of V over the other meters of its feeder; fitted on
   fault-free training weeks as u_i = a_i - b_i * E_i (own reported energy). Window statistic: mean of
   u_i - (a_i - b_i * E_i), standardised by its spread over fault-free windows of that meter.
D2 gap regression: per window, ridge regression (penalty 1.0, standardised regressors) of the gap
   T - sum(E) on every meter's reported energy; statistic = raw-scale coefficient of the meter,
   standardised by its spread over fault-free windows. D2 also names the meter (largest |statistic|).
Thresholds: 1% false alarms per meter-window on fault-free windows (as CP8). ASSUMPTION: a fault hits
the energy register, not the voltage channel. Optimism limit: the benchmark holds the MV voltage fixed.
Voltage cannot help a SILENT meter (finding 09); this module is not applied to the merge case.

Run: python -m shahid.p3_single_meter   (development: semiurb5, seed 951 -> results/p3/p3_dev.json)
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from shahid import scenario
from shahid.cp8_single_meter import CFG as CP8, impute, inject
from shahid.cp4_expected_load import observed_wide
from shahid.stamp import stamp, write_json
from shahid.world import grid_meta

FAULTS = CP8["faults"]
EPISODES, DAYS, Q, RIDGE = 150, 7, 0.01, 1.0
PRIMARY = ["gain_0.8", "gain_0.5", "bias_-0.05"]


def voltage_wide(sim):
    r = sim["observed"]["meter_readings"]
    idx = sim["observed"]["transformer"].interval_start
    ids = sim["context"]["meters"].meter_id
    V = np.full((len(idx), len(ids)), np.nan)
    V[pd.DatetimeIndex(idx).get_indexer(r.interval_start), pd.Index(ids).get_indexer(r.meter_id.astype(str))] = \
        r.voltage_v.to_numpy()
    return V


def neighbour_residual(V, sec):
    """u_i(t) = V_i(t) - median over the other meters of the same feeder."""
    U = np.full_like(V, np.nan)
    for s in np.unique(sec):
        ms = np.flatnonzero(sec == s)
        for m in ms:
            others = [o for o in ms if o != m]
            if others:
                U[:, m] = V[:, m] - np.nanmedian(V[:, others], 1)
    return U


def fit_d1(U, E, rows):
    """Per meter least squares u = a - b*E on fault-free training rows."""
    ab = []
    for m in range(E.shape[1]):
        x, y = E[rows, m], U[rows, m]
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() < 50:
            ab.append((np.nan, np.nan))
            continue
        X = np.column_stack([np.ones(ok.sum()), -x[ok]])
        a, b = np.linalg.lstsq(X, y[ok], rcond=None)[0]
        ab.append((a, b))
    return np.array(ab)


def d1_stat(U, X, ab, a, b):
    """Window mean residual per meter (raw), X = reported energy (possibly corrupted)."""
    pred = ab[:, 0][None, :] - ab[:, 1][None, :] * X[a:b]
    return np.nanmean(U[a:b] - pred, 0)


def d2_stat(T, X, a, b):
    """Ridge coefficients of the gap on each meter's energy, raw scale."""
    Xw = X[a:b]
    gap = T[a:b] - Xw.sum(1)
    mu, sd = Xw.mean(0), Xw.std(0)
    sd = np.where(sd > 0, sd, 1.0)
    Z = (Xw - mu) / sd
    y = gap - gap.mean()
    beta = np.linalg.solve(Z.T @ Z + RIDGE * np.eye(Z.shape[1]), Z.T @ y)
    return beta / sd


def run(grid, seed, rng_seed=6):
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    cfg = scenario.merge(scenario.load_cfg("configs/baseline.yaml"), {"world": {"grid": grid}, "seed": seed})
    sim = scenario.simulate(cfg)
    E = impute(observed_wide(sim))
    V = voltage_wide(sim)
    T = sim["observed"]["transformer"].energy_kwh.to_numpy()
    n_days, N = len(T) // 96, E.shape[1]
    E, T, V = E[: n_days * 96], T[: n_days * 96], V[: n_days * 96]
    meta = grid_meta(grid)
    sec = np.full(N, -1)
    for k, f in enumerate(meta["feeders"]):
        sec[sorted(meta["zones"][f])] = k
    U = neighbour_residual(V, sec)
    rows = np.arange(len(T))
    ab = fit_d1(U, E, rows[np.isin((rows // 672) % 4, [0, 1])])
    weeks = (np.arange(n_days) // 7) % 4
    ok_days = np.arange(CP8["own_window"], n_days - DAYS)
    starts = ok_days[np.isin(weeks[ok_days], [0, 1, 2]) & (ok_days % 7 == 0)]
    # fault-free windows: per-meter spread of each statistic, then pooled 1% thresholds on |z|
    s1 = np.array([d1_stat(U, E, ab, d0 * 96, (d0 + DAYS) * 96) for d0 in starts])
    s2 = np.array([d2_stat(T, E, d0 * 96, (d0 + DAYS) * 96) for d0 in starts])
    c1, c2 = np.nanmedian(s1, 0), np.nanmedian(s2, 0)
    sd1 = 1.4826 * np.nanmedian(np.abs(s1 - c1), 0)
    sd2 = 1.4826 * np.nanmedian(np.abs(s2 - c2), 0)
    z1, z2 = np.abs((s1 - c1) / sd1), np.abs((s2 - c2) / sd2)
    thr = {"d1": float(np.nanquantile(z1, 1 - Q)), "d2": float(np.nanquantile(z2, 1 - Q))}
    fa = {"d1": float(np.nanmean(z1 > thr["d1"])), "d2": float(np.nanmean(z2 > thr["d2"]))}
    rng = np.random.default_rng(rng_seed)
    res = {}
    for kind, vals in FAULTS.items():
        for val in vals:
            h1 = h2 = loc = n = 0
            for _ in range(EPISODES):
                d0 = int(rng.choice(starts))
                m = int(rng.integers(N))
                a, b = d0 * 96, (d0 + DAYS) * 96
                X = inject(E, m, a, b, kind, val, rng)
                t1 = abs((d1_stat(U, X, ab, a, b)[m] - c1[m]) / sd1[m])
                zz = np.abs((d2_stat(T, X, a, b) - c2) / sd2)
                h1 += bool(t1 > thr["d1"])
                hit2 = bool(zz[m] > thr["d2"])
                h2 += hit2
                loc += hit2 and int(np.nanargmax(zz)) == m
                n += 1
            res[f"{kind}_{val}"] = {"n": n, "d1": h1 / n, "d2": h2 / n, "d2_localised_share": loc / h2 if h2 else None}
            print(kind, val, res[f"{kind}_{val}"], flush=True)
    return {"grid": grid, "seed": seed, "thresholds": thr, "fault_free_false_alarm_rate": fa,
            "calibration_windows": int(len(starts)), "meter_windows": int(len(starts) * N),
            "results": res, "stamp": stamp(cfg, "python -m shahid.p3_single_meter")}


def h3(res):
    """Protocol 06 H3 per primary setting: detection >= 0.5 for D1 or D2 at <= 1% measured false alarms."""
    fa_ok = {k: res["fault_free_false_alarm_rate"][k] <= Q for k in ("d1", "d2")}
    return {s: bool(any(fa_ok[k] and res["results"][s][k] >= 0.5 for k in ("d1", "d2"))) for s in PRIMARY}


def main():
    Path("results/p3").mkdir(parents=True, exist_ok=True)
    r = run("1-LV-semiurb5--0-sw", 951)
    r["label"] = "development"
    r["h3_dev"] = h3(r)
    write_json("results/p3/p3_dev.json", r)
    print(json.dumps({"thr": r["thresholds"], "fa": r["fault_free_false_alarm_rate"], "h3": r["h3_dev"]}))


if __name__ == "__main__":
    main()
