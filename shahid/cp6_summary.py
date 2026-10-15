"""CP6 summary: cell table and detectability curves from results/cp6 (no simulation).

Run: python -m shahid.cp6_summary   (writes results/cp6_summary.json)
"""
import glob
import json
import os

import pandas as pd

from shahid import evaluate
from shahid.cp5_compare import primary_method
from shahid.stamp import stamp, write_json

BINS = [0, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 1.0]
KEYS = ["n_outage", "n_comms", "accuracy_when_decided", "abstention_rate", "outage_recall",
        "comms_recall", "false_outage_rate", "missed_outage_rate", "balanced_correct",
        "unlabelled_false_outages_per_meter_day"]


def curve(tab, method, frac):
    t = tab[tab.method == method].join(frac, on=["seed", "episode_id"])
    out = []
    for k, g in t.groupby(pd.cut(t.frac, BINS), observed=True):
        o, c = g[g.cause == "OUTAGE"], g[g.cause == "COMMS_FAILURE"]
        ok = int((g.verdict == g.cause).sum())
        out.append({"bin": str(k), "n": len(g), "correct": ok / len(g),
                    "correct_ci95": evaluate.wilson(ok, len(g)),
                    "abstention": float((g.verdict == "UNCERTAIN").mean()),
                    "wrong": float(((g.verdict != g.cause) & (g.verdict != "UNCERTAIN")).mean()),
                    "false_outages": int((c.verdict == "OUTAGE").sum()), "n_comms": len(c),
                    "missed_outages": int(o.verdict.isin(["COMMS_FAILURE", "MISSED"]).sum()),
                    "n_outage": len(o)})
    return out


def main():
    primary = primary_method()
    cells = {}
    stamps = {}
    for f in sorted(glob.glob("results/cp6/*.json")):
        d = json.load(open(f))
        name = os.path.basename(f)[:-5]
        cells[name] = {m: {k: r[k] for k in KEYS} | {"ci95": r["ci95"]}
                       for m, r in d["methods"].items()}
        stamps[name] = d["stamp"]["commit"]
    tab = pd.read_parquet("results/cp6/nominal_episodes.parquet")
    # |expected silent energy| / typical transformer energy, taken from the primary method
    frac = tab[tab.method == primary].set_index(["seed", "episode_id"]).silent_load_fraction.abs()
    frac = frac.rename("frac")
    n_unbinned = int(tab[tab.method == primary].silent_load_fraction.isna().sum())
    curves = {m: curve(tab, m, frac) for m in [primary, "naive", "step", "count"]}
    write_json("results/cp6_summary.json", {
        "stamp": stamp({"bins": BINS, "primary": primary}, "python -m shahid.cp6_summary"),
        "primary": primary, "cell_commits": stamps, "cells": cells,
        "detectability_nominal": curves, "episodes_without_group_match": n_unbinned})
    for r in curves[primary]:
        print(r["bin"], r["n"], round(r["correct"], 3), round(r["abstention"], 3),
              r["false_outages"], r["missed_outages"])


if __name__ == "__main__":
    main()
