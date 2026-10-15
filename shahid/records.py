"""Per-episode and per-group records for the frozen version 1 method (CP10).

Regenerates the CP5, CP6 and CP7 families (original seeds) plus the CP10 addendum families (new
seeds, docs/eval_protocol.md addendum A) and stores, per family:
  results/records/<family>__episodes.parquet  one row per labelled OUTAGE/COMMS episode and method
  results/records/<family>__groups.parquet    one row per detected silent group and method
Evidence values (R, M, sd_O, sd_C) are kept for the physics methods. Nothing is tuned.
`--verify` checks that the regenerated CP5/CP6/CP7 aggregates equal the published result files.

Run: python -m shahid.records [family ...] [--verify]
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
from shahid.cp6_sweep import CELLS
from shahid.world import MAX_WORKERS, grid_meta

OUT = Path("results/records")
PHYS = ["bayes", "lr", "share", "ztest"]
BASES = ["naive", "step", "count", "structure"]
DEV, HELD = "1-LV-semiurb5--0-sw", "1-LV-urban6--0-sw"
EV_COLS = ["R", "M", "sd_O", "sd_C", "n_intervals", "gap0", "p_comms", "latency_intervals"]


def _base(grid, extra=None):
    return scenario.merge(scenario.load_cfg("configs/baseline.yaml"),
                          {"world": {"grid": grid}, **(extra or {})})


def _eps(grid, extra=None):
    return scenario.merge(scenario.load_cfg("configs/cp5_episodes.yaml"),
                          {"world": {"grid": grid}, **(extra or {})})


def feeder_events(grid, seed, n_days=366, first_day=15):
    """Addendum A: about one whole-feeder event per day, alternating outage / comms failure."""
    meta = grid_meta(grid)
    rng = np.random.default_rng(seed + 1000)
    ev = []
    for i, day in enumerate(range(first_day, n_days - 1)):
        f = int(rng.integers(len(meta["feeders"])))
        start = int(day * 96 + rng.integers(0, 96 - 20))
        dur = int(rng.integers(4, 17))
        if i % 2 == 0:
            ev.append({"type": "outage", "feeder": f, "start_step": start, "duration_steps": dur})
        else:
            ev.append({"type": "comms_failure", "zone": int(meta["feeders"][f]),
                       "start_step": start, "duration_steps": dur})
    return ev


def families():
    """name -> (list of (seed, cfg)), fit config, history_days or None."""
    fam = {"cp5": ([(s, _eps(DEV, {"seed": s})) for s in [101, 102, 103]], _base(DEV), None),
           "cp7_heldout_urban6": ([(s, _eps(HELD, {"seed": s})) for s in [301, 302, 303]],
                                  _base(HELD), "refit"),
           "cp7_dev_semiurb5": ([(s, _eps(DEV, {"seed": s})) for s in [301, 302, 303]],
                                _base(DEV), "refit"),
           "ff_semiurb5": ([(1, _base(DEV))], _base(DEV), None),
           "ff_urban6": ([(1, _base(HELD))], _base(HELD), "refit")}
    cp6_base = scenario.load_cfg("configs/cp6_base.yaml")
    for c, over in CELLS.items():
        over = dict(over)
        h = over.pop("_history_days", None)
        fam[f"cp6_{c}"] = ([(s, scenario.merge(cp6_base, {**over, "seed": s})) for s in [201, 202]],
                           _base(DEV), h)
    # ---- addendum A (new seeds)
    for g, seeds, name in [(DEV, [401, 402], "feeder_semiurb5"), (HELD, [411, 412], "feeder_urban6")]:
        fam[name] = ([(s, scenario.merge(_base(g), {"seed": s, "events": feeder_events(g, s)}))
                      for s in seeds], _base(g), None if g == DEV else "refit")
    loss = {"comms": {"p_missing": 0.10}}
    fam["loss10_ff_semiurb5"] = ([(421, _base(DEV, {**loss, "seed": 421}))], _base(DEV), None)
    fam["loss10_ff_urban6"] = ([(422, _base(HELD, {**loss, "seed": 422}))], _base(HELD), "refit")
    fam["loss10_semiurb5"] = ([(s, _eps(DEV, {**loss, "seed": s})) for s in [431, 432]],
                              _base(DEV), None)
    fam["loss10_urban6"] = ([(s, _eps(HELD, {**loss, "seed": s})) for s in [433, 434]],
                            _base(HELD), "refit")
    fam["diag_tmeter2_ff"] = ([(441, _base(DEV, {"seed": 441, "tmeter": {"gain_sd": 0.02,
                                                                         "noise_rel_sd": 0.01}}))],
                              _base(DEV), None)
    fam["diag_unmet5_ff"] = ([(442, _base(DEV, {"seed": 442, "world": {
        "grid": DEV, "unmetered": {"kind": "profile", "kw": 5.0}}}))], _base(DEV), None)
    for w in [1, 2, 3]:
        fam[f"world{w}_nominal"] = ([(s, scenario.merge(cp6_base, {"seed": s, "world": {"seed": w}}))
                                     for s in [201, 202]],
                                    scenario.merge(_base(DEV), {"world": {"seed": w}}), "refit_world")
    # ---- addendum B (CP11): new fault-free observation seeds on cached worlds; untouched grid
    for sd in [451, 452, 453, 454]:
        fam[f"ffx_semiurb5_{sd}"] = ([(sd, _base(DEV, {"seed": sd}))], _base(DEV), None)
    for sd in [455, 456, 457, 458]:
        fam[f"ffx_urban6_{sd}"] = ([(sd, _base(HELD, {"seed": sd}))], _base(HELD), "refit")
    R3G = "1-LV-rural3--0-sw"
    fam["rural3_ff"] = ([(1, _base(R3G))], _base(R3G), "refit")
    fam["rural3_eps"] = ([(sd, _eps(R3G, {"seed": sd})) for sd in [501, 502]], _base(R3G), "refit")
    return fam


def fitted_for(fit_cfg, mode):
    frozen = json.load(open("results/detector_params.json"))
    if mode is None:
        return frozen["fitted"], frozen["thresholds"]
    base = scenario.simulate(fit_cfg)
    rows = np.arange(len(base["observed"]["transformer"]))
    train = rows[np.isin((rows // 672) % 4, [0, 1])]
    h = mode if isinstance(mode, int) else detect.DEFAULTS["history_days"]
    return detect.fit(inputs_of(base), train, history_days=h), frozen["thresholds"]


def size_class(meters, meta, conc_sets):
    """Topology class of a silent set (DESIGN CHOICE: zones come from single line openings)."""
    s = set(meters)
    for f in meta["feeders"]:
        if s == set(meta["zones"][f]):
            return "feeder"
    if len(s) == 1:
        return "single"
    if any(s == set(z) for z in meta["zones"].values()):
        return "branch"
    return "scattered"


def run_family(name):
    os.environ["SHAHID_SERIAL"] = "1"
    sims, fit_cfg, mode = families()[name]
    fitted, thr = fitted_for(fit_cfg, mode)
    meta = grid_meta(sims[0][1]["world"]["grid"])
    eps, grps = [], []
    for seed, cfg in sims:
        sim = scenario.simulate(cfg)
        inp = inputs_of(sim)
        idx = pd.DatetimeIndex(sim["observed"]["transformer"].interval_start)
        ev = detect.evidence_table(inp, fitted)
        verdicts = {m: detect.decide_table(ev, m, {**fitted, **thr[m]}) for m in PHYS}
        verdicts.update({b: baselines.detect(inp, b) for b in BASES})
        lab = dict(sim["labels"])
        if "cause" not in lab["episodes"]:  # fault-free scenario: no labelled episodes
            lab["episodes"] = pd.DataFrame(columns=["episode_id", "cause", "start", "end",
                                                    "n_meters", "meters", "line", "selector"])
        ep = lab["episodes"]
        ep = ep[ep.cause.isin(["OUTAGE", "COMMS_FAILURE"])].reset_index(drop=True)
        cls = [size_class(json.loads(m), meta, None) for m in ep.meters]
        for m, v in verdicts.items():
            tab = evaluate.episode_table(v, lab).assign(seed=seed, method=m, size_class=cls)
            for c in EV_COLS:
                if c in v:
                    tab[c] = [v.at[i, c] if i >= 0 else np.nan for i in tab.verdict_row]
            tab["week"] = split_of(tab.start)
            eps.append(tab.drop(columns=["meters"]))
            if len(v):
                truth = evaluate.truth_of_groups(v, lab["cells"])
                matched = np.full(len(v), -1)
                for k, i in enumerate(tab.verdict_row):
                    if i >= 0:
                        matched[i] = tab.episode_id.iloc[k]
                g = pd.DataFrame({"seed": seed, "method": m, "onset": v.onset,
                                  "n_meters": v.n_meters, "verdict": v.verdict, "truth": truth,
                                  "matched_episode": matched, "week": split_of(v.onset)})
                for c in EV_COLS:
                    if c in v:
                        g[c] = v[c].to_numpy()
                grps.append(g)
        n_days = len(idx) / 96
        grps.append(pd.DataFrame({"seed": [seed], "method": ["_meta"], "n_meters": [len(inp["meters"])],
                                  "verdict": [f"days={n_days}"]}))
    OUT.mkdir(parents=True, exist_ok=True)
    pd.concat(eps, ignore_index=True).to_parquet(OUT / f"{name}__episodes.parquet")
    pd.concat(grps, ignore_index=True).to_parquet(OUT / f"{name}__groups.parquet")
    return name


# ---------------------------------------------------------------- verification
def _cmp(pub, tab, fa=None, keys=("outage_recall", "comms_recall", "false_outage_rate",
                                  "missed_outage_rate", "abstention_rate", "accuracy_when_decided")):
    r = evaluate.rates(tab)
    bad = {k: (pub[k], r[k]) for k in keys
           if not (pub[k] == r[k] or (np.isnan(pub[k]) and np.isnan(r[k]))
                   or abs(pub[k] - r[k]) < 1e-12)}
    return bad


def verify():
    out = {}
    cp5 = json.load(open("results/cp5_compare.json"))["results_val"]
    t = pd.read_parquet(OUT / "cp5__episodes.parquet")
    for m in PHYS + BASES:
        out[f"cp5/{m}"] = _cmp(cp5[m], t[(t.method == m) & (t.week == 2)])
    for c in CELLS:
        p = OUT / f"cp6_{c}__episodes.parquet"
        if not p.exists():
            out[f"cp6/{c}"] = "records missing"
            continue
        pub = json.load(open(f"results/cp6/{c}.json"))["methods"]
        t = pd.read_parquet(p)
        for m in PHYS + BASES:
            out[f"cp6/{c}/{m}"] = _cmp(pub[m], t[(t.method == m) & (t.week != 3)])
    cp7 = json.load(open("results/cp7_heldout.json"))["targets"]
    for fam, tgt in [("cp7_heldout_urban6", "heldout_urban6"), ("cp7_dev_semiurb5", "dev_semiurb5")]:
        t = pd.read_parquet(OUT / f"{fam}__episodes.parquet")
        for m in PHYS + BASES:
            out[f"cp7/{tgt}/{m}"] = _cmp(cp7[tgt]["results"][m], t[(t.method == m) & (t.week == 3)])
    bad = {k: v for k, v in out.items() if v}
    Path("results/records/verify.json").write_text(json.dumps(
        {"checked": len(out), "mismatches": bad}, indent=1, default=str))
    print("checked", len(out), "mismatches", len(bad))
    for k, v in list(bad.items())[:20]:
        print(" ", k, v)
    return not bad


def main(argv):
    if "--verify" in argv:
        sys.exit(0 if verify() else 1)
    names = [a for a in argv if not a.startswith("--")] or list(families())
    names = [n for n in names if not (OUT / f"{n}__groups.parquet").exists()]
    with ProcessPoolExecutor(max(1, min(MAX_WORKERS, len(names)))) as ex:
        for n in ex.map(run_family, names):
            print("done", n, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
