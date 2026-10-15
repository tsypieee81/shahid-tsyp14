"""Protocol 03: split candidate silent groups by line section (feeder partition from context zones) before
scoring with frozen version 1. Development: rule v3 check, the price per episode selector, merge frequency.

Run: python -m shahid.p5_split   (writes results/p5/p5_dev.json; needs python -m shahid.p2cache)
The functions are reused by the confirmatory batch (protocol 05).
"""
import json

import numpy as np
import pandas as pd

from shahid import p2eval as E
from shahid.p2cache import load
from shahid.stamp import stamp, write_json
from shahid.world import grid_meta

FAMS = {"cp5": [101, 102, 103], "cp6_concentrators_random": [201, 202], "feeder_semiurb5": [401, 402]}
VAL = [2]
SELECTORS = ["line", "feeder", "zone", "concentrator", "meters"]


def section_map(grid):
    meta = grid_meta(grid)
    sec = np.full(meta["n_meters"], -1)
    for k, f in enumerate(meta["feeders"]):
        sec[sorted(meta["zones"][f])] = k
    return sec


def mode_items(fam, seeds, mode):
    out = []
    for s in seeds:
        it = load(fam, s)
        it = dict(it, groups=it["groups"][it["groups"]["mode"] == mode].reset_index(drop=True))
        out.append(it)
    return out


def paired(fam, seeds, weeks, rng, boot=1000):
    """v1 against P5 on the same labelled episodes: rates per selector and paired abstention difference."""
    tabs = {}
    for mode in ("v1", "split"):
        ts = []
        for it in mode_items(fam, seeds, mode):
            d = E.decide(it["groups"], E.v1_posterior, 0.03)
            ts.append(E.episode_tab(it, it["groups"], d, weeks).assign(seed=it["seed"]))
        tabs[mode] = pd.concat(ts, ignore_index=True)
    a, b = tabs["v1"], tabs["split"]
    res = {"all": {"v1": E.summarise(a), "P5": E.summarise(b)}}
    for sel in sorted(set(a.selector)):
        ma, mb = a[a.selector == sel], b[b.selector == sel]
        ua, ub = (ma.verdict == "UNCERTAIN").to_numpy(), (mb.verdict == "UNCERTAIN").to_numpy()
        diffs = []
        for _ in range(boot):
            i = rng.integers(0, len(ua), len(ua))
            diffs.append(ub[i].mean() - ua[i].mean())
        res[sel] = {"n": len(ma), "v1": E.summarise(ma), "P5": E.summarise(mb),
                    "abstention_diff_P5_minus_v1": float(ub.mean() - ua.mean()),
                    "abstention_diff_ci95": [float(np.quantile(diffs, 0.025)), float(np.quantile(diffs, 0.975))]}
    return res, tabs


def union_tab(fam, seeds, mode, weeks):
    """Protocol 03 addendum A: episode outcome over every group at its onset sharing a meter with it.
    OUTAGE if any is OUTAGE, else UNCERTAIN if any is UNCERTAIN, COMMS_FAILURE if all are, MISSED if none.
    Also: subsets per episode and human items (version 1 escalation table, no gate)."""
    rows = []
    for it in mode_items(fam, seeds, mode):
        g, ep = it["groups"], it["episodes"]
        d = E.decide(g, E.v1_posterior, 0.03)
        out, _ = E.policy(g, d, gate=False, escalate=False)
        by_onset = g.groupby("onset").groups
        for e in ep[ep.week.isin(weeks)].itertuples():
            em = {f"m{m:03d}" for m in json.loads(e.meters)}
            idx = [i for i in by_onset.get(e.start, []) if em & set(g.at[i, "meters"])]
            vs = [d.at[i, "verdict"] for i in idx]
            v = ("MISSED" if not vs else "OUTAGE" if "OUTAGE" in vs else "UNCERTAIN" if "UNCERTAIN" in vs
                 else "COMMS_FAILURE")
            rows.append({"seed": it["seed"], "episode_id": e.episode_id, "cause": e.cause, "selector": e.selector,
                         "verdict": v, "latency_intervals": np.nan, "subsets": len(idx),
                         "human_items": int(sum(out[i] in E.HUMAN for i in idx))})
    return pd.DataFrame(rows)


def price(fam, seeds, weeks, rng, boot=1000):
    """Paired v1 / P5 comparison under the addendum-A outcome, per selector."""
    a, b = union_tab(fam, seeds, "v1", weeks), union_tab(fam, seeds, "split", weeks)
    res = {}
    for sel in ["all", *sorted(set(a.selector))]:
        ma, mb = (a, b) if sel == "all" else (a[a.selector == sel], b[b.selector == sel])
        ua, ub = (ma.verdict == "UNCERTAIN").to_numpy(), (mb.verdict == "UNCERTAIN").to_numpy()
        ha, hb = ma.human_items.to_numpy(), mb.human_items.to_numpy()
        da, dh = [], []
        for _ in range(boot):
            i = rng.integers(0, len(ua), len(ua))
            da.append(ub[i].mean() - ua[i].mean())
            dh.append(hb[i].mean() - ha[i].mean())
        res[sel] = {"n": len(ma), "v1": E.summarise(ma), "P5": E.summarise(mb),
                    "abstention_diff_P5_minus_v1": float(ub.mean() - ua.mean()),
                    "abstention_diff_ci95": [float(np.quantile(da, 0.025)), float(np.quantile(da, 0.975))],
                    "subsets_per_episode": {"v1": float(ma.subsets.mean()), "P5": float(mb.subsets.mean())},
                    "human_items_per_episode": {"v1": float(ha.mean()), "P5": float(hb.mean())},
                    "human_items_diff_ci95": [float(np.quantile(dh, 0.025)), float(np.quantile(dh, 0.975))]}
    return res


