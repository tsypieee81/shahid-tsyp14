"""Observation layer: what a utility head-end would receive from the simulated truth.

Origin: ORIGINAL. Status: SIMULATED. Every parameter is an ASSUMPTION (see docs/ASSUMPTIONS.md,
A-METERERR, A-TMETERERR, A-COMMS); no metering standard is cited.
"""
import numpy as np
import pandas as pd

STEP = pd.Timedelta(minutes=15)
CAUSES = ["NORMAL", "RANDOM_LOSS", "DELAYED", "COMMS_FAILURE", "OUTAGE"]
NORMAL, RANDOM_LOSS, DELAYED, COMMS, OUTAGE = range(5)


def quant(x, q):
    return np.round(x / q) * q if q else x


def meter_readings(e_true, rng, m):
    """Per-meter gain error (fixed), noise (relative + absolute), register quantisation."""
    T, N = e_true.shape
    gain = 1 + rng.normal(0, m["gain_sd"], N)
    sd = np.sqrt((m["noise_rel_sd"] * e_true) ** 2 + m["noise_abs_kwh"] ** 2)
    return quant(gain * e_true + rng.normal(0, 1, (T, N)) * sd, m["quant_kwh"])


def trafo_reading(t_true, rng, tm):
    gain = 1 + rng.normal(0, tm["gain_sd"])
    sd = np.sqrt((tm["noise_rel_sd"] * t_true) ** 2 + tm.get("noise_abs_kwh", 0) ** 2)
    return quant(gain * t_true + rng.normal(0, 1, len(t_true)) * sd, tm["quant_kwh"])


def delivery(no_supply, comm_events, rng, c):
    """Arrival lag (intervals after interval end; -1 = never arrives) and cause code per cell.

    no_supply: T x N bool, customer has no power (outage). Such a meter cannot measure or send.
    comm_events: list of (a, b, meters): concentrator/link down for rows [a, b).
    """
    T, N = no_supply.shape
    lag = np.zeros((T, N), int)
    cause = np.zeros((T, N), int)
    d = rng.random((T, N)) < c["p_delay"]
    lag[d] = rng.geometric(1 / c["delay_mean_intervals"], d.sum())
    cause[d] = DELAYED
    lost = rng.random((T, N)) < c["p_missing"]
    lag[lost] = -1
    cause[lost] = RANDOM_LOSS
    for a, b, meters in comm_events:
        for t in range(a, b):
            if c["backlog"]:  # stored in the meter, delivered after the link returns
                lag[t, meters] = (b - t) + rng.integers(0, c["backlog_spread"] + 1, len(meters))
            else:
                lag[t, meters] = -1
            cause[t, meters] = COMMS
    lag[no_supply] = -1
    cause[no_supply] = OUTAGE
    if c.get("outage_backfill"):
        # optional, default off: after restoration the meter uploads zero-energy intervals
        for n in range(N):
            off = np.flatnonzero(no_supply[:, n])
            for t in off:
                nxt = np.flatnonzero(~no_supply[t:, n])
                if len(nxt):
                    lag[t, n] = nxt[0] + 1
    return lag, cause


def coarsen(e_true, t_true, vm, no_supply, comm_events, f):
    """Reporting interval option (protocol 02; ported unchanged from branch cadence-study, commit 6853c6e):
    f consecutive 15-min rows form one reading. Energy is SUMMED (kWh). Each reading is one transmission
    at the interval end:
    - no supply at transmission (last sub-row) -> never sent; earlier restoration -> partial energy;
    - a link failure delays the reading iff its transmission falls inside the failure, i.e. the
      last sub-row (i+1)f-1 lies in [a, b) -> coarse rows [ceil((a+1)/f)-1, floor(b/f)).
    Voltage is the value of the last sub-row (an instantaneous quantity, not summed)."""
    T, N = e_true.shape
    assert T % f == 0, "series length must be a multiple of the aggregation factor"
    e_c = e_true.reshape(T // f, f, N).sum(1)
    t_c = t_true.reshape(T // f, f).sum(1)
    vm_c = vm[f - 1::f]
    ns_c = no_supply[f - 1::f]
    comm_c = []
    for a, b, meters in comm_events:
        ca, cb = -(-(a + 1) // f) - 1, b // f
        if cb > ca:
            comm_c.append((ca, cb, meters))
    return e_c, t_c, vm_c, ns_c, comm_c


def to_long(index, e_obs, v_obs, lag, meter_ids, no_supply, step=STEP):
    t_i, m_i = np.nonzero(lag >= 0)
    e = e_obs[t_i, m_i].copy()
    e[no_supply[t_i, m_i]] = 0.0  # backfilled outage interval: register did not advance
    df = pd.DataFrame({
        "meter_id": pd.Categorical.from_codes(m_i, meter_ids),
        "interval_start": index[t_i],
        "energy_kwh": e,
        "arrival_ts": index[t_i] + step * (1 + lag[t_i, m_i]),
    })
    if v_obs is not None:
        v = v_obs[t_i, m_i].copy()
        v[no_supply[t_i, m_i]] = np.nan
        df["voltage_v"] = v
    return df


def last_gasps(index, no_supply, rng, c, meter_ids):
    """Optional power-fail messages at outage onset (default off; headline results never use)."""
    if not c.get("last_gasp"):
        return pd.DataFrame(columns=["meter_id", "ts", "type"])
    onset = no_supply & ~np.vstack([np.zeros((1, no_supply.shape[1]), bool), no_supply[:-1]])
    t_i, m_i = np.nonzero(onset)
    keep = rng.random(len(t_i)) < c.get("p_last_gasp", 1.0)
    return pd.DataFrame({"meter_id": [meter_ids[m] for m in m_i[keep]],
                         "ts": index[t_i[keep]], "type": "last_gasp"})
