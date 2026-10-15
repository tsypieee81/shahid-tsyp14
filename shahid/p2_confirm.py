"""Protocol 05: joint confirmatory batch on the two untouched grids, run once.

Run: python -m shahid.p2_confirm simulate   evidence caches and interval tables (resumable)
     python -m shahid.p2_confirm evaluate   every registered endpoint -> results/p2/confirm.json
Grids rural2 (primary) and semiurb4 (secondary). Frozen candidates only (protocol 05 addendum A):
version 1, P5, gate policy rows, version 2 against "v1 at any interval", P3 detectors D1/D2.
Labels are read on the evaluation side only.
"""
import json
import os
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from shahid import detect, p2_v2, p3_single_meter, p5_split, scenario
from shahid import p2eval as E
from shahid.cp5_compare import inputs_of
from shahid.p1_prior import gate_rows
from shahid.p2cache import CACHE, build, label, sections
from shahid.records import feeder_events
from shahid.stamp import stamp, write_json
from shahid.world import MAX_WORKERS, grid_meta

GRIDS = {"rural2": "1-LV-rural2--0-sw", "semiurb4": "1-LV-semiurb4--0-sw"}
EVENTS, FFX, FEEDER, LOSS = [801, 802, 803], [821, 822], [811, 812], 831
P2_SEEDS, P2_OFF = [841, 842], 843
THR = json.load(open("results/detector_params.json"))["thresholds"]["bayes"]
V2_BAND = json.load(open("results/p2/v2_params.json"))["frozen"]["band"]
TEST = [3]


def base(grid, seed, extra=None):
    return scenario.merge(scenario.load_cfg("configs/baseline.yaml"), {"world": {"grid": grid}, "seed": seed, **(extra or {})})


def eps(grid, seed):
    return scenario.merge(scenario.load_cfg("configs/cp5_episodes.yaml"), {"world": {"grid": grid}, "seed": seed})


def families(short, grid):
    return {f"conf_{short}_ff": [(1, base(grid, 1))] + [(s, base(grid, s)) for s in FFX],
            f"conf_{short}_events": [(s, eps(grid, s)) for s in EVENTS],
            f"conf_{short}_feeder": [(s, base(grid, s, {"events": feeder_events(grid, s)})) for s in FEEDER],
            f"conf_{short}_loss10": [(LOSS, base(grid, LOSS, {"comms": {"p_missing": 0.10}}))]}


def fitted_path(short):
    return CACHE / f"conf_{short}__fitted.pkl"


