"""Build one scenario: truth -> observed / context / labels.

Run: python -m shahid.scenario configs/<name>.yaml [out_dir]
Origin: ORIGINAL. Status: SIMULATED.

Storage layout per scenario directory:
  truth/    hidden physical state (never read by the detector)
  observed/ what a utility data export could contain
  context/  static information the detector may use
  labels/   evaluation ground truth, emitted here by the injector (never hand-written)

Events (start_step / duration_steps are rows from the world start):
  outage:        line: <idx> | feeder: <k>        opens the line, re-solves the power flow
  comms_failure: concentrator: <k> | zone: <line idx> | meters: [..]   data stops, power does not
  load_change:   zone: <line idx> | meters: [..], factor: <x>   real consumption change (re-solved)
"""
import copy
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from shahid import observe as ob
from shahid.episodes import expand
from shahid.stamp import config_hash, stamp
from shahid.world import apply_physical, build_world, meter_net_kwh, trafo_kwh, unmetered_kwh

T0 = pd.Timestamp("2016-01-01")  # SimBench profile year
STEP = pd.Timedelta(minutes=15)


def merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_cfg(path, defaults="configs/defaults.yaml"):
    return merge(yaml.safe_load(open(defaults)), yaml.safe_load(open(path)))


def meter_ids(n):
    return [f"m{i:03d}" for i in range(n)]


def concentrator_map(meta, mode, seed):
    """'aligned': one concentrator per feeder. 'random': same group sizes, meters shuffled
    (not aligned with electrical zones). DESIGN CHOICE (A-CONC)."""
    by_feeder = np.full(meta["n_meters"], -1)
    for k, f in enumerate(meta["feeders"]):
        by_feeder[sorted(meta["zones"][f])] = k
    if mode == "aligned":
        return by_feeder
    if mode == "random":
        return np.random.default_rng(seed).permutation(by_feeder)
    raise ValueError(mode)


def event_meters(ev, meta, conc):
    if "line" in ev or "feeder" in ev:
        line = ev["line"] if "line" in ev else meta["feeders"][ev["feeder"]]
        return line, sorted(meta["zones"][line])
    if "zone" in ev:
        return None, sorted(meta["zones"][ev["zone"]])
    if "concentrator" in ev:
        return None, np.flatnonzero(conc == ev["concentrator"]).tolist()
    return None, sorted(ev["meters"])


