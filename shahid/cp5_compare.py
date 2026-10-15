"""CP5: detector comparison, baselines, threshold choice on validation, sanity controls.

Splits by onset week (week % 4): 0,1 train (detector fitting on the fault-free year),
2 validation (all comparisons and threshold choices here), 3 dev-test (untouched until CP7).

Run: python -m shahid.cp5_compare   (writes results/cp5_compare.json, results/detector_params.json)
"""
import numpy as np
import pandas as pd

from shahid import baselines, detect, evaluate, scenario
from shahid.stamp import stamp, write_json

CFG = {"episodes_config": "configs/cp5_episodes.yaml", "seeds": [101, 102, 103],
       "baseline_config": "configs/baseline.yaml",
       "methods": ["share", "ztest", "lr", "bayes"],
       "baselines": ["count", "structure", "step", "naive"],
       "grid": {"share": ("share_threshold", [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]),
                "ztest": ("z_crit", [1.645, 1.96, 2.25, 2.576, 2.9, 3.29]),
                "lr": ("llr_threshold", [-6, -4, -3, -2, -1, 0, 1, 2, 4]),
                "bayes": ("abstain_band", [0.005, 0.01, 0.02, 0.03, 0.05, 0.1, 0.2])},
       "min_expected_grid": [0.0, 0.25, 0.5, 1.0, 2.0],
       # DESIGN CHOICE (safety-constrained selection): a missed outage is auto-handled as a comms
       # failure, so it is the costliest error; abstentions go to a human.
       "constraints": {"fault_free_false_outage_per_meter_day": 0.001,
                       "missed_outage_rate": 0.05, "false_outage_rate": 0.05},
       "objective": "minimise abstention_rate subject to constraints",
       "permute_shift_days": 7, "boot": 1000, "seed": 5}


def inputs_of(sim):
    return {"readings": sim["observed"]["meter_readings"], "trafo": sim["observed"]["transformer"],
            "meters": sim["context"]["meters"], "zones": sim["context"]["zones"]}


