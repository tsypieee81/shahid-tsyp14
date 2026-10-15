"""Truth simulation: per-customer diversity, cached baseline power flow, physical events.

Origin: ORIGINAL (power flow REUSED from pandapower, network/profiles REUSED from SimBench).
Status: SIMULATED.
"""
import copy
import os
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

import numpy as np

from shahid.grid import DT_H, candidate_zones, load_grid, profile_arrays, run_steps
from shahid.stamp import config_hash

CACHE = Path("cache")
# ponytail: one global cap on parallel worker processes (laptop heat); raise via SHAHID_WORKERS
MAX_WORKERS = int(os.environ.get("SHAHID_WORKERS", "4"))
TRUTH_KEYS = ["load_p", "sgen_p", "vm_load", "trafo_p_lv", "trafo_pl", "line_pl", "storage_p",
              "converged"]


def diversify(lp, lq, d, seed, steps_per_day=96):
    """Per-customer stochastic variation around SimBench's shared shapes. DESIGN CHOICE.

    SimBench loads are exact scaled copies of ~10 shapes (CP1, prior P2). Knob d >= 0:
      - daily time shift ~ round(N(0, 4d)) intervals, per customer and day
      - daily scale ~ LogNormal(-s^2/2, s), s = 0.3 d       (mean 1)
      - interval noise: AR(1) phi=0.7 in log space, marginal sd 0.5 d, mean-one corrected
    d = 0 reproduces SimBench exactly. The magnitudes are ASSUMPTIONS (A-DIV), not calibrated.
    """
    if d == 0:
        return lp.copy(), lq.copy()
    rng = np.random.default_rng(seed)
    T, N = lp.shape
    D = -(-T // steps_per_day)
    shift = np.rint(rng.normal(0, 4 * d, (D, N))).astype(int)
    s_day = 0.3 * d
    day_scale = np.exp(rng.normal(-s_day ** 2 / 2, s_day, (D, N)))
    sd, phi = 0.5 * d, 0.7
    e = np.empty((T, N))
    e[0] = rng.normal(0, sd, N)
    innov = rng.normal(0, sd * np.sqrt(1 - phi ** 2), (T, N))
    for t in range(1, T):
        e[t] = phi * e[t - 1] + innov[t]
    mult = np.exp(e - sd ** 2 / 2)
    day = np.arange(T) // steps_per_day
    idx = (np.arange(T)[:, None] - shift[day]) % T  # circular shift per customer-day
    cols = np.arange(N)[None, :]
    k = day_scale[day] * mult
    return lp[idx, cols] * k, lq[idx, cols] * k


@lru_cache(maxsize=4)
def _base_net(code):
    return load_grid(code)[0]


def _worker(args):
    code, lp, lq, sp, open_lines = args
    net = copy.deepcopy(_base_net(code))
    for li in open_lines:
        net.line.at[li, "in_service"] = False
    r = run_steps(net, lp, lq, sp, np.arange(len(lp)))
    return {k: r[k] for k in TRUTH_KEYS}


def _run(jobs, workers=None):
    workers = workers or max(1, min(MAX_WORKERS, len(jobs)))
    if workers == 1 or len(jobs) == 1 or os.environ.get("SHAHID_SERIAL"):
        return [_worker(j) for j in jobs]
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(_worker, jobs))


