"""Phase 2 studies: decisions on cached evidence and their evaluation (protocols 01, 03, 04, 05).

A posterior function maps (cached group rows, lead L) -> P(comms) per row; the decision is version 1's
sequential rule over leads 0..L_max with abstention band b. Evaluation uses the truth and matched-episode
columns of the cache (evaluation side) and the metrics of docs/eval_protocol.md.
"""
import numpy as np
import pandas as pd
from scipy import stats

from shahid import evaluate

K, L_MAX, NU = 2, 4, 4
GATE_N, GATE_T = 3, 1  # CP12 / addendum C gate, not re-chosen
SIZE_BINS = [(1, 1), (2, 2), (3, 5), (6, 20), (21, 10 ** 6)]


def llr(g, L):
    """Frozen version 1 Student-t log likelihood ratio at lead L (shahid.detect.score)."""
    R, M, sO, sC = (g[f"{c}{L}"].to_numpy() for c in ("R", "M", "sd_O", "sd_C"))
    return stats.t.logpdf(R, NU, loc=M, scale=sC) - stats.t.logpdf(R, NU, loc=0, scale=sO)


def sigmoid(x):
    return 1 / (1 + np.exp(-np.clip(x, -50, 50)))


def v1_posterior(g, L, prior=0.5):
    return sigmoid(llr(g, L) + np.log(prior / (1 - prior)))


def decide(g, post_fn, band):
    """Sequential decision: first lead whose posterior leaves the band; else UNCERTAIN at L_max."""
    n = len(g)
    verdict = np.full(n, "UNCERTAIN", dtype=object)
    lead = np.full(n, L_MAX)
    post = np.full(n, np.nan)
    open_ = np.ones(n, bool)
    for L in range(L_MAX + 1):
        p = post_fn(g, L)
        post[open_] = p[open_]
        c = open_ & (p >= 1 - band)
        o = open_ & (p <= band)
        verdict[c], verdict[o] = "COMMS_FAILURE", "OUTAGE"
        lead[c | o] = L
        open_ &= ~(c | o)
    return pd.DataFrame({"verdict": verdict, "lead": lead, "p_comms": post}, index=g.index)


def size_bin(n):
    return np.select([(n >= a) & (n <= b) for a, b in SIZE_BINS], range(len(SIZE_BINS)), -1)


def episode_tab(item, g, d, weeks):
    """Labelled episodes of the given weeks with the verdict of their matched group (or MISSED)."""
    ep = item["episodes"]
    if ep is None or not len(ep):
        return pd.DataFrame(columns=["cause", "verdict", "latency_intervals", "p_comms", "selector", "n_meters"])
    ep = ep[ep.week.isin(weeks)]
    m = g[g.matched_episode >= 0]
    pos = dict(zip(m.matched_episode.astype(int), m.index))
    rows = []
    for e in ep.itertuples():
        i = pos.get(int(e.episode_id))
        rows.append({"cause": e.cause, "selector": e.selector, "n_meters": e.n_meters, "start": e.start, "end": e.end,
                     "episode_id": e.episode_id, "group": i,
                     "verdict": d.at[i, "verdict"] if i is not None else "MISSED",
                     "latency_intervals": K + d.at[i, "lead"] if i is not None else np.nan,
                     "p_comms": d.at[i, "p_comms"] if i is not None else np.nan})
    return pd.DataFrame(rows)


def fault_free(items_ff, decided, weeks):
    """Outage verdicts on fault-free data of the given weeks: per meter-day and per transformer-year."""
    k, days, md = 0, 0.0, 0.0
    for item, d in zip(items_ff, decided):
        g = item["groups"]
        k += int(((d.verdict == "OUTAGE") & g.week.isin(weeks).to_numpy()).sum())
        dd = np.isin(item["row_weeks"], weeks).sum() / 96
        days += dd
        md += dd * item["n_meters"]
    return {"k": k, "meter_days": md, "per_meter_day": k / md if md else np.nan,
            "per_meter_day_ci95": evaluate.wilson(k, md) if md else [np.nan, np.nan],
            "per_transformer_year": k / days * 365 if days else np.nan, "days": days}


def summarise(tab, rng=None, boot=1000):
    r = evaluate.rates(tab) if len(tab) else {}
    if rng is not None and len(tab):
        r["ci95"] = {k: evaluate.bootstrap(tab, k, rng, boot) for k in
                     ["missed_outage_rate", "false_outage_rate", "abstention_rate", "outage_recall", "comms_recall"]}
    return r


def feasible(r, ff, lim=(0.05, 0.05, 0.001)):
    return (np.nan_to_num(r["missed_outage_rate"], nan=1) <= lim[0]
            and np.nan_to_num(r["false_outage_rate"], nan=1) <= lim[1]
            and np.nan_to_num(ff["per_meter_day"], nan=1) <= lim[2])


def policy(g, d, gate, escalate):
    """CP12 policy outcomes per group (version 1 escalation table, optional meter-count gate).
    escalate: a gated group whose meters resume without the onset reading goes to a human (protocol 01)
    instead of being closed with no verdict. Returns outcome and human time (interval units)."""
    tau = (g.t0 + K + d.lead).to_numpy()
    out = np.full(len(g), "", dtype=object)
    ht = np.full(len(g), np.nan)
    gated = (g.n_meters.to_numpy() < GATE_N) if gate else np.zeros(len(g), bool)
    Tw = GATE_T * 4
    fill = g.t_fill.to_numpy() <= tau + Tw
    silent = g.t_resume.to_numpy() > tau + Tw

    def put(mask, name, t=None):
        out[mask] = name
        if t is not None:
            ht[mask] = t[mask]
    put(gated & fill, "watch_resolved_comms")
    put(gated & ~fill & silent, "watch_timeout", tau + Tw)
    put(gated & ~fill & ~silent, "watch_escalated" if escalate else "watch_closed_no_verdict",
        (tau + Tw) if escalate else None)
    v = d.verdict.to_numpy()
    ng = ~gated
    put(ng & (v == "OUTAGE"), "outage_verdict", tau)
    put(ng & (v == "UNCERTAIN"), "uncertain", tau)
    c = ng & (v == "COMMS_FAILURE")
    r3 = (np.nan_to_num(d.p_comms.to_numpy()) >= 0.95) & (g.n_meters.to_numpy() <= 40)
    put(c & r3, "comms_auto_closed")
    put(c & ~r3, "comms_review", tau)
    return out, ht


HUMAN = {"watch_timeout", "watch_escalated", "outage_verdict", "uncertain", "comms_review"}