def simulate(cfg):
    w = build_world(cfg["world"])
    meta, N = w["meta"], w["meta"]["n_meters"]
    partial = []  # protocol 02: outages starting offset_min minutes into their first 15-min step
    index = T0 + STEP * pd.Index(w["steps"])
    conc = concentrator_map(meta, cfg["comms"]["concentrators"], cfg["seed"])
    physical, comm, episodes = [], [], []
    for k, ev in enumerate(expand(cfg)):
        a, b = ev["start_step"], ev["start_step"] + ev["duration_steps"]
        line, meters = event_meters(ev, meta, conc)
        if ev["type"] == "outage":
            physical.append({"a": a, "b": b, "open_line": line})
            if ev.get("offset_min"):
                partial.append((a, meters, ev["offset_min"] / 15))
            cause = "OUTAGE"
        elif ev["type"] == "comms_failure":
            comm.append((a, b, meters))
            cause = "COMMS_FAILURE"
        elif ev["type"] == "load_change":
            physical.append({"a": a, "b": b, "load_meters": meters, "load_factor": ev["factor"]})
            cause = "LOAD_CHANGE"
        else:
            raise ValueError(ev["type"])
        episodes.append({"episode_id": k, "cause": cause, "start": index[a],
                         "end": index[a] + STEP * (b - a), "n_meters": len(meters),
                         "meters": json.dumps([int(m) for m in meters]),
                         "line": -1 if line is None else int(line),
                         "selector": next(k for k in ["line", "feeder", "zone", "concentrator",
                                                      "meters"] if k in ev),
                         **({"offset_min": ev["offset_min"]} if "offset_min" in ev else {})})
    truth = apply_physical(w, physical)
    if not truth["converged"].all():
        raise RuntimeError(f"power flow did not converge on {(~truth['converged']).sum()} steps")
    e_true = meter_net_kwh(truth, meta)
    u = unmetered_kwh(cfg["world"], w["lp"])
    t_true = trafo_kwh(truth) + u
    no_supply = np.isnan(truth["vm_load"])  # isolated customers have no voltage
    if partial:  # ASSUMPTION (protocol 02): linear partial-interval model, losses not re-solved
        e_base = meter_net_kwh(w["truth"], meta)
        for a, ms, frac in partial:
            e_true[a, ms] = frac * e_base[a, ms]
            t_true[a] += frac * e_base[a, ms].sum()
    index_m, step, e_meas, t_meas, vm, ns, comm_m = index, STEP, e_true, t_true, truth["vm_load"], no_supply, comm
    f = int(cfg.get("cadence_min", 15)) // 15
    if f > 1:  # reporting interval option (protocol 02): same truth and events, coarser readings
        e_meas, t_meas, vm, ns, comm_m = ob.coarsen(e_true, t_true, truth["vm_load"], no_supply, comm, f)
        index_m, step = index[::f], STEP * f

    rng = np.random.default_rng(cfg["seed"])
    e_obs = ob.meter_readings(e_meas, rng, cfg["meter"])
    t_obs = ob.trafo_reading(t_meas, rng, cfg["tmeter"])
    v_obs = ob.quant(vm * 230 * (1 + rng.normal(0, 0.002, e_meas.shape)), 0.1) \
        if cfg["comms"]["voltage"] else None
    lag, cause = ob.delivery(ns, comm_m, rng, cfg["comms"])
    ids = meter_ids(N)
    readings = ob.to_long(index_m, e_obs, v_obs, lag, ids, ns, step)
    t_c, m_c = np.nonzero(cause != ob.NORMAL)
    cells = pd.DataFrame({"interval_start": index_m[t_c],
                          "meter_id": pd.Categorical.from_codes(m_c, ids),
                          "cause": pd.Categorical.from_codes(cause[t_c, m_c], ob.CAUSES)})
    pv_kw = np.zeros(N)
    np.add.at(pv_kw, meta["sgen_owner"], meta["net"].sgen.sn_mva.to_numpy() * 1000)
    return {
        "truth": {"powerflow": truth, "meter_energy_true": pd.DataFrame(e_true, index, ids),
                  "unmetered_kwh": u, "trafo_true_kwh": t_true},
        "observed": {
            "meter_readings": readings,
            "transformer": pd.DataFrame({"interval_start": index_m, "energy_kwh": t_obs}),
            "events": ob.last_gasps(index_m, ns, rng, cfg["comms"], ids)},
        "context": {
            "meters": pd.DataFrame({"meter_id": ids, "concentrator_id": conc, "pv_kw": pv_kw}),
            "zones": pd.DataFrame([{"zone_id": int(li), "meter_id": ids[m]}
                                   for li, ms in meta["zones"].items() for m in sorted(ms)])},
        "labels": {"episodes": pd.DataFrame(episodes), "cells": cells},
    }


def write(sim, out, cfg, command):
    out = Path(out)
    for area in ["observed", "context", "labels"]:
        (out / area).mkdir(parents=True, exist_ok=True)
        for name, df in sim[area].items():
            df.to_parquet(out / area / f"{name}.parquet", index=False)
    (out / "truth").mkdir(parents=True, exist_ok=True)
    tr = sim["truth"]
    np.savez_compressed(out / "truth" / "powerflow.npz", **tr["powerflow"],
                        unmetered_kwh=tr["unmetered_kwh"], trafo_true_kwh=tr["trafo_true_kwh"])
    tr["meter_energy_true"].astype("float32").to_parquet(out / "truth" / "meter_energy_true.parquet")
    with open(out / "manifest.json", "w") as f:
        json.dump(stamp(cfg, command), f, indent=1, default=str)
    return out


def main(path, out_dir=None):
    cfg = load_cfg(path)
    out_dir = Path(out_dir or Path("data") / f"{Path(path).stem}_{config_hash(cfg)}")
    write(simulate(cfg), out_dir, cfg, f"python -m shahid.scenario {Path(path).as_posix()}")
    print("wrote", out_dir)
    return out_dir


if __name__ == "__main__":
    main(*sys.argv[1:])
