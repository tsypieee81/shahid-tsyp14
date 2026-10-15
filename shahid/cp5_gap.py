"""CP5: the observed balance gap on fault-free data (training weeks only).

gap(t) = transformer(t) - sum of all meter readings(t), on intervals where every meter reported.
Examines distribution, dependence on load, and autocorrelation, which decide valid detectors.

Run: python -m shahid.cp5_gap   (writes results/cp5_gap.json, results/figs/cp5_gap.png)
"""
from pathlib import Path

import matplotlib
import numpy as np
import scipy.stats as st

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from shahid import scenario  # noqa: E402
from shahid.cp4_expected_load import observed_wide, week_split  # noqa: E402
from shahid.stamp import stamp, write_json  # noqa: E402

CFG = {"base_config": "configs/baseline.yaml", "max_lag": 8}


def acf(x, lags):
    x = x - np.nanmean(x)
    return [float(np.nanmean(x[k:] * x[:-k]) / np.nanvar(x)) for k in lags]


def main():
    cfg = scenario.load_cfg(CFG["base_config"])
    sim = scenario.simulate(cfg)
    E = observed_wide(sim)
    T = sim["observed"]["transformer"].energy_kwh.to_numpy()
    rows = np.arange(len(T))
    train = np.isin(week_split(rows), [0, 1])
    full = np.isfinite(E).all(1)
    load = np.nansum(E, 1)
    gap = np.where(full, T - load, np.nan)
    g, x = gap[train & full], load[train & full]
    # models: constant, linear in load, linear + quadratic in load
    X1 = np.c_[np.ones_like(x), x]
    X2 = np.c_[X1, x ** 2]
    fits = {}
    for name, X in [("const", X1[:, :1]), ("linear", X1), ("quadratic", X2)]:
        coef, *_ = np.linalg.lstsq(X, g, rcond=None)
        res = g - X @ coef
        fits[name] = {"coef": coef.tolist(), "resid_sd_kwh": float(res.std()),
                      "resid_mad_sd_kwh": float(1.4826 * np.median(np.abs(res - np.median(res))))}
    coef = np.array(fits["linear"]["coef"])
    resid_all = np.where(train & full, gap - (coef[0] + coef[1] * load), np.nan)
    res = resid_all[np.isfinite(resid_all)]
    out = {
        "stamp": stamp(CFG, "python -m shahid.cp5_gap"),
        "n_train_full_intervals": int(len(g)),
        "share_intervals_fully_reported": float(full.mean()),
        "gap_kwh": {"mean": float(g.mean()), "sd": float(g.std()),
                    "share_of_trafo": float(g.sum() / T[train & full].sum())},
        "fits": fits,
        "resid_linear": {"skew": float(st.skew(res)), "excess_kurtosis": float(st.kurtosis(res)),
                         "q01_q99": [float(np.quantile(res, 0.01)), float(np.quantile(res, 0.99))],
                         "acf_lag1_to_8": acf(resid_all, range(1, CFG["max_lag"] + 1))},
        "resid_sd_by_load_quintile": [],
    }
    q = np.quantile(x, np.linspace(0, 1, 6))
    r_lin = g - (coef[0] + coef[1] * x)
    for a, b in zip(q[:-1], q[1:]):
        m = (x >= a) & (x <= b)
        out["resid_sd_by_load_quintile"].append(
            {"load_kwh": [float(a), float(b)], "sd": float(r_lin[m].std())})
    Path("results/figs").mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.4))
    ax[0].scatter(x[::20], g[::20], s=2, alpha=0.4)
    ax[0].set(xlabel="sum of meters (kWh/interval)", ylabel="gap (kWh)", title="Gap vs load")
    ax[1].hist(r_lin, bins=100)
    ax[1].set(xlabel="residual of linear gap model (kWh)", title="Residual distribution")
    ax[2].bar(range(1, CFG["max_lag"] + 1), out["resid_linear"]["acf_lag1_to_8"])
    ax[2].set(xlabel="lag (15-min intervals)", title="Residual autocorrelation")
    fig.tight_layout()
    fig.savefig("results/figs/cp5_gap.png", dpi=120)
    write_json("results/cp5_gap.json", out)
    print({k: v for k, v in out.items() if k != "stamp"})


if __name__ == "__main__":
    main()
