"""Tooling: replay one simulated day through the real, frozen pipeline for the operator UI preview.

Run: python -m shahid.demo_day [scenario ...]   (default: every scenario in configs/demo_scenarios.yaml)

scenario -> observe -> detect (frozen bayes parameters, results/detector_params.json) -> explain.
Only the observed and context tables reach the detector (cp5_compare.inputs_of). Writes, per scenario:
  results/demo/<scenario>.json        stamped: per-interval trace (balance, gap, reporting counts as
                                      known at that replay time), arrival and voltage per meter,
                                      every silent group with its evidence and posterior at each
                                      lead, expected energy per interval, verdict, explanation, rule
  results/demo/<scenario>_log.jsonl   hash-chained decision log, same format as shahid.explain.demo
Simulation outcomes for the evaluation view are written separately by shahid.demo_eval.
SIMULATED. Not real-time: the day is computed offline and replayed.
"""
import json
import sys
from pathlib import Path

import numpy as np
import yaml

from shahid import detect, explain, scenario
from shahid.cp5_compare import inputs_of
from shahid.stamp import git_commit, stamp, write_json
from shahid.world import grid_meta

CFG = "configs/demo_scenarios.yaml"
OUT = Path("results/demo")


def scenario_cfg(name, path=CFG):
    """Scenario config: defaults + demo world + events placed on the last (replayed) day."""
    d = yaml.safe_load(open(path, encoding="utf8"))
    s = d["scenarios"][name]
    world = {**d["world"], **s.get("world", {})}
    day0 = (world["days"] - 1) * 96
    events = []
    for ev in s["events"]:
        e = {k: v for k, v in ev.items() if k != "hour"}
        e["start_step"] = day0 + round(ev["hour"] * 4)  # hours on the 15-minute grid (6.25 = 06:15)
        events.append(e)
    cfg = scenario.merge(yaml.safe_load(open("configs/defaults.yaml", encoding="utf8")),
                         {"world": world, "seed": d["seed"], "events": events})
    return cfg, s["description"], day0


def frozen_params():
    fp = json.load(open("results/detector_params.json", encoding="utf8"))
    return {**fp["fitted"], **fp["thresholds"]["bayes"]}


EXPECTED_SPAN = 16  # intervals of expected energy stored per group (ponytail: covers the decision window + 2.5 h)


def expected_series(E, A, T, t0, group, p):
    """Expected energy of the group per interval from onset (comms-failure hypothesis), as the detector's
    own window evidence differenced over growing windows: M(t0..t) - M(t0..t-1), each as known at t+1."""
    M = [detect.evidence(E, A, T, t0, group, tau, p)["M"] for tau in range(t0 + 1, min(t0 + EXPECTED_SPAN, len(T)) + 1)]
    return [M[0]] + [b - a for a, b in zip(M, M[1:])]


def cursor_stats(A, T, E, day0):
    """Per replay time c (end of interval c): what is known from arrivals A <= c.
    reporting: meters whose reading of interval c-1 has arrived; late: readings of the day that arrived
    after their usual delivery; outstanding: readings of the day not yet arrived (lost or still stored)."""
    out = []
    for c in range(day0, len(T)):
        rows = slice(day0, c)
        late = ((A[rows] > np.arange(day0, c)[:, None] + 1) & (A[rows] <= c)).sum() if c > day0 else 0
        out.append({"n_reporting": int((A[c - 1] <= c).sum()), "n_late": int(late),
                    "n_outstanding": int((A[rows] > c).sum()) if c > day0 else 0})
    return out


