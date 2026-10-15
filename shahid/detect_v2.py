"""Protocol 02: evidence accounting version 2, a SEPARATE registered method (shahid/detect.py, version 1,
is frozen and untouched).

Interval-general: the reporting step is read from the data. Four registered changes, each a switch, so
that "version 1 at any interval" is a configuration of this module (RULES_V1; at 15 minutes it equals
shahid.detect exactly, checked by a test):
  stored          at decision time, if at least half of the group's onset readings have arrived late,
                  the verdict is COMMS_FAILURE ("stored readings delivered"), no posterior (A-COMMS)
  own_excluded    the silent group's own readings that arrive during the window stay out of the
                  visible sum (their energy is counted once, in M)
  onset_excluded  the onset interval (possibly partial) is left out of R and M
  minutes         silence 30 min and decision window 60 min, converted to readings at the data's step
Scoring is version 1's Student-t likelihood ratio with an abstention band (shahid.detect.score, bayes).
"""
import math

import numpy as np
import pandas as pd

from shahid import detect

RULES_V1 = {"stored": False, "own_excluded": False, "onset_excluded": False, "minutes": False, "K": 2, "L_max": 4}
RULES_V2 = {"stored": True, "own_excluded": True, "onset_excluded": True, "minutes": True,
            "silence_min": 30, "window_min": 60}
STORED_SHARE = 0.5


def step_min(inputs):
    idx = pd.DatetimeIndex(inputs["trafo"].interval_start)
    return (idx[1] - idx[0]) / pd.Timedelta(minutes=1) if len(idx) > 1 else 15.0


def windows(rules, smin):
    """(K, L_max) in readings at a step of smin minutes."""
    if rules.get("minutes"):
        return math.ceil(rules["silence_min"] / smin), math.ceil(rules["window_min"] / smin)
    return rules["K"], rules["L_max"]


def arrays(inputs):
    """As detect.arrays, with interval units at the data's own step."""
    trafo = inputs["trafo"]
    index = pd.DatetimeIndex(trafo.interval_start)
    step = pd.Timedelta(minutes=step_min(inputs))
    meters = inputs["meters"].meter_id.astype(str).tolist()
    r = inputs["readings"]
    ti = index.get_indexer(r.interval_start)
    mi = pd.Index(meters).get_indexer(r.meter_id.astype(str))
    E = np.full((len(index), len(meters)), np.nan)
    A = np.full((len(index), len(meters)), np.inf)
    E[ti, mi] = r.energy_kwh.to_numpy()
    A[ti, mi] = ((r.arrival_ts - index[0]) / step).to_numpy()
    return index, meters, E, A, trafo.energy_kwh.to_numpy()


def slot_history(X, rows, days, spd):
    h = rows[:, None] - spd * np.arange(1, days + 1)[None, :]
    h = np.where(h >= 0, h, rows[:, None] % spd)
    return X[h]


def evidence(E, A, T, t0, group, tau, p, rules, spd):
    """Window evidence at decision time tau, version 1 algebra with the registered switches.
    Returns None when the window is empty (onset excluded and no later interval yet)."""
    H = p["history_days"]
    off = max(0, t0 - spd * max(H, p["gap_days"]) - 1)
    known = A[off:tau] <= tau
    t0l = t0 - off
    start = t0l + (1 if rules.get("onset_excluded") else 0)
    w = np.arange(start, tau - off)
    if not len(w):
        return None
    g = np.zeros(E.shape[1], bool)
    g[group] = True
    if rules.get("own_excluded"):  # the group's late readings stay out of the visible sum
        known[t0l:, g] = False
    Ek = np.where(known, E[off:tau], np.nan)
    Tl = T[off:tau]
    Eh = slot_history(Ek, w, H, spd)
    mean = np.nanmean(Eh, 1)
    sd = np.nanstd(Eh, 1, ddof=1)
    prev_mean = np.nanmean(slot_history(Ek, np.array([t0l - 1]), H, spd), 1)[0]
    dev_all = np.nan_to_num(Ek[t0l - 1] - prev_mean)
    lead = w - t0l + 1  # positions counted from the onset, as in version 1

    def per_lead(key):
        v = np.array(p[key])
        return v[np.minimum(lead, len(v)) - 1]

    dev = float(dev_all[g].sum())
    mu_g = np.nansum(mean[:, g], 1) + per_lead("rho_by_lead") * dev
    sd_g = per_lead("sigma_mult_by_lead") * np.sqrt(np.nansum(sd[:, g] ** 2, 1))
    g0 = max(0, t0l - spd * p["gap_days"])
    full = known[g0:t0l].all(1)
    gaps = Tl[g0:t0l][full] - Ek[g0:t0l][full].sum(1)
    gap0 = float(np.median(gaps)) if len(gaps) else p["gap_const"]
    other = ~known[w] & ~g[None, :]
    mu1 = np.nan_to_num(mean) + per_lead("rho1_by_lead")[:, None] * dev_all[None, :]
    mu_other = np.where(other, mu1, 0).sum(1)
    sd_other = per_lead("sigma1_mult_by_lead") * np.sqrt(np.where(other, np.nan_to_num(sd) ** 2, 0).sum(1))
    r = Tl[w] - np.nansum(Ek[w], 1) - gap0 - mu_other
    n = len(w)
    rg = p["gap_acf1"]
    var_gap = p["gap_sd"] ** 2 * n * (1 + rg) / (1 - rg)
    var_other = sd_other.sum() ** 2
    return {"R": float(r.sum()), "M": float(mu_g.sum()), "sd_O": float(np.sqrt(var_gap + var_other)),
            "sd_C": float(np.sqrt(var_gap + var_other + sd_g.sum() ** 2)), "n_intervals": n, "gap0": gap0}