def fit_grid(short, grid):
    """Nuisance fit on the grid's own fault-free year (seed 1), training weeks; line-section check."""
    path = fitted_path(short)
    if path.exists():
        return pickle.load(open(path, "rb"))
    inp = inputs_of(scenario.simulate(base(grid, 1)))
    meta = grid_meta(grid)
    feeders = sorted(sorted(meta["zones"][f]) for f in meta["feeders"])
    sec = sections(inp)
    mine = sorted(sorted(np.flatnonzero(sec == k).tolist()) for k in set(sec))
    if feeders != mine:
        raise SystemExit(f"line sections differ from the network feeders on {grid}: run stopped (addendum A)")
    rows = np.arange(len(inp["trafo"]))
    p = detect.fit(inp, rows[np.isin((rows // 672) % 4, [0, 1])])
    pickle.dump(p, open(path, "wb"))
    return p


def cache_job(args):
    fam, seed, cfg, short = args
    os.environ["SHAHID_SERIAL"] = "1"
    path = CACHE / f"{fam}__{seed}.pkl"
    if path.exists():
        return fam, seed, "cached"
    fitted = pickle.load(open(fitted_path(short), "rb"))
    sim = scenario.simulate(cfg)
    from shahid.cp5_compare import split_of
    groups, n_rows, n_meters = build(inputs_of(sim), fitted)
    groups, ep = label(groups, sim["labels"]) if len(groups) else (groups, None)
    pickle.dump({"family": fam, "seed": seed, "grid": cfg["world"]["grid"], "n_rows": n_rows, "n_meters": n_meters,
                 "row_weeks": split_of(sim["observed"]["transformer"].interval_start), "groups": groups,
                 "episodes": ep, "fitted": fitted}, open(path, "wb"))
    return fam, seed, len(groups)


def p2_jobs(short, grid):
    jobs = [(f"conf_{short}_{s}_{c}", p2_v2.cfg_events(s, grid, c), grid, c) for s in P2_SEEDS for c in p2_v2.CADENCES]
    jobs += [(f"conf_{short}_{P2_OFF}_15_off", p2_v2.cfg_events(P2_OFF, grid, 15, [5, 10]), grid, 15)]
    jobs += [(f"conf_{short}_ff_{c}", p2_v2.cfg_ff(grid, c), grid, c) for c in p2_v2.CADENCES]
    return jobs


def simulate():
    CACHE.mkdir(parents=True, exist_ok=True)
    for short, grid in GRIDS.items():
        fit_grid(short, grid)
    jobs = [(fam, s, cfg, short) for short, grid in GRIDS.items() for fam, lst in families(short, grid).items()
            for s, cfg in lst]
    with ProcessPoolExecutor(max(1, min(2, MAX_WORKERS))) as ex:
        for fam, s, n in ex.map(cache_job, jobs):
            print("cached", fam, s, n, flush=True)
    for short, grid in GRIDS.items():
        p2_v2.run_jobs(p2_jobs(short, grid))


# ---------------------------------------------------------------------------------------------- evaluation
def items(fam, seeds, mode):
    return p5_split.mode_items(fam, seeds, mode)


def ff_exposure(short, mode, band=0.03):
    """Fault-free outage verdicts: fitting year test weeks + observation seeds 821-822 all weeks."""
    parts = [(items(f"conf_{short}_ff", [1], mode), TEST)] + [(items(f"conf_{short}_ff", [s], mode), [0, 1, 2, 3]) for s in FFX]
    k = md = days = 0.0
    for its, weeks in parts:
        r = E.fault_free(its, [E.decide(it["groups"], E.v1_posterior, band) for it in its], weeks)
        k, md, days = k + r["k"], md + r["meter_days"], days + r["days"]
    return {"k": int(k), "meter_days": md, "per_meter_day": k / md, "per_meter_day_wilson95": E.evaluate.wilson(k, md),
            "per_transformer_year": k / days * 365, "days": days}


def episodes_tab(short, mode, band=0.03):
    tabs = [E.episode_tab(it, it["groups"], E.decide(it["groups"], E.v1_posterior, band), TEST).assign(seed=it["seed"])
            for it in items(f"conf_{short}_events", EVENTS, mode)]
    return pd.concat(tabs, ignore_index=True)


def detection_block(short, rng):
    out = {}
    for name, mode in (("v1", "v1"), ("P5", "split")):
        tab = episodes_tab(short, mode)
        r = E.summarise(tab, rng)
        ff = ff_exposure(short, mode)
        out[name] = {**r, "fault_free": ff, "v3_feasible": bool(E.feasible(r, ff))}
    return out


def h5(short, rng):
    ev = p5_split.merges(f"conf_{short}_events", EVENTS, TEST)
    fd = p5_split.merges(f"conf_{short}_feeder", FEEDER)
    wrong_v1 = ev["wrong_comms_p095_v1"] + fd["wrong_comms_p095_v1"]
    wrong_p5 = ev["wrong_comms_p095_P5"] + fd["wrong_comms_p095_P5"]
    return {"merges_events_test_weeks": ev, "merges_feeder_all_weeks": fd,
            "H5a": {"wrong_comms_p095_cross_feeder_v1": wrong_v1, "P5": wrong_p5},
            "price_addendum_A": {"events_test_weeks": p5_split.price(f"conf_{short}_events", EVENTS, TEST, rng),
                                 "feeder_all_weeks": p5_split.price(f"conf_{short}_feeder", FEEDER, [0, 1, 2, 3], rng)}}


def gate_block(short):
    feeders = items(f"conf_{short}_feeder", FEEDER, "v1")
    ffs = [it for s in FFX for it in items(f"conf_{short}_ff", [s], "v1")]
    rows = [("v1", E.v1_posterior, 0.03, False, False), ("v1+gate-close", E.v1_posterior, 0.03, True, False),
            ("v1+gate-escalate", E.v1_posterior, 0.03, True, True)]
    out = {"ff_1pct": gate_rows(feeders, ffs, rows)}
    out["loss10"] = gate_rows(feeders, items(f"conf_{short}_loss10", [LOSS], "v1"), rows)
    return out


def p2_tabs(short, method, band, c):
    names = [f"conf_{short}_{s}_{c}" for s in P2_SEEDS]
    tab, ff = p2_v2.evaluate_set(names, method, band, [0, 1, 2, 3], [f"conf_{short}_ff_{c}"])
    return tab.assign(grid=short), ff


def paired_diff(a, b, mask_fn, metric_fn, rng, boot=2000):
    """Bootstrap over episodes (pairs by grid, sim, episode) of metric(b) - metric(a) on a subset."""
    key = ["grid", "sim", "episode_id"]
    m = a[key + ["cause", "verdict", "mid_interval"]].merge(b[key + ["verdict"]], on=key, suffixes=("_a", "_b"))
    m = m[mask_fn(m)].reset_index(drop=True)
    if not len(m):
        return {"n": 0}
    va, vb = metric_fn(m.verdict_a), metric_fn(m.verdict_b)
    d = [vb[i].mean() - va[i].mean() for i in (rng.integers(0, len(m), len(m)) for _ in range(boot))]
    return {"n": len(m), "a": float(va.mean()), "b": float(vb.mean()), "diff_b_minus_a": float(vb.mean() - va.mean()),
            "ci95": [float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))]}


def p2_block(rng):
    out, t60, tmid = {}, {"v1": [], "v2": []}, {"v1": [], "v2": []}
    for short in GRIDS:
        for c in p2_v2.CADENCES:
            for m, b in (("v1", 0.03), ("v2", V2_BAND)):
                tab, ff = p2_tabs(short, m, b, c)
                out[f"{short}_{m}_{c}"] = {"all": p2_v2.rates(tab), "mid_interval": p2_v2.rates(tab[tab.mid_interval]),
                                           "ff": ff, "outage_verdicts": tab[tab.cause == "OUTAGE"].verdict.value_counts().to_dict()}
                if c == 60:
                    t60[m].append(tab)
                if c in (30, 60):
                    tmid[m].append(tab)
        for m, b in (("v1", 0.03), ("v2", V2_BAND)):
            tab, _ = p2_v2.evaluate_set([f"conf_{short}_{P2_OFF}_15_off"], m, b, [0, 1, 2, 3])
            tab = tab.assign(grid=short)
            out[f"{short}_{m}_15_offsets"] = {"all": p2_v2.rates(tab), "outages": p2_v2.rates(tab[tab.cause == "OUTAGE"])}
            tmid[m].append(tab)
    cat = {m: pd.concat(v, ignore_index=True) for m, v in t60.items()}
    mid = {m: pd.concat(v, ignore_index=True) for m, v in tmid.items()}
    out["S1_false_outage_60min"] = paired_diff(cat["v1"], cat["v2"], lambda d: d.cause == "COMMS_FAILURE",
                                               lambda v: (v == "OUTAGE").to_numpy(float), rng)
    out["S2_missed_mid_interval"] = paired_diff(mid["v1"], mid["v2"], lambda d: (d.cause == "OUTAGE") & d.mid_interval,
                                                lambda v: v.isin(["COMMS_FAILURE", "MISSED"]).to_numpy(float), rng)
    for k in ("S1_false_outage_60min", "S2_missed_mid_interval"):
        ci = out[k].get("ci95")
        out[k]["verdict"] = "supported" if ci and ci[1] < 0 else "not supported"
    tab, _ = p2_v2.evaluate_set([f"conf_rural2_{s}_15" for s in P2_SEEDS], "v2", V2_BAND, [0, 1, 2, 3])
    _, ff = p2_v2.evaluate_set([f"conf_rural2_{s}_15" for s in P2_SEEDS], "v2", V2_BAND, TEST, ["conf_rural2_ff_15"])
    r = p2_v2.rates(tab)
    out["safety_v2_15min_rural2"] = {"missed": r["missed_outage_rate"], "false": r["false_outage_rate"],
                                     "ff_per_meter_day_test_weeks": ff["per_meter_day"],
                                     "verdict": "met" if (r["missed_outage_rate"] <= 0.05 and r["false_outage_rate"] <= 0.05
                                                          and ff["per_meter_day"] <= 0.001) else "broken (harmful)"}
    return out


def evaluate():
    rng = np.random.default_rng(805)
    res = {"stamp": stamp({"protocol": "docs/process/protocols/05_confirmatory_batch.md", "grids": GRIDS,
                           "v2_band": V2_BAND}, "python -m shahid.p2_confirm evaluate"),
           "label": "confirmatory, run once", "frozen_params": {s: str(fitted_path(s)) for s in GRIDS}}
    for short in GRIDS:
        res[short] = {"detection": detection_block(short, rng), "p5": h5(short, rng), "gate": gate_block(short)}
        d = res[short]["detection"]
        res[short]["H5b_P5_safety"] = "met" if d["P5"]["v3_feasible"] else "broken (harmful)"
    w = sum(res[s]["p5"]["H5a"]["wrong_comms_p095_cross_feeder_v1"] for s in GRIDS)
    w5 = sum(res[s]["p5"]["H5a"]["P5"] for s in GRIDS)
    res["H5a"] = {"v1": w, "P5": w5, "verdict": ("inconclusive (no such event)" if w == 0 else
                                                 "supported" if w5 < w and res["rural2"]["detection"]["P5"]["v3_feasible"]
                                                 else "not supported")}
    res["p2"] = p2_block(rng)
    p3 = p3_single_meter.run("1-LV-rural2--0-sw", 851)
    res["p3_rural2"] = {**p3, "H3": p3_single_meter.h3(p3)}
    write_json("results/p2/confirm.json", res)
    print(json.dumps({"H5a": res["H5a"], "H5b": {s: res[s]["H5b_P5_safety"] for s in GRIDS},
                      "S1": res["p2"]["S1_false_outage_60min"], "S2": res["p2"]["S2_missed_mid_interval"],
                      "v2_safety": res["p2"]["safety_v2_15min_rural2"], "H3": res["p3_rural2"]["H3"]}, default=str, indent=1))


if __name__ == "__main__":
    {"simulate": simulate, "evaluate": evaluate}[sys.argv[1]]()
