"""Representative demonstration: three typical cases and one documented failure, plus a count over
every labelled event in one committed dataset folder. SIMULATED data (SimBench grid).

Reads only committed files: dataset/episodes_semiurb5_seed101 (observed, context, labels; never
truth), results/detector_params.json, results/decision_log_demo.jsonl and configs/smoke.yaml.
Writes only results/demo_summary.json (stamped).
Run: python -m shahid.demo
"""
import json

import pandas as pd
import yaml

from shahid import detect, evaluate, explain
from shahid.stamp import stamp, write_json

DATA = "dataset/episodes_semiurb5_seed101"
MIN_METERS = 10
RULE = (f"Cases are fixed by this rule: the first labelled episode (by start time) with at least "
        f"{MIN_METERS} meters that (1) is an outage decided OUTAGE, (2) is a communication failure "
        f"decided COMMS_FAILURE, (3) is abstained (UNCERTAIN); (4) the documented wrong verdict of "
        f"ledger C9-01 (smoke scenario, first entry of results/decision_log_demo.jsonl).")


def known_failure():
    """C9-01: first record of the committed demo log; true cause from the smoke scenario's events."""
    entry = json.loads(open("results/decision_log_demo.jsonl", encoding="utf8").readline())
    cfg = yaml.safe_load(open("configs/smoke.yaml"))
    t0 = pd.Timestamp("2016-01-01") + pd.Timedelta(days=cfg["world"]["start_day"])
    truth = {str(t0 + pd.Timedelta(minutes=15) * e["start_step"]): e["type"] for e in cfg["events"]}
    cause = {"outage": "OUTAGE", "comms_failure": "COMMS_FAILURE"}[truth[entry["record"]["onset"]]]
    return entry["explanation"], cause


def main():
    p = json.load(open("results/detector_params.json"))
    inputs = detect.load_inputs(DATA)
    labels = {k: pd.read_parquet(f"{DATA}/labels/{k}.parquet") for k in ["episodes", "cells"]}
    v = detect.detect(inputs, {**p["fitted"], **p["thresholds"]["bayes"]}, "bayes")
    tab = evaluate.episode_table(v, labels)
    big = tab[tab.n_meters >= MIN_METERS]
    picks = [("typical: outage decided correctly", big[(big.cause == "OUTAGE") & (big.verdict == "OUTAGE")]),
             ("typical: communication failure decided correctly",
              big[(big.cause == "COMMS_FAILURE") & (big.verdict == "COMMS_FAILURE")]),
             ("typical: abstained, sent to a human", big[big.verdict == "UNCERTAIN"])]
    print("SIMULATED data (SimBench grid), frozen version 1 detector (lr_band).")
    print(RULE, "\n")
    for title, rows in picks:
        c = rows.sort_values("start").iloc[0]
        rec = explain.verdict_record(v.loc[int(c.verdict_row)], "version 1 (frozen)")
        print(f"[{title}] true cause: {c.cause}")
        print(explain.explain(rec), "\n")
    text, cause = known_failure()
    print(f"[known failure, ledger C9-01] true cause: {cause}")
    print(text, "\n")
    counts = {"decided_correctly": int(((tab.verdict == tab.cause)).sum()),
              "abstained": int((tab.verdict == "UNCERTAIN").sum()),
              "decided_wrongly": int((tab.verdict.isin(["OUTAGE", "COMMS_FAILURE"]) & (tab.verdict != tab.cause)).sum()),
              "never_detected": int((tab.verdict == "MISSED").sum())}
    n = len(tab)
    print(f"All {n} labelled outage and communication-failure events in {DATA} (whole year): "
          f"{counts['decided_correctly']} decided correctly, {counts['abstained']} abstained, "
          f"{counts['decided_wrongly']} decided wrongly, {counts['never_detected']} never detected.")
    write_json("results/demo_summary.json", {
        "stamp": stamp({"data": DATA, "rule": RULE}, "python -m shahid.demo"),
        "label": "SIMULATED; one dataset folder, whole year, all labelled events; not a held-out result",
        "n_labelled_events": n, **counts, "rule": RULE})


if __name__ == "__main__":
    main()