def solve(code, lp, lq, sp, open_lines=(), workers=None):
    """Power flow for every row of lp/lq/sp, parallel in chunks. Returns dict of arrays."""
    n = len(lp)
    if os.environ.get("SHAHID_SERIAL"):
        workers = 1
    workers = workers or max(1, min(MAX_WORKERS, n // 200 or 1))
    chunks = np.array_split(np.arange(n), workers)
    parts = _run([(code, lp[c], lq[c], sp[c], list(open_lines)) for c in chunks], workers)
    return {k: np.concatenate([p[k] for p in parts]) for k in TRUTH_KEYS}


def grid_meta(code):
    net, prof = load_grid(code)
    zones, feeders = candidate_zones(net)
    load_bus = net.load.bus.to_numpy()
    sgen_bus = net.sgen.bus.to_numpy()
    owner = np.array([int(np.flatnonzero(load_bus == b)[0]) for b in sgen_bus], dtype=int)
    return {"net": net, "prof": prof, "zones": zones, "feeders": feeders, "load_bus": load_bus,
            "sgen_bus": sgen_bus, "sgen_owner": owner, "n_meters": len(load_bus)}


def build_world(w):
    """Baseline (fault-free) truth for world config w, cached on disk by config hash.

    w keys: grid, start_day, days, diversity, pv_scale, seed.
    """
    meta = grid_meta(w["grid"])
    lp, lq, sp = profile_arrays(meta["net"], meta["prof"])
    lp, lq = diversify(lp, lq, w["diversity"], w["seed"])
    steps = np.arange(w["start_day"] * 96, (w["start_day"] + w["days"]) * 96)
    lp, lq, sp = lp[steps], lq[steps], sp[steps] * w.get("pv_scale", 1.0)
    CACHE.mkdir(exist_ok=True)
    key = {k: w.get(k) for k in ["grid", "start_day", "days", "diversity", "pv_scale", "seed"]}
    path = CACHE / f"truth_{config_hash(key)}.npz"
    if path.exists():
        z = np.load(path)
        truth = {k: z[k] for k in TRUTH_KEYS}
    else:
        truth = solve(w["grid"], lp, lq, sp)
        np.savez_compressed(path, **truth)
    return {"cfg": w, "meta": meta, "lp": lp, "lq": lq, "sp": sp, "steps": steps, "truth": truth}


def apply_physical(world, events):
    """Re-solve the power flow where physical events change the network.

    events: list of dicts with a, b (row range, end exclusive) and either
      open_line (outage: the line is opened, downstream customers lose supply) or
      load_meters + load_factor (a real load change for those customers).
    Overlapping events combine. Only affected rows are re-solved. Returns a new truth dict.
    """
    truth = {k: v.copy() for k, v in world["truth"].items()}
    if not events:
        return truth
    n = len(world["lp"])
    opens = [set() for _ in range(n)]
    factor = np.ones_like(world["lp"])
    for ev in events:
        for t in range(ev["a"], ev["b"]):
            if "open_line" in ev:
                opens[t].add(ev["open_line"])
        if "load_factor" in ev:
            factor[ev["a"]:ev["b"], ev["load_meters"]] *= ev["load_factor"]
    rows = [t for t in range(n) if opens[t] or (factor[t] != 1).any()]
    # group contiguous rows with the same open-line set into one job
    idx = []
    for t in rows:
        if idx and t == idx[-1][-1] + 1 and opens[t] == opens[idx[-1][-1]]:
            idx[-1].append(t)
        else:
            idx.append([t])
    lp, lq, sp = world["lp"] * factor, world["lq"] * factor, world["sp"]
    jobs = [(world["cfg"]["grid"], lp[r], lq[r], sp[r], sorted(opens[r[0]])) for r in idx]
    for r, res in zip(idx, _run(jobs)):
        for k in TRUTH_KEYS:
            truth[k][r] = res[k]
    return truth


def meter_net_kwh(truth, meta):
    """True net import energy per meter and interval (kWh); PV behind the meter (A-PV)."""
    e = truth["load_p"] * 1000 * DT_H
    for g, m in enumerate(meta["sgen_owner"]):
        e[:, m] -= truth["sgen_p"][:, g] * 1000 * DT_H
    return e


def trafo_kwh(truth):
    """Energy delivered from the transformer LV terminals into the LV network (kWh)."""
    return -truth["trafo_p_lv"][:, 0] * 1000 * DT_H


def unmetered_kwh(w, lp):
    """Unmetered energy the transformer sees but no meter reports (truth-side, kWh/interval).

    Robustness parameter, not a model of Tunisian theft or losses. Added to the transformer energy
    after the power flow (the second-order change in line losses is ignored; CP3 measures it).
      none | constant: kw | profile: kw x (aggregate load shape normalised to mean 1)
    """
    u = w.get("unmetered", {"kind": "none"})
    n = len(lp)
    if u["kind"] == "none":
        return np.zeros(n)
    if u["kind"] == "constant":
        return np.full(n, u["kw"] * DT_H)
    if u["kind"] == "profile":
        agg = lp.sum(1)
        return u["kw"] * DT_H * agg / agg.mean()
    raise ValueError(u["kind"])