def merges(fam, seeds, weeks=None):
    """Version 1 groups matched to an outage episode that contain meters outside the episode (powered
    meters), per transformer-year, all weeks; cross- and same-feeder; verdicts under v1 and under P5."""
    out = {"groups_matched_to_outage": 0, "with_powered_meter": 0, "cross_feeder": 0, "same_feeder_only": 0,
           "wrong_comms_p095_v1": 0, "wrong_comms_p095_P5": 0, "cases": []}
    days = 0.0
    for v1it, spit in zip(mode_items(fam, seeds, "v1"), mode_items(fam, seeds, "split")):
        sec = section_map(v1it["grid"])
        days += (np.isin(v1it["row_weeks"], weeks).sum() if weeks is not None else v1it["n_rows"]) / 96
        g, ep = v1it["groups"], v1it["episodes"]
        dv = E.decide(g, E.v1_posterior, 0.03)
        gs = spit["groups"]
        ds = E.decide(gs, E.v1_posterior, 0.03)
        spos = dict(zip(gs.matched_episode[gs.matched_episode >= 0].astype(int), gs.index[gs.matched_episode >= 0]))
        outs = ep[ep.cause == "OUTAGE"].set_index("episode_id")
        for i in g.index[(g.matched_episode >= 0) & (g.week.isin(weeks) if weeks is not None else True)]:
            eid = int(g.at[i, "matched_episode"])
            if eid not in outs.index:
                continue
            out["groups_matched_to_outage"] += 1
            em = set(json.loads(outs.at[eid, "meters"]))
            gm = [int(m[1:]) for m in g.at[i, "meters"]]
            extra = [m for m in gm if m not in em]
            if not extra:
                continue
            out["with_powered_meter"] += 1
            esec = {sec[m] for m in em}
            cross = any(sec[m] not in esec for m in extra)
            out["cross_feeder" if cross else "same_feeder_only"] += 1
            wrong = dv.at[i, "verdict"] == "COMMS_FAILURE" and dv.at[i, "p_comms"] >= 0.95
            j = spos.get(eid)
            wrong5 = j is not None and ds.at[j, "verdict"] == "COMMS_FAILURE" and ds.at[j, "p_comms"] >= 0.95
            if cross:
                out["wrong_comms_p095_v1"] += int(wrong)
                out["wrong_comms_p095_P5"] += int(wrong5)
            out["cases"].append({"seed": v1it["seed"], "episode": eid, "n_episode": len(em), "n_extra": len(extra),
                                 "cross_feeder": bool(cross), "v1": dv.at[i, "verdict"], "v1_p": float(dv.at[i, "p_comms"]),
                                 "P5": ds.at[j, "verdict"] if j is not None else "MISSED",
                                 "P5_p": float(ds.at[j, "p_comms"]) if j is not None else None})
    out["transformer_years"] = days / 365
    out["with_powered_meter_per_transformer_year"] = out["with_powered_meter"] / (days / 365)
    return out


def main():
    rng = np.random.default_rng(3)
    res = {"stamp": stamp({"protocol": "docs/process/protocols/03_p5_split.md", "fams": FAMS},
                          "python -m shahid.p5_split"), "label": "development, selection data"}
    ffv = E.fault_free(mode_items("ff_semiurb5", [1], "v1"),
                       [E.decide(it["groups"], E.v1_posterior, 0.03) for it in mode_items("ff_semiurb5", [1], "v1")], VAL)
    ffs = E.fault_free(mode_items("ff_semiurb5", [1], "split"),
                       [E.decide(it["groups"], E.v1_posterior, 0.03) for it in mode_items("ff_semiurb5", [1], "split")], VAL)
    res["fault_free_val"] = {"v1": ffv, "P5": ffs}
    res["cp5_val"], tabs = paired("cp5", FAMS["cp5"], VAL, rng)
    res["v3_feasible"] = {"v1": bool(E.feasible(res["cp5_val"]["all"]["v1"], ffv)),
                          "P5": bool(E.feasible(res["cp5_val"]["all"]["P5"], ffs))}
    res["concentrators_random_val"], _ = paired("cp6_concentrators_random", FAMS["cp6_concentrators_random"], VAL, rng)
    res["whole_feeder_all_weeks"], _ = paired("feeder_semiurb5", FAMS["feeder_semiurb5"], [0, 1, 2, 3], rng)
    res["merges"] = {f: merges(f, s) for f, s in FAMS.items()}
    res["price_addendum_A"] = {"cp5_val": price("cp5", FAMS["cp5"], VAL, rng),
                               "concentrators_random_val": price("cp6_concentrators_random",
                                                                 FAMS["cp6_concentrators_random"], VAL, rng),
                               "whole_feeder_all_weeks": price("feeder_semiurb5", FAMS["feeder_semiurb5"], [0, 1, 2, 3], rng)}
    write_json("results/p5/p5_dev.json", res)
    print(json.dumps({"v3": res["v3_feasible"], "all": {k: {m: round(v, 4) for m, v in r.items() if m in (
        "missed_outage_rate", "false_outage_rate", "abstention_rate")} for k, r in res["cp5_val"]["all"].items()},
        "merges": {f: {k: v for k, v in m.items() if k != "cases"} for f, m in res["merges"].items()}}, default=str, indent=1))


if __name__ == "__main__":
    from pathlib import Path
    Path("results/p5").mkdir(parents=True, exist_ok=True)
    main()
