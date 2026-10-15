"""CP6: detectability and robustness sweeps, hard negatives, baselines.

Every cell is a scenario family (overrides of configs/cp6_base.yaml) simulated with several seeds.
The detector uses the FROZEN parameters chosen in CP5 (results/detector_params.json), fitted on the
nominal fault-free year, so off-nominal cells also test robustness to a wrong noise model.
Exception: the history-length cells refit on the nominal fault-free year with that history.
Evaluation uses weeks 0-2 (week % 4 != 3); week 3 stays reserved for CP7.

Run: python -m shahid.cp6_sweep [cell ...]   (writes results/cp6/<cell>.json)
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from shahid import baselines, detect, evaluate, scenario
from shahid.cp5_compare import inputs_of, split_of
from shahid.stamp import stamp, write_json

BASE = "configs/cp6_base.yaml"
SEEDS = [201, 202]
METHODS = ["bayes", "lr", "share", "ztest"]
BASELINES = ["naive", "step", "count", "structure"]
MIX = {"outage": 0.5, "comms_zone": 0.5}


def mscale(k):
    return {"meter": {"gain_sd": 0.005 * k, "noise_rel_sd": 0.002 * k, "noise_abs_kwh": 0.0005 * k}}


CELLS = {
    "nominal": {},
    **{f"diversity_{d}": {"world": {"diversity": d}} for d in [0.0, 0.25, 1.0]},
    **{f"history_{h}": {"_history_days": h} for h in [7, 28]},
    **{f"meter_noise_x{k}": mscale(k) for k in [0, 3, 10]},
    **{f"tmeter_gain_{g}": {"tmeter": {"gain_sd": g, "noise_rel_sd": max(0.001, g / 2)}}
       for g in [0.0, 0.01, 0.02]},
    **{f"unmetered_{kind}_{kw}kw": {"world": {"unmetered": {"kind": kind, "kw": kw}}}
       for kind in ["constant", "profile"] for kw in [2.0, 5.0, 10.0]},
    # audit addition (2026-10-07): finer load-shaped unmetered levels to locate the failure boundary
    **{f"unmetered_profile_{kw}kw": {"world": {"unmetered": {"kind": "profile", "kw": kw}}}
       for kw in [1.0, 3.0]},
    **{f"pv_scale_{s}": {"world": {"pv_scale": s}} for s in [0.0, 2.0, 3.0]},
    "concentrators_random": {"comms": {"concentrators": "random"},
                             "generator": {"mix": {"outage": 0.5, "comms_concentrator": 0.5}}},
    "hn_concentrator_is_zone": {"generator": {"mix": {"outage": 0.5, "comms_concentrator": 0.5}}},
    "hn_low_load_night": {"generator": {"hours": [1, 5]}},
    "hn_pv_midday": {"world": {"pv_scale": 2.0}, "generator": {"hours": [10, 15]}},
    "hn_comms_with_load_change": {"generator": {"mix": {"outage": 0.5, "comms_load_change": 0.5}}},
    "hn_simultaneous_outage_comms": {"generator": {"mix": {"outage_plus_comms": 1.0}}},
    "hn_packet_loss_10pct": {"comms": {"p_missing": 0.10}},
}


def frozen_params():
    p = json.load(open("results/detector_params.json"))
    return p["fitted"], p["thresholds"]


def refit(H):
    """History-length cells: refit on the nominal fault-free year (training weeks) with H days."""
    base = scenario.simulate(scenario.load_cfg("configs/baseline.yaml"))
    rows = np.arange(len(base["observed"]["transformer"]))
    return detect.fit(inputs_of(base), rows[np.isin((rows // 672) % 4, [0, 1])], history_days=H)


def run_cell(name):
    os.environ["SHAHID_SERIAL"] = "1"  # cells already run in parallel processes
    over = dict(CELLS[name])
    H = over.pop("_history_days", None)
    fitted, thr = frozen_params()
    if H:
        fitted = refit(H)
    rows_all = []
    for seed in SEEDS:
        cfg = scenario.merge(scenario.load_cfg(BASE), {**over, "seed": seed})
        sim = scenario.simulate(cfg)
        inp = inputs_of(sim)
        ev = detect.evidence_table(inp, fitted)
        verdicts = {m: detect.decide_table(ev, m, {**fitted, **thr[m]}) for m in METHODS}
        verdicts.update({b: baselines.detect(inp, b) for b in BASELINES})
        idx = pd.DatetimeIndex(sim["observed"]["transformer"].interval_start)
        meter_days = (split_of(idx) != 3).sum() / 96 * len(sim["context"]["meters"])
        mean_abs_T = float(np.mean(np.abs(sim["observed"]["transformer"].energy_kwh)))
        for m, v in verdicts.items():
            tab = evaluate.episode_table(v, sim["labels"])
            keep = split_of(tab.start) != 3
            tab = tab[keep].assign(seed=seed, method=m)
            if len(v):
                truth = evaluate.truth_of_groups(v, sim["labels"]["cells"])
                use = split_of(v.onset) != 3
                matched = np.zeros(len(v), bool)
                matched[tab.verdict_row[tab.verdict_row >= 0].to_numpy()] = True
                fa = int(((v.verdict == "OUTAGE") & (truth == "COMMS_FAILURE") & use
                          & ~matched).sum())
            else:
                fa = 0
            if "M" in v:
                M = [v.at[i, "M"] if i >= 0 else np.nan for i in tab.verdict_row]
                n = [v.at[i, "n_intervals"] if i >= 0 else np.nan for i in tab.verdict_row]
                # expected silent energy as a share of typical transformer energy in the window
                tab = tab.assign(M=M, silent_load_fraction=np.array(M, float)
                                 / (mean_abs_T * np.array(n, float)))
            rows_all.append(tab.assign(unlabelled_false_outages=fa, meter_days=meter_days))
    tab = pd.concat(rows_all, ignore_index=True)
    out = {"stamp": stamp({"cell": name, "overrides": CELLS[name], "seeds": SEEDS,
                           "base": BASE}, f"python -m shahid.cp6_sweep {name}"), "methods": {}}
    rng = np.random.default_rng(0)
    for m, t in tab.groupby("method"):
        r = evaluate.rates(t)
        fa = t.drop_duplicates("seed").unlabelled_false_outages.sum()
        md = t.drop_duplicates("seed").meter_days.sum()
        r["unlabelled_false_outages_per_meter_day"] = float(fa / md)
        r["ci95"] = {k: evaluate.bootstrap(t, k, rng, 500) for k in
                     ["balanced_correct", "outage_recall", "comms_recall", "false_outage_rate",
                      "abstention_rate"]}
        out["methods"][m] = r
    Path("results/cp6").mkdir(parents=True, exist_ok=True)
    tab.drop(columns=["meters"]).to_parquet(f"results/cp6/{name}_episodes.parquet")
    write_json(f"results/cp6/{name}.json", out)
    b = out["methods"].get("bayes", {})
    return name, round(b.get("balanced_correct", np.nan), 3), round(b.get("abstention_rate", np.nan), 3)


def prebuild(cells):
    """Build every distinct baseline world once (parallel power flow) before the cell pool."""
    from shahid.world import build_world
    seen = set()
    for c in cells:
        w = scenario.merge(scenario.load_cfg(BASE), CELLS[c])["world"]
        key = json.dumps({k: w[k] for k in ["diversity", "pv_scale"]})
        if key not in seen:
            seen.add(key)
            build_world(w)


def main(cells):
    cells = cells or [c for c in CELLS if not Path(f"results/cp6/{c}.json").exists()]
    prebuild(cells)
    from shahid.world import MAX_WORKERS
    with ProcessPoolExecutor(max(1, min(len(cells), MAX_WORKERS))) as ex:
        for r in ex.map(run_cell, cells):
            print(*r, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
