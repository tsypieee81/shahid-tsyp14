"""Protocol 02: evidence accounting version 2 against "version 1 at any interval" (development).

Run: python -m shahid.p2_v2 select     band by rule v3 at 15 min, development validation (seeds 101-103 and
                                       the fault-free year) -> results/p2/v2_select.json, results/p2/v2_params.json
     python -m shahid.p2_v2 diagnose   development diagnostics, not used for selection: semiurb5 seeds 901-902
                                       at 15/30/60 min, sub-interval offsets at 15 min, the m093 merge case
                                       -> results/p2/v2_dev.json
Labels are read on the evaluation side only (truth of groups, episode matching).
"""
import json
import os
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from shahid import detect_v2 as D
from shahid import evaluate, scenario
from shahid.cp5_compare import inputs_of, split_of
from shahid.stamp import stamp, write_json
from shahid.world import MAX_WORKERS

OUT = Path("results/p2")
CACHE = OUT / "cache"
DEV = "1-LV-semiurb5--0-sw"
BANDS = [0.005, 0.01, 0.02, 0.03, 0.05, 0.1, 0.2]
FROZEN = json.load(open("results/detector_params.json"))
P15 = {**FROZEN["fitted"], **FROZEN["thresholds"]["bayes"]}
CADENCES = [15, 30, 60]
METHODS = {"v1": D.RULES_V1, "v2": D.RULES_V2}


def cfg_events(seed, grid=DEV, cadence=15, offsets=None):
    over = {"world": {"grid": grid}, "seed": seed, "cadence_min": cadence}
    if offsets:
        over["generator"] = {"offset_min": offsets}
    return scenario.merge(scenario.load_cfg("configs/cp5_episodes.yaml"), over)


def cfg_ff(grid=DEV, cadence=15, seed=1):
    return scenario.merge(scenario.load_cfg("configs/baseline.yaml"),
                          {"world": {"grid": grid}, "seed": seed, "cadence_min": cadence})


