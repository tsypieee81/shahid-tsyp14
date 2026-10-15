"""CP11: per-group timing (for the WATCH policy) and Isolation Forest verdicts on record families.

Re-simulates the observation layer with the ORIGINAL seeds (worlds are cached; outage events only
re-solve their own rows). Per silent group (same grouping as version 1):
  t_fill    median over the group's meters of the arrival time of their onset-interval reading
            (inf if never delivered): late data recovered
  t_resume  median over the group's meters of the first arrival of any reading for an interval at or
            after the onset: meters heard again
Times are in interval units since the start of the year, like detect.arrays.
Isolation Forest: fitted on the grid's fault-free training weeks, q = 0.05 (chosen in CP10 on CP5
validation weeks), applied to every group.

Run: python -m shahid.cp11_sims [family ...]   (writes results/records/<family>__cp11.parquet,
     results/records/<family>__iforest_episodes.parquet)
"""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from shahid import evaluate, scenario
from shahid.cp5_compare import inputs_of, split_of
from shahid.detect import arrays, silent_groups
from shahid.iforest import FEATS, features
from shahid.records import DEV, HELD, families

OUT = Path("results/records")
K, HORIZON = 2, 400  # look at most 100 hours ahead for resumption
Q = json.load(open("results/iforest.json"))["chosen_q"]


def extra_families():
    """Addendum B: new fault-free observation seeds on cached worlds; untouched grid rural3."""
    base = lambda g, s: scenario.merge(scenario.load_cfg("configs/baseline.yaml"),
                                       {"world": {"grid": g}, "seed": s})
    fam = {f"ffx_semiurb5_{s}": [(s, base(DEV, s))] for s in [451, 452, 453, 454]}
    fam.update({f"ffx_urban6_{s}": [(s, base(HELD, s))] for s in [455, 456, 457, 458]})
    R3 = "1-LV-rural3--0-sw"
    fam["rural3_ff"] = [(1, base(R3, 1))]
    fam["rural3_eps"] = [(s, scenario.merge(scenario.load_cfg("configs/cp5_episodes.yaml"),
                                            {"world": {"grid": R3}, "seed": s})) for s in [501, 502]]
    return fam


def all_families():
    fam = {k: v[0] for k, v in families().items()}
    fam.update(extra_families())
    return fam


_forests = {}


def forest_for(grid):
    from sklearn.ensemble import IsolationForest
    if grid not in _forests:
        base = scenario.simulate(scenario.merge(scenario.load_cfg("configs/baseline.yaml"),
                                                {"world": {"grid": grid}}))
        f = features(inputs_of(base))
        tr = f[np.isin(split_of(f.onset), [0, 1])]
        forest = IsolationForest(n_estimators=300, random_state=0).fit(tr[FEATS])
        _forests[grid] = (forest, np.quantile(forest.score_samples(tr[FEATS]), Q))
    return _forests[grid]


def timing(A):
    rows = []
    for t0, g in silent_groups(A, K).items():
        a = A[t0:t0 + HORIZON, g]
        fill = np.median(A[t0, g])
        resume = np.median(a.min(0))
        rows.append({"t0": t0, "n_meters": len(g), "t_fill": fill, "t_resume": resume})
    return pd.DataFrame(rows)


def run(name):
    os.environ["SHAHID_SERIAL"] = "1"
    t = time.time()
    sims = all_families()[name]
    grid = sims[0][1]["world"]["grid"]
    forest, cut = forest_for(grid)
    tabs, eps = [], []
    for seed, cfg in sims:
        sim = scenario.simulate(cfg)
        inp = inputs_of(sim)
        index, meters, E, A, T = arrays(inp)
        tm = timing(A).assign(seed=seed, onset=lambda d: index[d.t0.to_numpy()])
        f = features(inp)
        if len(f):
            f = f.assign(if_score=forest.score_samples(f[FEATS]))
            f["verdict"] = np.where(f.if_score < cut, "OUTAGE", "COMMS_FAILURE")
            f["method"], f["p_comms"] = "iforest", np.nan
            tm = tm.merge(f[["onset", "if_score", "verdict"]].rename(columns={"verdict": "if_verdict"}),
                          on="onset", how="left")
            lab = dict(sim["labels"])
            if "cause" in lab["episodes"]:
                et = evaluate.episode_table(f, lab)
                eps.append(et.drop(columns=["meters"]).assign(seed=seed, method="iforest",
                                                             week=split_of(et.start)))
                truth = evaluate.truth_of_groups(f, lab["cells"])
            else:
                truth = np.array(["COMMS_FAILURE"] * len(f))
            tm = tm.merge(pd.DataFrame({"onset": f.onset, "if_truth": truth}), on="onset", how="left")
        tabs.append(tm)
    pd.concat(tabs, ignore_index=True).to_parquet(OUT / f"{name}__cp11.parquet")
    if eps:
        pd.concat(eps, ignore_index=True).to_parquet(OUT / f"{name}__iforest_episodes.parquet")
    return name, round(time.time() - t)


DEFAULT = ["ff_semiurb5", "ff_urban6", "loss10_ff_semiurb5", "loss10_ff_urban6", "cp5",
           "cp7_heldout_urban6", "cp7_dev_semiurb5", "loss10_semiurb5", "loss10_urban6",
           "feeder_semiurb5", "feeder_urban6", "cp6_nominal", "cp6_tmeter_gain_0.02",
           "cp6_unmetered_profile_10.0kw", "cp6_hn_simultaneous_outage_comms",
           *extra_families()]  # addendum B: extra fault-free seeds and the untouched grid


def main(argv):
    names = [a for a in argv if not a.startswith("--")] or DEFAULT
    names = [n for n in names if not (OUT / f"{n}__cp11.parquet").exists()]
    workers = max(1, min(2, len(names)))  # heat: at most 2 families at a time
    with ProcessPoolExecutor(workers) as ex:
        for n, sec in ex.map(run, names):
            print("done", n, sec, "s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
