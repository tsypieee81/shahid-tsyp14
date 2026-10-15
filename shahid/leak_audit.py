"""Leak audit for CP7 (integrity rule 9: metrics >= 0.99 are suspect until audited).

Does NOT re-run or change the held-out evaluation. It re-simulates one held-out seed and checks:
  1. the detector's inputs contain only observed/ and context/ tables and none of their columns
     appear in truth/ or labels/;
  2. replacing the transformer series by itself shifted 7 days (or by a series from a different
     observation seed) collapses performance on the same episodes;
  3. accuracy when decided is reported with a Wilson interval.
Run: python -m shahid.leak_audit   (writes results/leak_audit.json)
"""
import json

import numpy as np

from shahid import detect, evaluate, scenario
from shahid.cp5_compare import inputs_of, split_of
from shahid.stamp import stamp, write_json

CFG = {"grid": "1-LV-urban6--0-sw", "seed": 301, "episodes_config": "configs/cp5_episodes.yaml",
       "other_seed": 999, "shift_days": 7, "test_week": 3}


def score(inp, fitted, thr, sim):
    v = detect.detect(inp, {**fitted, **thr}, "bayes")
    tab = evaluate.episode_table(v, sim["labels"])
    tab = tab[split_of(tab.start) == CFG["test_week"]]
    r = evaluate.rates(tab)
    dec = tab.verdict.isin(["OUTAGE", "COMMS_FAILURE"])
    k = int((tab.verdict == tab.cause)[dec].sum())
    r["accuracy_when_decided_wilson95"] = evaluate.wilson(k, int(dec.sum()))
    r["n_decided"] = int(dec.sum())
    return r


def main():
    thr = json.load(open("results/detector_params.json"))["thresholds"]["bayes"]
    base = scenario.simulate(scenario.merge(scenario.load_cfg("configs/baseline.yaml"),
                                            {"world": {"grid": CFG["grid"]}}))
    rows = np.arange(len(base["observed"]["transformer"]))
    fitted = detect.fit(inputs_of(base), rows[np.isin((rows // 672) % 4, [0, 1])])
    cfg = scenario.merge(scenario.load_cfg(CFG["episodes_config"]),
                         {"seed": CFG["seed"], "world": {"grid": CFG["grid"]}})
    sim = scenario.simulate(cfg)
    inp = inputs_of(sim)
    out = {"stamp": stamp(CFG, "python -m shahid.leak_audit")}

    # 1. input provenance
    truth_cols = set(sim["truth"]["meter_energy_true"].columns)
    label_cols = {c for df in sim["labels"].values() for c in df.columns}
    shared_ok = {"interval_start", "meter_id"}  # join keys present in observed data by design
    out["inputs"] = {k: list(map(str, df.columns)) for k, df in inp.items()}
    out["input_tables_from"] = {"readings": "observed", "trafo": "observed",
                                "meters": "context", "zones": "context"}
    out["overlap_with_truth_or_label_columns"] = sorted(
        {c for df in inp.values() for c in map(str, df.columns)}
        & ((truth_cols | label_cols) - shared_ok))

    # 2. controls
    out["actual"] = score(inp, fitted, thr, sim)
    tr = inp["trafo"].copy()
    tr["energy_kwh"] = np.roll(tr.energy_kwh.to_numpy(), 96 * CFG["shift_days"])
    out["transformer_shifted"] = score({**inp, "trafo": tr}, fitted, thr, sim)
    other = scenario.simulate(scenario.merge(cfg, {"seed": CFG["other_seed"]}))
    out["transformer_from_other_seed"] = score(
        {**inp, "trafo": other["observed"]["transformer"]}, fitted, thr, sim)
    write_json("results/leak_audit.json", out)
    for k in ["actual", "transformer_shifted", "transformer_from_other_seed"]:
        r = out[k]
        print(k, {x: round(r[x], 3) for x in ["accuracy_when_decided", "abstention_rate",
                                             "outage_recall", "comms_recall", "false_outage_rate",
                                             "missed_outage_rate"]}, r["n_decided"])
    print("overlap", out["overlap_with_truth_or_label_columns"])


if __name__ == "__main__":
    main()