def evidence_table(inputs, params, rules):
    """Every silent group with evidence and stored-reading share at each lead."""
    p = {**detect.DEFAULTS, **params}
    smin = step_min(inputs)
    spd = int(round(1440 / smin))
    K, Lm = windows(rules, smin)
    index, meters, E, A, T = arrays(inputs)
    rows = []
    for t0, group in detect.silent_groups(A, K).items():
        if t0 < spd * p["history_days"] or t0 + K + Lm > len(T):
            continue
        taus = [t0 + K + L for L in range(Lm + 1)]
        rows.append({"onset": index[t0], "t0": t0, "n_meters": len(group), "meters": [meters[i] for i in group],
                     "evs": [evidence(E, A, T, t0, group, tau, p, rules, spd) for tau in taus],
                     "stored": [float(np.mean(A[t0, group] <= tau)) for tau in taus],
                     "K": K, "step_min": smin})
    return rows


def decide_table(table, params, rules, band):
    """Sequential decision over leads; the stored-reading rule is checked first when switched on."""
    p = {**detect.DEFAULTS, **params, "abstain_band": band}
    out = []
    for g in table:
        verdict, prob, reason, L = "UNCERTAIN", None, "", len(g["evs"]) - 1
        for L, ev in enumerate(g["evs"]):
            if rules.get("stored") and g["stored"][L] >= STORED_SHARE:
                verdict, prob, reason = "COMMS_FAILURE", None, "stored readings delivered"
                break
            if ev is None:
                continue
            verdict, prob, reason = detect.score(ev, "bayes", p)
            if verdict != "UNCERTAIN":
                break
        out.append({"onset": g["onset"], "n_meters": g["n_meters"], "meters": g["meters"], "verdict": verdict,
                    "p_comms": prob, "reason": reason, "lead": L, "latency_intervals": g["K"] + L,
                    "decision_delay_min": (g["K"] + L) * g["step_min"]})
    return pd.DataFrame(out)


def fit(inputs, train_rows, rules, n_onsets=1500, seed=0, history_days=detect.DEFAULTS["history_days"]):
    """detect.fit at the data's step (ported from branch cadence-study 6853c6e): unlabelled fault-free rows."""
    rng = np.random.default_rng(seed)
    index, meters, E, A, T = arrays(inputs)
    smin = step_min(inputs)
    spd = int(round(1440 / smin))
    K, Lm = windows(rules, smin)
    p = dict(detect.DEFAULTS, history_days=history_days, K=K, L_max=Lm)
    H, Lw = p["history_days"], K + Lm
    full = np.isfinite(E).all(1)
    gap = np.where(full, T - np.nansum(E, 1), np.nan)
    rows = train_rows[train_rows >= spd * H]
    day_med = pd.Series(gap).rolling(spd, min_periods=min(10, spd)).median().shift(1).to_numpy()
    d = (gap - day_med)[rows]
    d = d[np.isfinite(d)]
    dd = gap - day_med
    m = np.isfinite(dd[1:]) & np.isfinite(dd[:-1])
    m[: rows.min()] = False
    p["gap_const"] = float(np.nanmedian(gap[rows]))
    p["gap_sd"] = float(1.4826 * np.median(np.abs(d - np.median(d))))
    p["gap_acf1"] = float(np.corrcoef(dd[1:][m], dd[:-1][m])[0, 1])
    zones = inputs["zones"].groupby("zone_id").meter_id.apply(list)
    mi = {m_: i for i, m_ in enumerate(meters)}
    G = np.zeros((len(zones), len(meters)))
    for k, ms in enumerate(zones):
        G[k, [mi[x] for x in ms]] = 1
    t0s = rng.choice(rows[rows < len(T) - Lw], min(n_onsets, len(rows[rows < len(T) - Lw])), replace=False)
    for suffix, Gm in [("", G), ("1", np.eye(len(meters)))]:
        devs, outs, sds = [], [], []
        for t0 in t0s:
            w = np.arange(t0 - 1, t0 + Lw)
            Eh = slot_history(E, w, H, spd)
            mean, sd = np.nanmean(Eh, 1), np.nanstd(Eh, 1, ddof=1)
            dev = (E[w] - mean) @ Gm.T
            devs.append(dev[0])
            outs.append(dev[1:])
            sds.append(np.sqrt((sd[1:] ** 2) @ Gm.T))
        dev0, devL, sdL = np.array(devs), np.array(outs), np.array(sds)
        rho, mult = [], []
        for ell in range(Lw):
            y, x = devL[:, ell], dev0
            ok = np.isfinite(x) & np.isfinite(y)
            r_ = float(np.sum(x[ok] * y[ok]) / np.sum(x[ok] ** 2))
            z = (y[ok] - r_ * x[ok]) / sdL[:, ell][ok]
            rho.append(r_)
            mult.append(float(np.quantile(np.abs(z[np.isfinite(z)]), 0.6827)))
        p[f"rho{suffix}_by_lead"], p[f"sigma{suffix}_mult_by_lead"] = rho, mult
    return p