def params_at(grid, cadence, rules, frozen15=True):
    """Nuisance parameters: frozen at 15 min on the development grid; otherwise refitted on the grid's
    fault-free year (training weeks, unlabelled) at that interval, thresholds frozen."""
    if frozen15 and grid == DEV and cadence == 15:
        return dict(P15)
    path = CACHE / f"fit__{grid}__{cadence}__{'min' if rules.get('minutes') else 'rd'}.pkl"
    if path.exists():
        return pickle.load(open(path, "rb"))
    inp = inputs_of(scenario.simulate(cfg_ff(grid, cadence)))
    rows = np.arange(len(inp["trafo"]))
    spd = int(round(1440 / D.step_min(inp)))
    p = {**D.fit(inp, rows[np.isin((rows // (7 * spd)) % 4, [0, 1])], rules), **FROZEN["thresholds"]["bayes"]}
    pickle.dump(p, open(path, "wb"))
    return p


def match(v, episodes, step):
    """Group onset == reading interval containing the episode start, Jaccard >= 0.5 (registered rule
    at 15 min; the cadence-study rule at coarser intervals)."""
    by_onset = v.groupby("onset").groups if len(v) else {}
    out = []
    for e in episodes.itertuples():
        lm = {f"m{m:03d}" for m in json.loads(e.meters)}
        best, bj = -1, 0.5
        for i in by_onset.get(e.start.floor(step), []):
            vm = set(v.at[i, "meters"])
            j = len(lm & vm) / len(lm | vm)
            if j >= bj:
                best, bj = i, j
        out.append(best)
    return np.array(out)


def episode_rows(v, labels, step, cadence):
    ep = labels["episodes"]
    ep = ep[ep.cause.isin(["OUTAGE", "COMMS_FAILURE"])].reset_index(drop=True)
    idx = match(v, ep, step)
    rows = ep.drop(columns=["meters"]).assign(
        verdict=[v.at[i, "verdict"] if i >= 0 else "MISSED" for i in idx],
        latency_intervals=[v.at[i, "latency_intervals"] if i >= 0 else np.nan for i in idx],
        delay_min=[v.at[i, "decision_delay_min"] if i >= 0 else np.nan for i in idx],
        reason=[v.at[i, "reason"] if i >= 0 else "" for i in idx], week=split_of(ep.start))
    minute = pd.DatetimeIndex(rows.start).minute + pd.DatetimeIndex(rows.start).hour * 60
    off = rows["offset_min"].fillna(0).to_numpy() if "offset_min" in rows else np.zeros(len(rows))
    rows["mid_interval"] = (minute % cadence != 0) | (off > 0)
    return rows


def table_job(args):
    """Evidence tables for one simulation at one interval, for every method (cached)."""
    name, cfg, grid, cadence = args
    os.environ["SHAHID_SERIAL"] = "1"
    path = CACHE / f"{name}.pkl"
    if path.exists():
        return name
    sim = scenario.simulate(cfg)
    inp = inputs_of(sim)
    out = {"labels": {"episodes": sim["labels"]["episodes"], "cells": sim["labels"]["cells"]},
           "n_rows": len(inp["trafo"]), "n_meters": len(inp["meters"]), "cadence": cadence,
           "row_weeks": split_of(inp["trafo"].interval_start)}
    for m, rules in METHODS.items():
        p = params_at(grid, cadence, rules)
        out[m] = {"table": D.evidence_table(inp, p, rules), "params": p}
    pickle.dump(out, open(path, "wb"))
    return name


def run_jobs(jobs):
    CACHE.mkdir(parents=True, exist_ok=True)
    for g, c in {(j[2], j[3]) for j in jobs}:  # fit once per (grid, interval) before parallel work
        for rules in METHODS.values():
            params_at(g, c, rules)
    with ProcessPoolExecutor(max(1, min(2, MAX_WORKERS, len(jobs)))) as ex:
        for n in ex.map(table_job, jobs):
            print("tables", n, flush=True)


def decided(name, method, band):
    d = pickle.load(open(CACHE / f"{name}.pkl", "rb"))
    v = D.decide_table(d[method]["table"], d[method]["params"], METHODS[method], band)
    return d, v


def evaluate_set(names, method, band, weeks, ff_names=()):
    tabs = []
    for n in names:
        d, v = decided(n, method, band)
        step = pd.Timedelta(minutes=d["cadence"])
        tabs.append(episode_rows(v, d["labels"], step, d["cadence"]).assign(sim=n))
    tab = pd.concat(tabs, ignore_index=True)
    tab = tab[tab.week.isin(weeks)]
    k = md = 0.0
    for n in ff_names:
        d, v = decided(n, method, band)
        if len(v):
            k += int(((v.verdict == "OUTAGE") & np.isin(split_of(v.onset), weeks)).sum())
        md += np.isin(d["row_weeks"], weeks).sum() * d["cadence"] / 1440 * d["n_meters"]
    return tab, {"k": int(k), "meter_days": md, "per_meter_day": k / md if md else np.nan}


def rates(tab):
    r = evaluate.rates(tab) if len(tab) else {}
    r["median_delay_min"] = float(np.nanmedian(tab.delay_min)) if len(tab) else np.nan
    return r


def select():
    jobs = [(f"sel_cp5_{s}", cfg_events(s), DEV, 15) for s in (101, 102, 103)] + [("sel_ff_1", cfg_ff(), DEV, 15)]
    run_jobs(jobs)
    names, ffn = [j[0] for j in jobs[:3]], ["sel_ff_1"]
    res = {"stamp": stamp({"protocol": "docs/process/protocols/02_p2_evidence_v2.md", "bands": BANDS},
                          "python -m shahid.p2_v2 select"), "label": "development, selection data", "sweep": []}
    for b in BANDS:
        tab, ff = evaluate_set(names, "v2", b, [2], ffn)
        r = rates(tab)
        ok = (np.nan_to_num(r["missed_outage_rate"], nan=1) <= 0.05 and np.nan_to_num(r["false_outage_rate"], nan=1) <= 0.05
              and np.nan_to_num(ff["per_meter_day"], nan=1) <= 0.001)
        res["sweep"].append({"band": b, **{k: r[k] for k in ("missed_outage_rate", "false_outage_rate", "abstention_rate",
                                                              "accuracy_when_decided", "median_delay_min")},
                             "ff_per_meter_day": ff["per_meter_day"], "ff_k": ff["k"], "feasible": bool(ok)})
    tab, ff = evaluate_set(names, "v1", 0.03, [2], ffn)
    res["v1_reference"] = {**{k: v for k, v in rates(tab).items() if not isinstance(v, dict)}, "ff_per_meter_day": ff["per_meter_day"]}
    ok = [r for r in res["sweep"] if r["feasible"]]
    res["frozen"] = {"band": min(ok, key=lambda r: r["abstention_rate"])["band"]} if ok else None
    write_json(OUT / "v2_select.json", res)
    write_json(OUT / "v2_params.json", {"stamp": res["stamp"], "rules": D.RULES_V2, "frozen": res["frozen"]})
    print(json.dumps({"frozen": res["frozen"], "v1": res["v1_reference"]}, default=str), flush=True)
    for r in res["sweep"]:
        print(r, flush=True)


def diagnose():
    band = json.load(open(OUT / "v2_params.json"))["frozen"]
    if not band:
        print("no frozen version 2: diagnostics of the reference only", flush=True)
    jobs = [(f"dev_{s}_{c}", cfg_events(s, cadence=c), DEV, c) for s in (901, 902) for c in CADENCES]
    jobs += [(f"dev_{s}_15_off", cfg_events(s, offsets=[5, 10]), DEV, 15) for s in (901, 902)]
    jobs += [(f"dev_ff_{c}", cfg_ff(cadence=c), DEV, c) for c in CADENCES]
    run_jobs(jobs)
    res = {"stamp": stamp({"protocol": "docs/process/protocols/02_p2_evidence_v2.md", "seeds": [901, 902]},
                          "python -m shahid.p2_v2 diagnose"),
           "label": "development diagnostics, not used for selection", "band_v2": band}
    for c in CADENCES:
        for m, b in (("v1", 0.03), ("v2", band["band"] if band else None)):
            if b is None:
                continue
            tab, ff = evaluate_set([f"dev_{s}_{c}" for s in (901, 902)], m, b, [0, 1, 2, 3], [f"dev_ff_{c}"])
            o = tab[tab.cause == "OUTAGE"]
            res[f"{m}_{c}"] = {"all": rates(tab), "mid_interval": rates(tab[tab.mid_interval]),
                               "aligned": rates(tab[~tab.mid_interval]), "ff": ff,
                               "stored_rule_share": float((tab.reason == "stored readings delivered").mean()),
                               "outage_verdicts": o.verdict.value_counts().to_dict(),
                               "silent_groups": int(sum(len(pickle.load(open(CACHE / f"dev_{s}_{c}.pkl", "rb"))[m]["table"])
                                                        for s in (901, 902)))}
    for m, b in (("v1", 0.03), ("v2", band["band"] if band else None)):
        if b is None:
            continue
        tab, _ = evaluate_set([f"dev_{s}_15_off" for s in (901, 902)], m, b, [0, 1, 2, 3])
        res[f"{m}_15_offsets"] = {"all": rates(tab), "outages": rates(tab[tab.cause == "OUTAGE"])}
    res["m093_case"] = m093_case(band["band"] if band else 0.03)
    write_json(OUT / "v2_dev.json", res)
    for k, v in res.items():
        if isinstance(v, dict) and "all" in v:
            print(k, {a: round(x, 4) for a, x in v["all"].items() if a in ("missed_outage_rate", "false_outage_rate",
                                                                         "abstention_rate", "median_delay_min")}, flush=True)
    print("m093", res["m093_case"], flush=True)


def m093_case(band):
    """The finding-09 merge (demo feeder_outage, 10:00) under version 2 at 15 min: expected NOT fixed."""
    from shahid.demo_day import scenario_cfg
    cfg, _, day0 = scenario_cfg("feeder_outage")
    inp = inputs_of(scenario.simulate(cfg))
    out = {}
    for m, b in (("v1", 0.03), ("v2", band)):
        t = [g for g in D.evidence_table(inp, P15, METHODS[m]) if str(g["onset"]) == "2016-06-09 10:00:00"]
        v = D.decide_table(t, P15, METHODS[m], b)
        out[m] = {"n_meters": int(v.n_meters.iloc[0]), "verdict": v.verdict.iloc[0],
                  "p_comms": None if v.p_comms.iloc[0] is None else float(v.p_comms.iloc[0]), "reason": v.reason.iloc[0]}
    return out


if __name__ == "__main__":
    {"select": select, "diagnose": diagnose}[sys.argv[1]]()
