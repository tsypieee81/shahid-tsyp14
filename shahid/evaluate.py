"""Episode-level evaluation. Reads labels (evaluation only; never imported by the detector).

Truth of a detected silent group: OUTAGE if most of its (meter, onset) cells are labelled OUTAGE,
otherwise COMMS_FAILURE (the customers still had power: concentrator failure, random loss or
delay). Labelled episodes with no detected group of Jaccard >= 0.5 at the same onset are MISSED.
"""
import json

import numpy as np
import pandas as pd


def truth_of_groups(verdicts, cells):
    c = cells[cells.cause == "OUTAGE"]
    out_cells = set(zip(c.interval_start, c.meter_id.astype(str)))
    t = []
    for _, v in verdicts.iterrows():
        k = sum((v.onset, m) in out_cells for m in v.meters)
        t.append("OUTAGE" if k > len(v.meters) / 2 else "COMMS_FAILURE")
    return np.array(t)


def match_episodes(verdicts, episodes):
    """For each labelled OUTAGE/COMMS episode: index of the matched verdict row or -1."""
    by_onset = verdicts.groupby("onset").groups if len(verdicts) else {}
    out = []
    for _, e in episodes.iterrows():
        lm = {f"m{m:03d}" for m in json.loads(e.meters)}
        best, bj = -1, 0.5
        for i in by_onset.get(e.start, []):
            vm = set(verdicts.at[i, "meters"])
            j = len(lm & vm) / len(lm | vm)
            if j >= bj:
                best, bj = i, j
        out.append(best)
    return np.array(out)


def episode_table(verdicts, labels):
    """One row per labelled silent episode with the verdict it received."""
    ep = labels["episodes"]
    ep = ep[ep.cause.isin(["OUTAGE", "COMMS_FAILURE"])].reset_index(drop=True)
    idx = match_episodes(verdicts, ep)
    v = [verdicts.at[i, "verdict"] if i >= 0 else "MISSED" for i in idx]
    lat = [verdicts.at[i, "latency_intervals"] if i >= 0 else np.nan for i in idx]
    p = [verdicts.at[i, "p_comms"] if i >= 0 and "p_comms" in verdicts else np.nan for i in idx]
    return ep.assign(verdict=v, latency_intervals=lat, p_comms=p, verdict_row=idx)


def rates(tab):
    """Metrics over an episode table (truth column `cause`, prediction `verdict`)."""
    o, c = tab[tab.cause == "OUTAGE"], tab[tab.cause == "COMMS_FAILURE"]
    called_o = tab.verdict == "OUTAGE"
    decided = tab.verdict.isin(["OUTAGE", "COMMS_FAILURE"])
    f = lambda a, b: float(a) / b if b else np.nan
    return {
        "n_outage": len(o), "n_comms": len(c),
        "outage_recall": f((o.verdict == "OUTAGE").sum(), len(o)),
        "comms_recall": f((c.verdict == "COMMS_FAILURE").sum(), len(c)),
        "precision_outage": f((called_o & (tab.cause == "OUTAGE")).sum(), called_o.sum()),
        "precision_comms": f(((tab.verdict == "COMMS_FAILURE") & (tab.cause == "COMMS_FAILURE")).sum(),
                             (tab.verdict == "COMMS_FAILURE").sum()),
        "false_outage_rate": f((c.verdict == "OUTAGE").sum(), len(c)),
        "missed_outage_rate": f((o.verdict.isin(["COMMS_FAILURE", "MISSED"])).sum(), len(o)),
        "abstention_rate": f((tab.verdict == "UNCERTAIN").sum(), len(tab)),
        "correct_cause_rate": f((tab.verdict == tab.cause).sum(), len(tab)),
        "balanced_correct": np.nanmean([f((o.verdict == "OUTAGE").sum(), len(o)),
                                        f((c.verdict == "COMMS_FAILURE").sum(), len(c))]),
        "accuracy_when_decided": f((tab.verdict == tab.cause)[decided].sum(), decided.sum()),
        "latency_median": float(np.nanmedian(tab.latency_intervals)) if len(tab) else np.nan,
    }


def bootstrap(tab, key, rng, n=1000):
    """95% CI of a metric by resampling episodes (stratified by cause)."""
    vals = []
    parts = [tab[tab.cause == c] for c in ["OUTAGE", "COMMS_FAILURE"]]
    for _ in range(n):
        s = pd.concat([p.iloc[rng.integers(0, len(p), len(p))] for p in parts if len(p)])
        vals.append(rates(s)[key])
    return [float(np.nanquantile(vals, 0.025)), float(np.nanquantile(vals, 0.975))]


def wilson(k, n, z=1.96):
    if n == 0:
        return [np.nan, np.nan]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(c - h), float(c + h)]
