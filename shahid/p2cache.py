"""Phase 2 studies (protocols 01, 03, 04, 05): per-lead evidence cache, version 1 grouping and the
feeder split (protocol 03), with evaluation-side truth kept in separate columns.

Per (family, seed) the cache holds every silent group of version 1 grouping ("v1") and of the split
grouping ("split") with the frozen version 1 evidence (R, M, sd_O, sd_C) at each lead 0..L_max, the
CP11 timing (t_fill, t_resume), and - read from the simulation labels, evaluation side only - the
group's true cause and its matched episode (addendum D rule). Scoring never sees those columns.

Run: python -m shahid.p2cache [family ...]   (results/p2/cache/<family>__<seed>.pkl, not tracked)
"""
import os
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from shahid import detect, evaluate, scenario
from shahid.cp5_compare import inputs_of, split_of
from shahid.records import families, fitted_for
from shahid.world import MAX_WORKERS

CACHE = Path("results/p2/cache")
HORIZON = 400  # as CP11 timing
DEV_FAMS = ["cp5", "ff_semiurb5", "feeder_semiurb5", "cp6_concentrators_random", "loss10_ff_semiurb5"]


def sections(inputs):
    """Line sections = feeder partition from the context zones only: maximal zones (zones contained in
    no other zone; a zone holding every meter is ignored). Meter index -> section id."""
    meters = inputs["meters"].meter_id.astype(str).tolist()
    mi = {m: i for i, m in enumerate(meters)}
    zones = {z: frozenset(mi[m] for m in ms.astype(str))
             for z, ms in inputs["zones"].groupby("zone_id").meter_id}
    zones = {z: s for z, s in zones.items() if len(s) < len(meters)}
    maximal = [z for z, s in zones.items() if not any(s < t for t in zones.values())]
    sec = np.full(len(meters), -1)
    for k, z in enumerate(sorted(maximal)):
        sec[list(zones[z])] = k
    free = np.flatnonzero(sec < 0)  # meters outside every zone: one section each
    sec[free] = len(maximal) + np.arange(len(free))
    return sec


def split(group, sec):
    return [group[sec[group] == s] for s in np.unique(sec[group])]


def timing(A, t0, g):
    a = A[t0:t0 + HORIZON, g]
    return float(np.median(A[t0, g])), float(np.median(a.min(0)))


def build(inputs, p):
    """Silent groups of both groupings with per-lead evidence and timing (observed data only)."""
    p = {**detect.DEFAULTS, **p}
    index, meters, E, A, T = detect.arrays(inputs)
    sec = sections(inputs)
    rows = []
    for t0, group in detect.silent_groups(A, p["K"]).items():
        if t0 < 96 * p["history_days"] or t0 + p["K"] + p["L_max"] > len(T):
            continue
        for mode, parts in (("v1", [group]), ("split", split(group, sec))):
            for k, g in enumerate(parts):
                evs = [detect.evidence(E, A, T, t0, g, t0 + p["K"] + L, p) for L in range(p["L_max"] + 1)]
                tf, tr = timing(A, t0, g)
                rows.append({"mode": mode, "part": k, "n_parts": len(parts), "onset": index[t0], "t0": t0,
                             "n_meters": len(g), "meters": [meters[i] for i in g], "t_fill": tf, "t_resume": tr,
                             **{f"{c}{L}": ev[c] for L, ev in enumerate(evs) for c in ("R", "M", "sd_O", "sd_C")}})
    return pd.DataFrame(rows), len(T), len(meters)


def label(groups, labels):
    """Evaluation side: true cause and matched episode per group, per grouping mode."""
    ep = labels["episodes"]
    ep = ep[ep.cause.isin(["OUTAGE", "COMMS_FAILURE"])].reset_index(drop=True) if "cause" in ep else ep.iloc[:0]
    out = []
    for mode, g in groups.groupby("mode"):
        g = g.reset_index(drop=True)
        g["truth"] = evaluate.truth_of_groups(g, labels["cells"])
        g["matched_episode"] = -1
        if len(ep):
            idx = evaluate.match_episodes(g, ep)
            for e, i in enumerate(idx):
                if i >= 0:
                    g.at[i, "matched_episode"] = int(ep.episode_id.iloc[e])
        out.append(g)
    groups = pd.concat(out, ignore_index=True)
    groups["week"] = split_of(groups.onset) if len(groups) else []
    if len(ep):
        ep = ep.assign(week=split_of(ep.start))
    return groups, ep


def run_one(args):
    fam, seed, cfg, fit_cfg, mode = args
    os.environ["SHAHID_SERIAL"] = "1"
    path = CACHE / f"{fam}__{seed}.pkl"
    if path.exists():
        return fam, seed, "cached"
    fitted, _ = fitted_for(fit_cfg, mode)
    sim = scenario.simulate(cfg)
    groups, n_rows, n_meters = build(inputs_of(sim), fitted)
    groups, ep = label(groups, sim["labels"]) if len(groups) else (groups, None)
    with open(path, "wb") as f:
        pickle.dump({"family": fam, "seed": seed, "grid": cfg["world"]["grid"], "n_rows": n_rows,
                     "n_meters": n_meters, "row_weeks": split_of(sim["observed"]["transformer"].interval_start),
                     "groups": groups, "episodes": ep, "fitted": fitted}, f)
    return fam, seed, len(groups)


def jobs(names, fams=None):
    fams = fams or families()
    out = []
    for n in names:
        sims, fit_cfg, mode = fams[n]
        out += [(n, s, cfg, fit_cfg, mode) for s, cfg in sims]
    return out


def load(fam, seed):
    with open(CACHE / f"{fam}__{seed}.pkl", "rb") as f:
        return pickle.load(f)


def main(names, fams=None):
    CACHE.mkdir(parents=True, exist_ok=True)
    js = jobs(names or DEV_FAMS, fams)
    with ProcessPoolExecutor(max(1, min(2, MAX_WORKERS, len(js)))) as ex:
        for fam, seed, n in ex.map(run_one, js):
            print("cached", fam, seed, n, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
