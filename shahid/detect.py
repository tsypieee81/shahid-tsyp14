"""Detector: OUTAGE / COMMS_FAILURE / UNCERTAIN for each silent meter group.

Inputs: ONLY the observed/ and context/ areas of a scenario (test-enforced).
Origin: ORIGINAL. Status: IMPLEMENTED.

Timing. A reading for interval t normally arrives at the end of t. A meter is silent from onset t0
when none of its readings for t0 .. t0+K-1 has arrived by time t0+K. Meters with the same onset form
one silent group. A decision at tau = t0 + K + L uses only data that had arrived by tau.

Evidence over the window [t0, tau):
  R = sum_t [ transformer(t) - sum(known readings) - gap0 - sum(expected of other missing meters) ]
  M = sum_t expected(silent group)           (anchored estimator, CP4)
Under COMMS_FAILURE the silent customers still draw power: R ~ M. Under OUTAGE: R ~ 0.
gap0 is the median gap over the last day's fully reported intervals: the test is on the change of
the gap relative to its recent baseline, not on the absolute gap.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

STEP = pd.Timedelta(minutes=15)
DEFAULTS = {"K": 2, "L_max": 4, "history_days": 14, "gap_days": 1,
            # scoring defaults; CP5 replaces them with values chosen on validation
            "min_expected_kwh": 0.5, "share_threshold": 0.5, "z_crit": 2.576, "t_df": 4,
            "llr_threshold": 0.0, "prior_comms": 0.5, "abstain_band": 0.05}


def load_inputs(scenario_dir):
    d = Path(scenario_dir)
    return {
        "readings": pd.read_parquet(d / "observed" / "meter_readings.parquet"),
        "trafo": pd.read_parquet(d / "observed" / "transformer.parquet"),
        "meters": pd.read_parquet(d / "context" / "meters.parquet"),
        "zones": pd.read_parquet(d / "context" / "zones.parquet"),
    }


def arrays(inputs):
    """Wide arrays: E (T x N kWh, NaN if never arrived), A (arrival as interval index, inf)."""
    trafo = inputs["trafo"]
    index = pd.DatetimeIndex(trafo.interval_start)
    meters = inputs["meters"].meter_id.astype(str).tolist()
    r = inputs["readings"]
    ti = index.get_indexer(r.interval_start)
    mi = pd.Index(meters).get_indexer(r.meter_id.astype(str))
    E = np.full((len(index), len(meters)), np.nan)
    A = np.full((len(index), len(meters)), np.inf)
    E[ti, mi] = r.energy_kwh.to_numpy()
    A[ti, mi] = ((r.arrival_ts - index[0]) / STEP).to_numpy()
    return index, meters, E, A, trafo.energy_kwh.to_numpy()


def silent_groups(A, K):
    """{onset t0: meter indices} where readings t0..t0+K-1 had not arrived by t0+K and t0-1 had."""
    T, N = A.shape
    groups = {}
    for t0 in range(1, T - K):
        late = (A[t0:t0 + K] > t0 + K).all(0)
        prev_ok = A[t0 - 1] <= t0 + K
        hit = np.flatnonzero(late & prev_ok)
        if len(hit):
            groups[t0] = hit
    return groups


def slot_history(X, rows, days):
    """X at the same slot on each of the previous `days` days: (len(rows), days, ...)."""
    h = rows[:, None] - 96 * np.arange(1, days + 1)[None, :]
    h = np.where(h >= 0, h, rows[:, None] % 96)  # clamp (only at the very start of the data)
    return X[h]


def evidence(E, A, T, t0, group, tau, p):
    """Window evidence for one silent group at decision time tau (all from observed data)."""
    H = p["history_days"]
    off = max(0, t0 - 96 * max(H, p["gap_days"]) - 1)  # local slice [off, tau)
    known = A[off:tau] <= tau
    Ek = np.where(known, E[off:tau], np.nan)
    Tl = T[off:tau]
    t0l = t0 - off
    w = np.arange(t0l, tau - off)
    Eh = slot_history(Ek, w, H)  # (W, H, N)
    mean = np.nanmean(Eh, 1)
    sd = np.nanstd(Eh, 1, ddof=1)
    g = np.zeros(E.shape[1], bool)
    g[group] = True
    # anchored expected energy: same-slot mean + decayed deviation of the last pre-onset reading
    prev_mean = np.nanmean(slot_history(Ek, np.array([t0l - 1]), H), 1)[0]
    dev_all = np.nan_to_num(Ek[t0l - 1] - prev_mean)  # 0 where the t0-1 reading is unknown
    lead = np.arange(1, len(w) + 1)

    def per_lead(key):
        v = np.array(p[key])
        return v[np.minimum(lead, len(v)) - 1]

    dev = float(dev_all[g].sum())
    mu_g = np.nansum(mean[:, g], 1) + per_lead("rho_by_lead") * dev
    sd_g = per_lead("sigma_mult_by_lead") * np.sqrt(np.nansum(sd[:, g] ** 2, 1))
    # recent gap baseline (fully reported intervals of the last gap_days before onset)
    g0 = max(0, t0l - 96 * p["gap_days"])
    full = known[g0:t0l].all(1)
    gaps = Tl[g0:t0l][full] - Ek[g0:t0l][full].sum(1)
    gap0 = float(np.median(gaps)) if len(gaps) else p["gap_const"]
    # other missing meters (random loss, delay): single-meter anchored estimate and uncertainty
    other = ~known[w] & ~g[None, :]
    mu1 = np.nan_to_num(mean) + per_lead("rho1_by_lead")[:, None] * dev_all[None, :]
    mu_other = np.where(other, mu1, 0).sum(1)
    sd_other = per_lead("sigma1_mult_by_lead") * np.sqrt(
        np.where(other, np.nan_to_num(sd) ** 2, 0).sum(1))
    r = Tl[w] - np.nansum(Ek[w], 1) - gap0 - mu_other
    n = len(w)
    rg = p["gap_acf1"]
    var_gap = p["gap_sd"] ** 2 * n * (1 + rg) / (1 - rg)  # AR(1) variance of a window sum
    var_other = sd_other.sum() ** 2  # perfectly correlated across the window (conservative)
    return {"R": float(r.sum()), "M": float(mu_g.sum()),
            "sd_O": float(np.sqrt(var_gap + var_other)),
            "sd_C": float(np.sqrt(var_gap + var_other + sd_g.sum() ** 2)),  # correlated errors
            "n_intervals": n, "gap0": gap0, "dev_before_onset": dev}


def score(ev, method, p):
    """Return (verdict, probability of COMMS_FAILURE or None, abstain reason)."""
    R, M, sO, sC = ev["R"], ev["M"], ev["sd_O"], ev["sd_C"]
    if abs(M) < p["min_expected_kwh"]:  # applies to every method
        return "UNCERTAIN", None, "expected energy of silent group too small for the balance"
    if method == "share":  # threshold on the visible share
        sh = R / M
        return ("COMMS_FAILURE" if sh > p["share_threshold"] else "OUTAGE"), None, ""
    if method == "ztest":  # standardised residual under both hypotheses
        zO, zC = abs(R) / sO, abs(R - M) / sC
        okO, okC = zO < p["z_crit"], zC < p["z_crit"]
        if okO and not okC:
            return "OUTAGE", None, ""
        if okC and not okO:
            return "COMMS_FAILURE", None, ""
        return "UNCERTAIN", None, ("both hypotheses fit" if okO else "neither hypothesis fits")
    # likelihood ratio, Student-t noise (residuals are heavy-tailed, CP5)
    nu = p["t_df"]
    llr = stats.t.logpdf(R, nu, loc=M, scale=sC) - stats.t.logpdf(R, nu, loc=0, scale=sO)
    if method == "lr":
        return ("COMMS_FAILURE" if llr > p["llr_threshold"] else "OUTAGE"), None, ""
    # "lr_band" is the honest name of "bayes": with prior 0.5 the posterior is sigmoid(llr), so the
    # rule is a likelihood-ratio test with a two-sided abstention band |llr| < logit(1 - band).
    if method in ("bayes", "lr_band"):  # posterior with an explicit abstention band
        prior = np.log(p["prior_comms"] / (1 - p["prior_comms"]))
        post = float(1 / (1 + np.exp(-np.clip(llr + prior, -50, 50))))
        a = p["abstain_band"]
        if post >= 1 - a:
            return "COMMS_FAILURE", post, ""
        if post <= a:
            return "OUTAGE", post, ""
        return "UNCERTAIN", post, f"posterior {post:.2f} inside abstention band"
    raise ValueError(method)


def evidence_table(inputs, params):
    """Evidence for every silent group at each decision time L = 0..L_max."""
    p = {**DEFAULTS, **params}
    index, meters, E, A, T = arrays(inputs)
    rows = []
    for t0, group in silent_groups(A, p["K"]).items():
        if t0 < 96 * p["history_days"] or t0 + p["K"] + p["L_max"] > len(T):
            continue
        evs = [evidence(E, A, T, t0, group, t0 + p["K"] + L, p) for L in range(p["L_max"] + 1)]
        rows.append({"onset": index[t0], "t0": t0, "n_meters": len(group),
                     "meters": [meters[g] for g in group], "evs": evs})
    return rows


def decide_table(table, method, params, sequential=True):
    """Verdict per group. sequential: first L in 0..L_max that is not UNCERTAIN
    (latency = K + L intervals after onset); otherwise the verdict at L_max."""
    p = {**DEFAULTS, **params}
    out = []
    for g in table:
        evs = g["evs"] if sequential else g["evs"][-1:]
        for L, ev in enumerate(evs):
            verdict, prob, reason = score(ev, method, p)
            if verdict != "UNCERTAIN":
                break
        L = L if sequential else p["L_max"]
        out.append({"onset": g["onset"], "latency_intervals": p["K"] + L,
                    "decided_at": g["onset"] + STEP * (p["K"] + L), "n_meters": g["n_meters"],
                    "meters": g["meters"], **ev,
                    "visible_share": ev["R"] / ev["M"] if ev["M"] else np.nan,
                    "verdict": verdict, "p_comms": prob, "abstain_reason": reason,
                    "method": method})
    return pd.DataFrame(out)


def detect(inputs, params, method="bayes", sequential=True):
    return decide_table(evidence_table(inputs, params), method, params, sequential)


def fit(inputs, train_rows, n_onsets=1500, seed=0, history_days=DEFAULTS["history_days"]):
    """Fit detector parameters on FAULT-FREE observed data, training rows only.

    Returns gap noise (sd and lag-1 autocorrelation of gap minus its last-day median), and for the
    anchored expected-load estimator the persistence rho and sigma multiplier per lead. Groups used
    for fitting are the electrical zones (context), the same sets outages produce.
    """
    rng = np.random.default_rng(seed)
    index, meters, E, A, T = arrays(inputs)
    p = dict(DEFAULTS, history_days=history_days)
    H, Lw = p["history_days"], p["K"] + p["L_max"]
    full = np.isfinite(E).all(1)
    gap = np.where(full, T - np.nansum(E, 1), np.nan)
    # gap change relative to its last-day median
    rows = train_rows[train_rows >= 96 * H]
    day_med = pd.Series(gap).rolling(96, min_periods=10).median().shift(1).to_numpy()
    d = (gap - day_med)[rows]
    d = d[np.isfinite(d)]
    dd = (gap - day_med)
    m = np.isfinite(dd[1:]) & np.isfinite(dd[:-1])
    m[: rows.min()] = False
    p["gap_const"] = float(np.nanmedian(gap[rows]))
    p["gap_sd"] = float(1.4826 * np.median(np.abs(d - np.median(d))))
    p["gap_acf1"] = float(np.corrcoef(dd[1:][m], dd[:-1][m])[0, 1])
    # anchored estimator per lead, zone groups
    zones = inputs["zones"].groupby("zone_id").meter_id.apply(list)
    mi = {m_: i for i, m_ in enumerate(meters)}
    G = np.zeros((len(zones), len(meters)))
    for k, ms in enumerate(zones):
        G[k, [mi[x] for x in ms]] = 1
    t0s = rng.choice(rows[rows < len(T) - Lw], n_onsets, replace=False)
    for suffix, Gm in [("", G), ("1", np.eye(len(meters)))]:
        devs, outs, sds = [], [], []
        for t0 in t0s:
            w = np.arange(t0 - 1, t0 + Lw)
            Eh = slot_history(E, w, H)
            mean, sd = np.nanmean(Eh, 1), np.nanstd(Eh, 1, ddof=1)
            dev = (E[w] - mean) @ Gm.T  # NaN where a member is missing
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
