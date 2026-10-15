"""CP7: held-out evaluation, run ONCE under docs/eval_protocol.md.

For each evaluation target (held-out grid urban6; development grid semiurb5 as a second report):
  1. simulate the fault-free year for that grid and fit the detector on its TRAINING weeks
     (the fitting procedure is part of the frozen method; thresholds are not refitted);
  2. simulate episode scenarios with held-out seeds;
  3. score only TEST weeks (week % 4 == 3), which no earlier checkpoint used.

Run: python -m shahid.cp7_heldout   (writes results/cp7_heldout.json, results/cp7/*.parquet)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from shahid import baselines, detect, evaluate, scenario
from shahid.cp5_compare import inputs_of, split_of
from shahid.stamp import stamp, write_json

CFG = {"targets": {"heldout_urban6": "1-LV-urban6--0-sw", "dev_semiurb5": "1-LV-semiurb5--0-sw"},
       "episodes_config": "configs/cp5_episodes.yaml", "seeds": [301, 302, 303],
       "methods": ["bayes", "lr", "share", "ztest"],
       "baselines": ["naive", "step", "count", "structure"], "test_week": 3, "boot": 1000,
       "z90": 1.6449}


def window_truth(sim, v, tab):
    """True energy of the silent group over the decision window, for matched comms episodes."""
    e = sim["truth"]["meter_energy_true"]
    out = []
    for _, r in tab.iterrows():
        if r.verdict_row < 0 or r.cause != "COMMS_FAILURE":
            out.append(np.nan)
            continue
        row = v.loc[r.verdict_row]
        t0 = e.index.get_loc(row.onset)
        out.append(float(e.iloc[t0:t0 + int(row.n_intervals)][row.meters].to_numpy().sum()))
    return np.array(out)


def evaluate_target(name, grid, thr, rng):
    base_cfg = scenario.merge(scenario.load_cfg("configs/baseline.yaml"), {"world": {"grid": grid}})
    base = scenario.simulate(base_cfg)
    rows = np.arange(len(base["observed"]["transformer"]))
    fitted = detect.fit(inputs_of(base), rows[np.isin((rows // 672) % 4, [0, 1])])
    idx = pd.DatetimeIndex(base["observed"]["transformer"].interval_start)
    md_ff = (split_of(idx) == CFG["test_week"]).sum() / 96 * len(base["context"]["meters"])
    evb = detect.evidence_table(inputs_of(base), fitted)
    sims = {}
    for s in CFG["seeds"]:
        cfg = scenario.merge(scenario.load_cfg(CFG["episodes_config"]),
                             {"seed": s, "world": {"grid": grid}})
        sims[s] = scenario.simulate(cfg)
    res = {}
    tabs_all = []
    for m in CFG["methods"] + CFG["baselines"]:
        tabs = []
        for s, sim in sims.items():
            inp = inputs_of(sim)
            if m in CFG["methods"]:
                v = detect.detect(inp, {**fitted, **thr[m]}, m)
            else:
                v = baselines.detect(inp, m)
            tab = evaluate.episode_table(v, sim["labels"])
            tab = tab[split_of(tab.start) == CFG["test_week"]].assign(seed=s, method=m)
            if m in CFG["methods"]:
                tab = tab.assign(
                    M=[v.at[i, "M"] if i >= 0 else np.nan for i in tab.verdict_row],
                    sd_load=[np.sqrt(max(v.at[i, "sd_C"] ** 2 - v.at[i, "sd_O"] ** 2, 0))
                             if i >= 0 else np.nan for i in tab.verdict_row],
                    true_group_kwh=window_truth(sim, v, tab))
            tabs.append(tab)
        tab = pd.concat(tabs, ignore_index=True)
        r = evaluate.rates(tab)
        r["ci95"] = {k: evaluate.bootstrap(tab, k, rng, CFG["boot"]) for k in
                     ["balanced_correct", "outage_recall", "comms_recall", "precision_outage",
                      "precision_comms", "false_outage_rate", "missed_outage_rate",
                      "abstention_rate"]}
        if m in CFG["methods"]:
            vff = detect.decide_table(evb, m, {**fitted, **thr[m]})
            n_ff = int((vff.verdict[split_of(vff.onset) == CFG["test_week"]] == "OUTAGE").sum())
        else:
            vff = baselines.detect(inputs_of(base), m)
            n_ff = int((vff.verdict[split_of(vff.onset) == CFG["test_week"]] == "OUTAGE").sum())
        r["fault_free_false_outages"] = n_ff
        r["fault_free_meter_days"] = float(md_ff)
        r["fault_free_false_outage_per_meter_day"] = n_ff / md_ff
        r["fault_free_ci95_per_meter_day"] = evaluate.wilson(n_ff, int(md_ff))
        if m in CFG["methods"]:
            c = tab.dropna(subset=["true_group_kwh", "M"])
            err = c.M - c.true_group_kwh
            r["expected_load"] = {
                "n": len(c), "mae_kwh": float(np.abs(err).mean()) if len(c) else np.nan,
                "rel_err": float(np.abs(err).sum() / np.abs(c.true_group_kwh).sum()) if len(c) else np.nan,
                "coverage90": float((np.abs(err) <= CFG["z90"] * c.sd_load).mean()) if len(c) else np.nan}
            if m == "bayes":
                p = tab.dropna(subset=["p_comms"])
                y = (p.cause == "COMMS_FAILURE").astype(float)
                r["brier"] = float(((p.p_comms - y) ** 2).mean())
                bins = np.linspace(0, 1, 11)
                cut = pd.cut(p.p_comms, bins, include_lowest=True)
                r["reliability"] = [{"bin": str(k), "n": len(g), "mean_p": float(g.p_comms.mean()),
                                     "frac_comms": float((g.cause == "COMMS_FAILURE").mean())}
                                    for k, g in p.groupby(cut, observed=True)]
        res[m] = r
        tabs_all.append(tab)
        print(name, m, {k: round(r[k], 3) for k in ["balanced_correct", "outage_recall",
                                                    "comms_recall", "false_outage_rate",
                                                    "abstention_rate"]}, flush=True)
    Path("results/cp7").mkdir(parents=True, exist_ok=True)
    pd.concat(tabs_all).drop(columns=["meters"]).to_parquet(f"results/cp7/{name}_episodes.parquet")
    return {"grid": grid, "fitted": fitted, "results": res}


def main():
    thr = json.load(open("results/detector_params.json"))["thresholds"]
    rng = np.random.default_rng(7)
    out = {"stamp": stamp({**CFG, "thresholds": thr}, "python -m shahid.cp7_heldout"),
           "targets": {}}
    for name, grid in CFG["targets"].items():
        out["targets"][name] = evaluate_target(name, grid, thr, rng)
    write_json("results/cp7_heldout.json", out)


if __name__ == "__main__":
    main()
