"""Protocol 08: shared learning between simulated nodes (proof of concept).

Node A (semiurb5, frozen) shares only dimensionless shape parameters; a new site B (urban6, rural3) has
d days of its own fault-free data after the 14-day warm-up. Conditions: Local(d), Shared(d), Oracle.
Measures on B's fault-free validation weeks: coverage of the nominal 90% interval of z = (R - M)/sd_C at
the deciding lead (|z| < t_0.95 with 4 df, as CP12 Task 3) and fault-free outage verdicts per meter-day.

Run: python -m shahid.p8_shared   (results/p8/shared.json)
"""
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from scipy import stats

from shahid import detect, detect_v2 as D, scenario
from shahid.cp5_compare import inputs_of, split_of
from shahid.evaluate import wilson
from shahid.stamp import stamp, write_json

GRIDS = {"urban6": "1-LV-urban6--0-sw", "rural3": "1-LV-rural3--0-sw"}
DAYS = [1, 2, 4, 7, 28]
SHARED = ["rho_by_lead", "sigma_mult_by_lead", "rho1_by_lead", "sigma1_mult_by_lead", "gap_acf1"]
FROZEN = json.load(open("results/detector_params.json"))
A = FROZEN["fitted"]
THR = FROZEN["thresholds"]["bayes"]
TCRIT = float(stats.t.ppf(0.95, 4))
USABLE = (0.85, 0.95, 0.001)


def val_measures(inp, fitted):
    """Validation-week silent groups of the fault-free year: coverage and outage verdicts."""
    p = {**detect.DEFAULTS, **fitted, **THR}
    index, meters, E, A_, T = detect.arrays(inp)
    weeks = split_of(index)
    z, k = [], 0
    for t0, g in detect.silent_groups(A_, p["K"]).items():
        if weeks[t0] != 2 or t0 < 96 * p["history_days"] or t0 + p["K"] + p["L_max"] > len(T):
            continue
        ev = None
        for L in range(p["L_max"] + 1):
            ev = detect.evidence(E, A_, T, t0, g, t0 + p["K"] + L, p)
            verdict, _, _ = detect.score(ev, "bayes", p)
            if verdict != "UNCERTAIN":
                break
        z.append((ev["R"] - ev["M"]) / ev["sd_C"])
        k += verdict == "OUTAGE"
    md = (weeks == 2).sum() / 96 * len(meters)
    z = np.array(z)
    cov = float(np.mean(np.abs(z) < TCRIT))
    return {"groups": len(z), "coverage90": cov, "outage_verdicts": int(k), "meter_days": md,
            "ff_per_meter_day": k / md, "ff_wilson95": wilson(k, md)}


def job(args):
    name, grid = args
    os.environ["SHAHID_SERIAL"] = "1"
    cfg = scenario.merge(scenario.load_cfg("configs/baseline.yaml"), {"world": {"grid": grid}})
    inp = inputs_of(scenario.simulate(cfg))
    rows = np.arange(len(inp["trafo"]))
    train = rows[np.isin((rows // 672) % 4, [0, 1]) & (rows >= 96 * 14)]
    out = {"oracle": val_measures(inp, D.fit(inp, rows[np.isin((rows // 672) % 4, [0, 1])], D.RULES_V1))}
    for d in DAYS:
        local = D.fit(inp, train[: 96 * d], D.RULES_V1)
        shared = {**local, **{k: A[k] for k in SHARED}}
        out[f"local_{d}"] = val_measures(inp, local)
        out[f"shared_{d}"] = val_measures(inp, shared)
        print(name, d, round(out[f"local_{d}"]["coverage90"], 3), round(out[f"shared_{d}"]["coverage90"], 3), flush=True)
    return name, out


def usable(m):
    return USABLE[0] <= m["coverage90"] <= USABLE[1] and m["ff_per_meter_day"] <= USABLE[2]


def main():
    Path("results/p8").mkdir(parents=True, exist_ok=True)
    res = {"stamp": stamp({"protocol": "docs/process/protocols/08_shared_learning.md", "days": DAYS, "shared": SHARED},
                          "python -m shahid.p8_shared"),
           "label": "proof of concept on previously examined grids (not confirmatory)"}
    with ProcessPoolExecutor(2) as ex:
        for name, out in ex.map(job, GRIDS.items()):
            res[name] = out
    h = {}
    for name in GRIDS:
        r = res[name]
        h[name] = {d: {"local_usable": usable(r[f"local_{d}"]), "shared_usable": usable(r[f"shared_{d}"]),
                       "local_dev": abs(r[f"local_{d}"]["coverage90"] - 0.9), "shared_dev": abs(r[f"shared_{d}"]["coverage90"] - 0.9)}
                   for d in DAYS}
        h[name]["days_to_usable"] = {c: next((d for d in DAYS if usable(r[f"{c}_{d}"])), None) for c in ("local", "shared")}
    small = [d for d in DAYS if d <= 4]
    better = all(any([(h[n][d]["shared_usable"] and not h[n][d]["local_usable"]) or h[n][d]["shared_dev"] < h[n][d]["local_dev"]])
                 for n in GRIDS for d in small)
    local1 = all(h[n][1]["local_usable"] for n in GRIDS)
    res["h8"] = {"by_grid": h, "verdict": "not supported (Local(1) already usable)" if local1 else
                 ("supported" if better else "not supported")}
    write_json("results/p8/shared.json", res)
    print(json.dumps(res["h8"], default=str, indent=1))


if __name__ == "__main__":
    main()
