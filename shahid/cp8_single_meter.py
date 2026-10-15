"""CP8 (time-boxed): single-meter faults. What can simple rules and the energy balance detect?

Faults are injected into ONE meter's observed readings for 7 days (data-quality faults: the
customer's consumption and the transformer are unchanged):
  stuck   the meter repeats its last reading
  gain    readings x g          bias   readings + b kWh per interval
  noise   readings + N(0, s)
Detectors (offline, daily; thresholds calibrated on fault-free weeks for 1% false alarms per check):
  stuck_rule   >= 8 consecutive identical readings
  own_history  daily energy / median of the previous 28 days outside fault-free quantiles
  balance      daily gap (transformer - sum of meters) shift vs the previous 14 days (robust z)
The balance can flag that SOME meter is wrong, not WHICH one; localisation is not attempted.

Run: python -m shahid.cp8_single_meter   (writes results/cp8_single_meter.json)
"""
import warnings

import numpy as np

from shahid import scenario
from shahid.cp4_expected_load import observed_wide
from shahid.stamp import stamp, write_json

CFG = {"base_config": "configs/baseline.yaml", "episodes": 150, "days": 7, "seed": 8,
       "faults": {"stuck": [None], "gain": [0.5, 0.8, 0.9, 1.1, 1.2, 1.5],
                  "bias": [-0.05, -0.02, 0.02, 0.05], "noise": [0.02, 0.05, 0.2]},
       "fa_target": 0.01, "stuck_run": 8, "own_window": 28, "gap_window": 14}


def impute(E):
    """Fill missing readings with the same-slot median of the previous 14 days (offline)."""
    E = E.copy()
    miss = np.argwhere(np.isnan(E))
    for t, m in miss:
        h = t - 96 * np.arange(1, 15)
        h = h[h >= 0]
        E[t, m] = np.nanmedian(E[h, m]) if len(h) else 0.0
    return np.nan_to_num(E)


def inject(E, m, a, b, kind, val, rng):
    X = E.copy()
    if kind == "stuck":
        X[a:b, m] = X[a - 1, m]
    elif kind == "gain":
        X[a:b, m] *= val
    elif kind == "bias":
        X[a:b, m] += val
    elif kind == "noise":
        X[a:b, m] += rng.normal(0, val, b - a)
    return X


def longest_run(x):
    best = run = 1
    for i in range(1, len(x)):
        run = run + 1 if x[i] == x[i - 1] else 1
        best = max(best, run)
    return best


def daily(E):
    return E.reshape(-1, 96, E.shape[1]).sum(1)  # (days, N)


def own_ratio(Ed, m, d0, days, w):
    base = np.median(Ed[d0 - w:d0, m])
    return Ed[d0:d0 + days, m] / base if base > 0.1 else np.full(days, np.nan)


def gap_z(Gd, d0, days, w):
    ref = Gd[d0 - w:d0]
    med, mad = np.median(ref), 1.4826 * np.median(np.abs(ref - np.median(ref)))
    return (Gd[d0:d0 + days] - med) / (mad if mad > 0 else np.nan)


def main():
    warnings.filterwarnings("ignore", category=RuntimeWarning)  # all-NaN ratio slices
    rng = np.random.default_rng(CFG["seed"])
    sim = scenario.simulate(scenario.load_cfg(CFG["base_config"]))
    E = impute(observed_wide(sim))
    T = sim["observed"]["transformer"].energy_kwh.to_numpy()
    n_days, N = len(T) // 96, E.shape[1]
    E, T = E[: n_days * 96], T[: n_days * 96]
    Ed = daily(E)
    Gd = (T - E.sum(1)).reshape(-1, 96).sum(1)
    weeks = (np.arange(n_days) // 7) % 4
    ok_days = np.arange(CFG["own_window"], n_days - CFG["days"])
    starts = ok_days[np.isin(weeks[ok_days], [0, 1, 2]) & (ok_days % 7 == 0)]

    # calibration on fault-free weeks: thresholds for 1% false alarms per (meter-)week check
    q = CFG["fa_target"]
    runs, ratios_lo, ratios_hi, zmax = [], [], [], []
    for d0 in starts:
        a, b = d0 * 96, (d0 + CFG["days"]) * 96
        for m in range(N):
            runs.append(longest_run(E[a:b, m]))
            r = own_ratio(Ed, m, d0, CFG["days"], CFG["own_window"])
            ratios_lo.append(np.nanmin(r))
            ratios_hi.append(np.nanmax(r))
        zmax.append(np.nanmax(np.abs(gap_z(Gd, d0, CFG["days"], CFG["gap_window"]))))
    thr = {"stuck_run": max(CFG["stuck_run"], int(np.quantile(runs, 1 - q)) + 1),
           "own_lo": float(np.nanquantile(ratios_lo, q / 2)),
           "own_hi": float(np.nanquantile(ratios_hi, 1 - q / 2)),
           "gap_z": float(np.quantile(zmax, 1 - q))}
    fa = {"stuck_rule": float(np.mean(np.array(runs) >= thr["stuck_run"])),
          "own_history": float(np.mean((np.array(ratios_lo) < thr["own_lo"])
                                       | (np.array(ratios_hi) > thr["own_hi"]))),
          "balance": float(np.mean(np.array(zmax) > thr["gap_z"]))}
    out = {"stamp": stamp(CFG, "python -m shahid.cp8_single_meter"), "thresholds": thr,
           "fault_free_false_alarm_rate": fa,
           "calibration": {"meter_weeks": len(runs), "weeks": len(zmax),
                           "note": "gap thresholds from only this many fault-free weeks"},
           "results": {}}
    for kind, vals in CFG["faults"].items():
        for val in vals:
            hits = {"stuck_rule": 0, "own_history": 0, "balance": 0}
            n = 0
            for _ in range(CFG["episodes"]):
                d0 = int(rng.choice(starts))
                m = int(rng.integers(N))
                a, b = d0 * 96, (d0 + CFG["days"]) * 96
                X = inject(E, m, a, b, kind, val, rng)
                Xd = Ed.copy()
                Xd[d0:d0 + CFG["days"], m] = X[a:b, m].reshape(-1, 96).sum(1)
                G = Gd.copy()
                G[d0:d0 + CFG["days"]] = (T[a:b] - X[a:b].sum(1)).reshape(-1, 96).sum(1)
                r = own_ratio(Xd, m, d0, CFG["days"], CFG["own_window"])
                hits["stuck_rule"] += longest_run(X[a:b, m]) >= thr["stuck_run"]
                hits["own_history"] += bool(np.nanmin(r) < thr["own_lo"] or np.nanmax(r) > thr["own_hi"])
                hits["balance"] += bool(np.nanmax(np.abs(gap_z(G, d0, CFG["days"],
                                                                CFG["gap_window"]))) > thr["gap_z"])
                n += 1
            key = f"{kind}_{val}"
            out["results"][key] = {k: v / n for k, v in hits.items()} | {"n": n}
            print(key, out["results"][key], flush=True)
    write_json("results/cp8_single_meter.json", out)


if __name__ == "__main__":
    main()