def replay(inputs, params, day0, version="bayes"):
    """Evidence, verdict, explanation and escalation for every silent group with onset on or after
    row day0, plus the per-interval trace. inputs: observed + context tables only."""
    p = {**detect.DEFAULTS, **params}
    index, meters, E, A, T = detect.arrays(inputs)
    table = [g for g in detect.evidence_table(inputs, p) if g["t0"] >= day0]
    verdicts = detect.decide_table(table, "bayes", p)
    prior = np.log(p["prior_comms"] / (1 - p["prior_comms"]))
    esc = explain.load_escalation()
    groups, log = [], []
    for g, (_, row) in zip(table, verdicts.iterrows()):
        leads = []
        for L, ev in enumerate(g["evs"]):
            verdict, post, _ = detect.score(ev, "bayes", p)
            llr = float(np.log(post / (1 - post)) - prior) if post is not None and 0 < post < 1 else None
            leads.append({"lead": L, "R": ev["R"], "M": ev["M"], "sd_O": ev["sd_O"], "sd_C": ev["sd_C"],
                          "posterior_comms": post, "llr": llr, "verdict": verdict})
        rec = explain.verdict_record(row, version)
        text = explain.explain(rec)
        rule = explain.escalate(rec, esc)
        log.append((rec, text, rule))
        idx = [meters.index(m) for m in g["meters"]]
        groups.append({"onset": str(g["onset"]), "t0": int(g["t0"]), "n_meters": g["n_meters"],
                       "expected_kwh": expected_series(E, A, T, g["t0"], idx, p),
                       "meters": g["meters"], "leads": leads, "decided_lead": int(row.latency_intervals) - p["K"],
                       "verdict": row.verdict, "posterior_comms": row.p_comms, "record": rec,
                       "explanation": text, "escalation": rule})
    w = np.arange(day0, len(T))
    ontime = np.where(A[w] <= w[:, None] + 1, E[w], np.nan)  # readings arrived by the end of the next interval
    reporting = np.nansum(ontime, 1)
    trace = [{"interval_start": str(index[t]), "transformer_kwh": float(T[t]),
              "reporting_meters_kwh": float(reporting[i]), "meters_reporting": int(np.isfinite(ontime[i]).sum()),
              "gap_kwh": float(T[t] - reporting[i]), **s}
             for i, (t, s) in enumerate(zip(w, cursor_stats(A, T, E, day0)))]
    # gap baseline as the detector forms it: median gap of fully reported intervals of the previous day
    prev = np.arange(day0 - 96, day0)
    full = (A[prev] <= day0).all(1)  # fully known by the start of the replayed day
    gap0 = float(np.median(T[prev][full] - E[prev][full].sum(1))) if full.any() else None
    rel = np.where(np.isfinite(A[w]), A[w] - day0, -1).astype(int)  # arrival interval within the day, -1 never
    V = inputs["readings"].pivot_table(index="interval_start", columns="meter_id", values="voltage_v")
    V = V.reindex(index=index[w], columns=meters)
    return {"trace": trace, "groups": groups, "n_meters": len(meters),
            "gap_baseline_kwh": gap0, "gap_sd_kwh": float(p["gap_sd"]),
            "arrival": rel.tolist(), "voltage_v": [[None if np.isnan(x) else round(float(x), 1) for x in r] for r in V.to_numpy()],
            "prev_day_kwh": np.round(np.nansum(E[day0 - 96:day0], 0), 3).tolist()}, log


def run(name):
    cfg, desc, day0 = scenario_cfg(name)
    sim = scenario.simulate(cfg)
    inputs = inputs_of(sim)  # the detector sees observed + context only
    out, log = replay(inputs, frozen_params(), day0, f"bayes@{git_commit()}")
    topo = grid_meta(cfg["world"]["grid"])  # network topology (feeder membership), as an operator holds it
    feeder = [-1] * topo["n_meters"]
    for k, f in enumerate(topo["feeders"]):
        for m in topo["zones"][f]:
            feeder[m] = k
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {"scenario": name, "description": desc, "grid": cfg["world"]["grid"],
            "pv_kw": inputs["meters"].pv_kw.round(3).tolist(),
            "concentrator_id": inputs["meters"].concentrator_id.tolist(), "feeder": feeder,
            "meter_id": inputs["meters"].meter_id.tolist(),
            "zones": inputs["zones"].groupby("zone_id").meter_id.apply(list).to_dict()}
    write_json(OUT / f"{name}.json", {"stamp": stamp(cfg, f"python -m shahid.demo_day {name}"),
                                      "note": "SIMULATED replay; frozen detector; not real-time",
                                      **meta, **out})
    lp = OUT / f"{name}_log.jsonl"
    lp.unlink(missing_ok=True)
    for rec, text, rule in log:
        explain.append_log(lp, rec, text, rule)
    print(name, "groups:", len(out["groups"]), "log valid:", explain.verify_log(lp), flush=True)


def main(names):
    names = names or list(yaml.safe_load(open(CFG, encoding="utf8"))["scenarios"])
    for n in names:
        run(n)


if __name__ == "__main__":
    main(sys.argv[1:])
