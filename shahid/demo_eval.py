"""Tooling: simulation outcomes for the replayed demo days (evaluation view only, decision 0007).

Run: python -m shahid.demo_eval [scenario ...]   (after python -m shahid.demo_day)

Re-runs the same deterministic simulation as shahid.demo_day, reads its labels (never passed to
the detector) and writes results/demo/<scenario>_eval.json: the true cause of each replayed silent
group (majority of its meters' cells, shahid.evaluate.truth_of_groups) and every labelled outage or
comms episode of the day with the verdict it received (registered matching rule). The operator UI
path never opens these files; only ui/panels/evaluation.py does.
"""
import json
import sys

import pandas as pd

from shahid import evaluate, scenario
from shahid.demo_day import CFG, OUT, scenario_cfg
from shahid.stamp import stamp, write_json


def run(name):
    cfg, _, day0 = scenario_cfg(name)
    replay = json.load(open(OUT / f"{name}.json", encoding="utf8"))
    sim = scenario.simulate(cfg)
    labels = sim["labels"]
    v = pd.DataFrame([{"onset": pd.Timestamp(g["onset"]), "meters": g["meters"], "verdict": g["verdict"],
                       "latency_intervals": g["decided_lead"] + 2, "p_comms": g["posterior_comms"]}
                      for g in replay["groups"]])
    truth = evaluate.truth_of_groups(v, labels["cells"]) if len(v) else []
    day_start = pd.Timestamp(replay["trace"][0]["interval_start"])
    ep = labels["episodes"]
    ep = ep[ep.start >= day_start] if len(ep) else ep  # a fault-free day has no episodes
    tab = evaluate.episode_table(v, {"episodes": ep}) if len(ep) else pd.DataFrame()
    episodes = [{"cause": r.cause, "start": str(r.start), "n_meters": int(r.n_meters), "verdict": r.verdict}
                for r in tab.itertuples()] if len(tab) else []
    write_json(OUT / f"{name}_eval.json", {
        "stamp": stamp(cfg, f"python -m shahid.demo_eval {name}"),
        "note": "SIMULATION EVALUATION: labels are not available to the detector",
        "group_truth": [{"onset": g["onset"], "n_meters": g["n_meters"], "verdict": g["verdict"], "truth": t}
                        for g, t in zip(replay["groups"], truth)],
        "episodes": episodes})
    print(name, "groups:", len(truth), "episodes:", len(episodes), flush=True)


def main(names):
    import yaml
    names = names or list(yaml.safe_load(open(CFG, encoding="utf8"))["scenarios"])
    for n in names:
        run(n)


if __name__ == "__main__":
    main(sys.argv[1:])