def split_of(onsets):
    rows = ((pd.DatetimeIndex(onsets) - pd.Timestamp("2016-01-01")) / pd.Timedelta(minutes=15))
    return (np.asarray(rows, int) // (96 * 7)) % 4


def tables(verdicts, sim):
    """Labelled-episode table and unlabelled-group false alarms, validation weeks only."""
    tab = evaluate.episode_table(verdicts, sim["labels"])
    tab = tab[split_of(tab.start) == 2]
    if len(verdicts):
        truth = evaluate.truth_of_groups(verdicts, sim["labels"]["cells"])
        val = split_of(verdicts.onset) == 2
        matched = np.zeros(len(verdicts), bool)
        matched[tab.verdict_row[tab.verdict_row >= 0].to_numpy()] = True
        fa = int(((verdicts.verdict == "OUTAGE") & (truth == "COMMS_FAILURE") & val & ~matched).sum())
    else:
        fa = 0
    return tab, fa


def val_meter_days(sim):
    idx = pd.DatetimeIndex(sim["observed"]["transformer"].interval_start)
    days = (split_of(idx) == 2).sum() / 96
    return days * len(sim["context"]["meters"])


def main():
    rng = np.random.default_rng(CFG["seed"])
    out = {"stamp": stamp(CFG, "python -m shahid.cp5_compare")}
    base_cfg = scenario.load_cfg(CFG["baseline_config"])
    base = scenario.simulate(base_cfg)
    n_rows = len(base["observed"]["transformer"])
    rows = np.arange(n_rows)
    params = detect.fit(inputs_of(base), rows[np.isin((rows // 672) % 4, [0, 1])])
    out["fitted_params"] = dict(params)

    ev_tables, sims = {}, {}
    for s in CFG["seeds"]:
        cfg = scenario.merge(scenario.load_cfg(CFG["episodes_config"]), {"seed": s})
        sims[s] = scenario.simulate(cfg)
        ev_tables[s] = detect.evidence_table(inputs_of(sims[s]), params)
        print("seed", s, "groups", len(ev_tables[s]), flush=True)

    def run(method, p, which=None):
        tabs, fa, md = [], 0, 0.0
        for s in CFG["seeds"]:
            v = detect.decide_table(ev_tables[s], method, p) if which is None else which[s]
            t, f = tables(v, sims[s])
            tabs.append(t.assign(seed=s))
            fa += f
            md += val_meter_days(sims[s])
        tab = pd.concat(tabs, ignore_index=True)
        return tab, fa / md

    # fault-free year (validation weeks): every outage verdict is a false alarm
    evb = detect.evidence_table(inputs_of(base), params)
    md_base = val_meter_days(base)

    def fault_free(method, p):
        v = detect.decide_table(evb, method, p)
        val = split_of(v.onset) == 2
        return float((v.verdict[val] == "OUTAGE").sum() / md_base)

    # threshold choice on validation: maximise the objective on labelled episodes subject to
    # the fault-free false-alarm budget (if nothing meets it, take the lowest false-alarm rate)
    chosen, res = {}, {}
    for m in CFG["methods"]:
        key, grid = CFG["grid"][m]
        sweep = []
        for me in CFG["min_expected_grid"]:
            for val in grid:
                p = {**params, key: val, "min_expected_kwh": me}
                tab, fapmd = run(m, p)
                sweep.append({key: val, "min_expected_kwh": me, **evaluate.rates(tab),
                              "false_alarms_per_meter_day_episodes": fapmd,
                              "fault_free_false_outage_per_meter_day": fault_free(m, p)})
        ok = [r for r in sweep if all(np.nan_to_num(r[k], nan=1.0) <= v
                                      for k, v in CFG["constraints"].items())]
        if ok:
            best = min(ok, key=lambda r: (r["abstention_rate"], -np.nan_to_num(r["balanced_correct"])))
        else:
            best = min(sweep, key=lambda r: (r["missed_outage_rate"],
                                             r["fault_free_false_outage_per_meter_day"]))
        pm = {**params, key: best[key], "min_expected_kwh": best["min_expected_kwh"]}
        chosen[m] = {key: best[key], "min_expected_kwh": best["min_expected_kwh"]}
        tab, fapmd = run(m, pm)
        res[m] = {"threshold": chosen[m], "budget_met": bool(ok), "sweep": sweep,
                  **evaluate.rates(tab), "false_alarms_per_meter_day_episodes": fapmd,
                  "fault_free_false_outage_per_meter_day": fault_free(m, pm),
                  "ci95": {k: evaluate.bootstrap(tab, k, rng, CFG["boot"]) for k in
                           ["balanced_correct", "false_outage_rate", "outage_recall",
                            "comms_recall", "abstention_rate"]}}
        print(m, chosen[m], {k: round(res[m][k], 4) for k in
                             ["balanced_correct", "false_outage_rate", "abstention_rate",
                              "fault_free_false_outage_per_meter_day"]}, flush=True)

    def params_for(m):
        return {**params, **chosen[m]}

    for b in CFG["baselines"]:
        vb = {s: baselines.detect(inputs_of(sims[s]), b) for s in CFG["seeds"]}
        tab, fapmd = run(b, None, vb)
        vff = baselines.detect(inputs_of(base), b)
        ffo = float((vff.verdict[split_of(vff.onset) == 2] == "OUTAGE").sum() / md_base)
        res[b] = {**evaluate.rates(tab), "false_alarms_per_meter_day_episodes": fapmd,
                  "fault_free_false_outage_per_meter_day": ffo,
                  "ci95": {k: evaluate.bootstrap(tab, k, rng, CFG["boot"]) for k in
                           ["balanced_correct", "false_outage_rate", "outage_recall",
                            "comms_recall"]}}
        print(b, {k: round(res[b][k], 3) for k in ["balanced_correct", "false_outage_rate"]},
              flush=True)
    out["results_val"] = res

    # difficulty breakdown for the main methods (validation)
    out["by_difficulty"] = {}
    for m in ["bayes", "lr", "share"]:
        v = {s: detect.decide_table(ev_tables[s], m, params_for(m)) for s in CFG["seeds"]}
        tab, _ = run(m, None, v)
        tab = tab.assign(M=[v[s].at[i, "M"] if i >= 0 else np.nan
                            for s, i in zip(tab.seed, tab.verdict_row)])
        br = {}
        for name, col, bins in [("n_meters", tab.n_meters, [0, 1, 2, 5, 10, 20, 40]),
                                ("expected_kwh", tab.M, [-np.inf, 0.5, 1, 2, 5, 10, np.inf]),
                                ("hour", pd.DatetimeIndex(tab.start).hour, [0, 6, 10, 15, 19, 24])]:
            cut = pd.cut(col, bins, right=False if name == "hour" else True)
            br[name] = {str(k): evaluate.rates(g) for k, g in tab.groupby(cut, observed=True)}
        br["selector"] = {k: evaluate.rates(g) for k, g in tab.groupby("selector")}
        out["by_difficulty"][m] = br

    # sanity 1: transformer series shifted in time -> physics methods should fall to chance
    sh = {}
    for s in CFG["seeds"][:1]:
        inp = inputs_of(sims[s])
        tr = inp["trafo"].copy()
        tr["energy_kwh"] = np.roll(tr.energy_kwh.to_numpy(), 96 * CFG["permute_shift_days"])
        evp = detect.evidence_table({**inp, "trafo": tr}, params)
        for m in CFG["methods"]:
            t, _ = tables(detect.decide_table(evp, m, params_for(m)), sims[s])
            sh[m] = evaluate.rates(t)
    out["sanity_shifted_transformer"] = sh
    out["chosen_thresholds"] = chosen
    write_json("results/cp5_compare.json", out)
    write_json("results/detector_params.json", {"stamp": out["stamp"], "fitted": params,
                                                "thresholds": chosen})


if __name__ == "__main__":
    main()


def primary_method(path="results/cp5_compare.json"):
    """Primary method = the constraint-feasible method with the lowest abstention (CP5 rule)."""
    import json
    r = json.load(open(path))["results_val"]
    ok = [m for m in CFG["methods"] if r[m].get("budget_met")]
    return min(ok, key=lambda m: r[m]["abstention_rate"]) if ok else None
