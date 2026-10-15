"""CP3 measurements on the development world (full year, nominal diversity).

1. Outage re-solve vs naive subtraction of the lost customers' energy.
2. Error of adding unmetered energy after the power flow instead of as a network load.
3. Fault-free baseline dataset statistics.

Run: python -m shahid.cp3_checks   (writes results/cp3_checks.json, builds the baseline dataset)
"""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandapower as pp

from shahid import scenario
from shahid.grid import DT_H, load_grid, run_steps
from shahid.stamp import config_hash, stamp, write_json
from shahid.world import MAX_WORKERS, _run, build_world, meter_net_kwh, trafo_kwh

CFG = {"n_random_zones": 24, "rows_per_zone": 20, "unmetered_kw": 2.0, "unmetered_rows": 200,
       "seed": 7, "baseline_config": "configs/baseline.yaml"}


def _unmetered_worker(args):
    code, lp, lq, sp, bus, kw = args
    net, _ = load_grid(code)
    pp.create_load(net, bus, p_mw=kw / 1000, q_mvar=0.0, name="unmetered")
    n = len(lp)
    lp = np.hstack([lp, np.full((n, 1), kw / 1000)])
    lq = np.hstack([lq, np.zeros((n, 1))])
    return run_steps(net, lp, lq, sp, np.arange(n))["trafo_p_lv"][:, 0]


def main():
    rng = np.random.default_rng(CFG["seed"])
    base_cfg = scenario.load_cfg(CFG["baseline_config"])
    w = build_world(base_cfg["world"])
    meta, truth = w["meta"], w["truth"]
    e = meter_net_kwh(truth, meta)
    T = trafo_kwh(truth)
    n = len(T)
    out = {"stamp": stamp({**CFG, "world": base_cfg["world"]}, "python -m shahid.cp3_checks")}
    out["world_converged"] = int(truth["converged"].sum())
    out["world_steps"] = n

    # 1. re-solve vs naive subtraction
    others = [li for li in meta["zones"] if li not in meta["feeders"]]
    zones = list(meta["feeders"]) + list(rng.choice(others, CFG["n_random_zones"], replace=False))
    jobs, rows_all = [], []
    for li in zones:
        rows = np.sort(rng.choice(n, CFG["rows_per_zone"], replace=False))
        rows_all.append(rows)
        jobs.append((w["cfg"]["grid"], w["lp"][rows], w["lq"][rows], w["sp"][rows], [int(li)]))
    res = _run(jobs)
    recs = []
    for li, rows, r in zip(zones, rows_all, res):
        z = sorted(meta["zones"][li])
        T_re = trafo_kwh(r)
        lost = e[rows][:, z].sum(1)
        naive = T[rows] - lost
        for k in range(len(rows)):
            recs.append({"zone": int(li), "n_meters": len(z), "lost_kwh": lost[k],
                         "T_base_kwh": T[rows[k]], "delta_kwh": T_re[k] - naive[k]})
    d = np.array([x["delta_kwh"] for x in recs])
    lost = np.array([x["lost_kwh"] for x in recs])
    Tb = np.array([x["T_base_kwh"] for x in recs])
    big = np.abs(lost) > 0.1
    out["resolve_vs_naive"] = {
        "n": len(recs), "n_zones": len(zones),
        "zone_sizes": sorted({x["n_meters"] for x in recs}),
        "delta_kwh_mean": float(d.mean()), "delta_kwh_abs_p50": float(np.median(np.abs(d))),
        "delta_kwh_abs_p95": float(np.quantile(np.abs(d), 0.95)),
        "delta_kwh_abs_max": float(np.abs(d).max()),
        "delta_over_abs_lost_p50_(|lost|>0.1kWh)": float(np.median(np.abs(d[big] / lost[big]))),
        "delta_over_abs_lost_p95_(|lost|>0.1kWh)": float(np.quantile(np.abs(d[big] / lost[big]), 0.95)),
        "delta_over_T_p95": float(np.quantile(np.abs(d / Tb), 0.95)),
        "sign_note": "delta < 0 means the re-solved transformer energy is lower than naive, i.e. "
                     "the outage also removed line losses",
    }

    # 2. unmetered energy: post-hoc addition vs a real unmetered load in the power flow
    feeder = max(meta["feeders"], key=lambda f: len(meta["zones"][f]))
    far = sorted(meta["zones"][feeder])[-1]
    bus = int(meta["load_bus"][far])
    rows = np.sort(rng.choice(n, CFG["unmetered_rows"], replace=False))
    chunks = np.array_split(rows, MAX_WORKERS)
    with ProcessPoolExecutor(len(chunks)) as ex:
        p_lv = np.concatenate(list(ex.map(_unmetered_worker, [
            (w["cfg"]["grid"], w["lp"][c], w["lq"][c], w["sp"][c], bus, CFG["unmetered_kw"])
            for c in chunks])))
    T_with = -p_lv * 1000 * DT_H
    u = CFG["unmetered_kw"] * DT_H
    err = (T_with - T[rows]) - u
    out["unmetered_posthoc_error"] = {
        "unmetered_kwh_per_interval": u, "bus": bus, "n": len(rows),
        "error_kwh_mean": float(err.mean()), "error_kwh_abs_max": float(np.abs(err).max()),
        "error_over_u_abs_max": float(np.abs(err).max() / u)}

    # 3. fault-free baseline dataset
    sim = scenario.simulate(base_cfg)
    out_dir = Path("data") / f"baseline_{config_hash(base_cfg)}"
    scenario.write(sim, out_dir, base_cfg, "python -m shahid.cp3_checks")
    cells = sim["labels"]["cells"]
    N = meta["n_meters"]
    out["baseline_dataset"] = {
        "dir": out_dir.as_posix(), "intervals": n, "meters": N,
        "cells_by_cause": {k: int(v) for k, v in cells.cause.value_counts().items()},
        "share_never_arrived": float(1 - len(sim["observed"]["meter_readings"]) / (n * N)),
        "files_mb": {p.relative_to(out_dir).as_posix(): round(p.stat().st_size / 1e6, 2)
                     for p in out_dir.rglob("*") if p.is_file()},
        "annual_meter_kwh_true": float(sim["truth"]["meter_energy_true"].to_numpy().sum()),
        "annual_trafo_kwh_observed": float(sim["observed"]["transformer"].energy_kwh.sum()),
        "annual_trafo_kwh_true": float(sim["truth"]["trafo_true_kwh"].sum()),
        "annual_line_losses_kwh": float(sim["truth"]["powerflow"]["line_pl"].sum() * 1000 * DT_H),
        "implied_trafo_meter_gain": float(sim["observed"]["transformer"].energy_kwh.sum()
                                          / sim["truth"]["trafo_true_kwh"].sum()),
    }
    write_json("results/cp3_checks.json", out)
    print({k: v for k, v in out.items() if k != "stamp"})


if __name__ == "__main__":
    main()
