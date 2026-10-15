"""CP1: measure SimBench LV grid facts, run power flows, check truth balance, profile diversity.

Run: python -m shahid.cp1_facts            (writes results/cp1_simbench_facts.json)
Origin: ORIGINAL (uses REUSED simbench/pandapower).
"""
import sys
import time

import numpy as np
import pandapower as pp
import simbench as sb

from shahid.grid import DT_H, candidate_zones, load_grid, profile_arrays, run_steps
from shahid.stamp import stamp, write_json

CFG = {
    "grids": [g for g in sb.collect_all_simbench_codes(hv_level="LV", lv_level="")
              if g.startswith("1-LV-") and g.endswith("-sw") and "no_sw" not in g],
    # two weeks: one winter (day 14), one summer (day 172), 15-min steps
    "ts_weeks_start_day": [14, 172],
    "ts_days": 7,
    "versions": {"simbench": sb.__version__, "pandapower": pp.__version__},
}


def counts(net):
    return {k: int(len(net[k])) for k in ["bus", "line", "trafo", "load", "sgen", "gen", "storage",
                                           "switch", "ext_grid"]}


def profile_usage(df):
    return {str(k): int(v) for k, v in df.profile.value_counts().items()} if len(df) else {}


def diversity(lp, net):
    """Are loads scaled copies of shared shapes? (prior P2)"""
    p = lp[:, lp.std(0) > 0]
    names = net.load.profile.to_numpy()[lp.std(0) > 0]
    norm = p / np.abs(p).max(0)
    same = []
    for name in np.unique(names):
        cols = norm[:, names == name]
        if cols.shape[1] > 1:
            same.append(float(np.abs(cols - cols[:, :1]).max()))
    c = np.corrcoef(p.T)
    iu = np.triu_indices_from(c, 1)
    # distinct normalised shapes, rounded to 1e-9
    shapes = {np.round(norm[:, j], 9).tobytes() for j in range(norm.shape[1])}
    return {
        "loads_nonconstant": int(p.shape[1]),
        "distinct_normalised_shapes": len(shapes),
        "max_abs_dev_within_same_profile_name_normalised": max(same) if same else None,
        "pairwise_corr_mean": float(c[iu].mean()),
        "pairwise_corr_share_above_0.999": float((c[iu] > 0.999).mean()),
    }


def ts_check(code, net, lp, lq, sp, days):
    steps = np.concatenate([np.arange(d * 96, (d + CFG["ts_days"]) * 96) for d in days])
    t0 = time.time()
    r = run_steps(net, lp, lq, sp, steps)
    dt = time.time() - t0
    ok = r["converged"]
    load = r["load_p"][ok].sum(1)
    gen = r["sgen_p"][ok].sum(1) if r["sgen_p"].shape[1] else np.zeros(ok.sum())
    lv_delivered = -r["trafo_p_lv"][ok, 0]
    line_pl = r["line_pl"][ok, 0]
    stor = r["storage_p"][ok, 0]
    resid_lv = lv_delivered - (load - gen + stor + line_pl)
    resid_hv = r["trafo_p_hv"][ok, 0] - (lv_delivered + r["trafo_pl"][ok, 0])
    e = lambda x: float(x.sum() * DT_H * 1000)  # MWh-> kWh over window: MW * h * 1000
    return {
        "steps": int(len(steps)), "converged": int(ok.sum()), "ms_per_step": 1000 * dt / len(steps),
        "vm_min_pu": float(np.nanmin(r["vm_min"])), "vm_max_pu": float(np.nanmax(r["vm_max"])),
        "trafo_loading_max_pct": float(np.nanmax(r["trafo_loading"])),
        "energy_kwh": {"load": e(load), "pv": e(gen), "lv_delivered": e(lv_delivered),
                       "line_losses": e(line_pl), "storage": e(stor), "trafo_losses": e(r["trafo_pl"][ok, 0])},
        "line_losses_share_of_load": float(line_pl.sum() / load.sum()),
        "trafo_losses_share_of_load": float(r["trafo_pl"][ok, 0].sum() / load.sum()),
        "reverse_flow_steps": int((lv_delivered < 0).sum()),
        "balance_resid_lv_max_abs_mw": float(np.abs(resid_lv).max()),
        "balance_resid_hv_max_abs_mw": float(np.abs(resid_hv).max()),
    }


def main():
    out = {"stamp": stamp(CFG, "python -m shahid.cp1_facts"), "grids": {}}
    for code in CFG["grids"]:
        print(code, flush=True)
        net, prof = load_grid(code)
        lp, lq, sp = profile_arrays(net, prof)
        zones, feeders = candidate_zones(net)
        sizes = sorted({len(z) for z in zones.values()})
        distinct_zones = {z for z in zones.values()}
        pp.runpp(net, numba=True)
        g = {
            "counts": counts(net),
            "trafo_sn_mva": [float(x) for x in net.trafo.sn_mva],
            "trafo_std_type": net.trafo.std_type.tolist(),
            "switch_types": {f"{et}/{t}": int(v) for (et, t), v in
                             net.switch.groupby(["et", "type"]).size().items()},
            "open_switches": int((~net.switch.closed).sum()),
            "load_profiles": profile_usage(net.load),
            "sgen_profiles": profile_usage(net.sgen),
            "sgen_types": profile_usage(net.sgen.assign(profile=net.sgen.type)),
            "sgen_installed_kw": float(net.sgen.sn_mva.sum() * 1000) if len(net.sgen) else 0.0,
            "load_ref_p_kw": {"min": float(net.load.p_mw.min() * 1000),
                              "max": float(net.load.p_mw.max() * 1000)},
            "profile_steps": int(lp.shape[0]),
            "profile_array_dims": {"load_p": list(lp.shape), "sgen_p": list(sp.shape)},
            "profile_time_first_last": [str(net.profiles["load"].time.iloc[0]),
                                        str(net.profiles["load"].time.iloc[-1])],
            "annual_load_kwh": float(lp.sum() * DT_H * 1000),
            "annual_pv_kwh": float(sp.sum() * DT_H * 1000),
            "feeders": len(feeders),
            "loads_per_feeder": sorted([len(zones[f]) for f in feeders], reverse=True),
            "candidate_zones_distinct": len(distinct_zones),
            "candidate_zone_sizes": sizes,
            "diversity": diversity(lp, net),
            "first_pf": {"converged": bool(net.converged),
                         "trafo_p_lv_mw": float(net.res_trafo.p_lv_mw.iloc[0])},
            "result_columns": {k: net[k].columns.tolist() for k in
                               ["res_bus", "res_line", "res_trafo", "res_load", "res_sgen"]},
            "timeseries": ts_check(code, net, lp, lq, sp, CFG["ts_weeks_start_day"]),
        }
        out["grids"][code] = g
        print({k: g[k] for k in ["counts", "feeders", "candidate_zones_distinct"]},
              g["diversity"], g["timeseries"]["ms_per_step"], flush=True)
    write_json("results/cp1_simbench_facts.json", out)


if __name__ == "__main__":
    sys.exit(main())
