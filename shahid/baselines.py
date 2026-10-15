"""Baseline detectors. Same inputs as shahid.detect (observed + context only). Origin: ORIGINAL.

count      silent set covers >= 90% of the smallest electrical zone containing it -> OUTAGE
structure  silent set matches a concentrator group -> COMMS; matches a zone -> OUTAGE;
           both (aligned concentrators) -> UNCERTAIN; neither -> COMMS
step       transformer drop at onset >= half the group's expected energy -> OUTAGE
naive      visible share with the same-slot median and a 0.5 threshold (the CP2 detector)
"""
import numpy as np
import pandas as pd

from shahid.detect import STEP, arrays, silent_groups, slot_history


def zone_sets(inputs):
    return [set(v) for v in inputs["zones"].groupby("zone_id").meter_id.apply(list)]


def smallest_zone(silent, zones):
    cands = [z for z in zones if silent <= z]
    return min(cands, key=len) if cands else None


def detect(inputs, method, K=2, L=2, history_days=14, cover=0.9):
    index, meters, E, A, T = arrays(inputs)
    zones = zone_sets(inputs)
    conc = inputs["meters"].groupby("concentrator_id").meter_id.apply(lambda s: set(s.astype(str)))
    out = []
    for t0, group in silent_groups(A, K).items():
        if t0 < 96 * history_days or t0 + K + L > len(T):
            continue
        tau = t0 + K + L
        S = {meters[g] for g in group}
        z = smallest_zone(S, zones)
        fills_zone = z is not None and len(S) >= cover * len(z)
        is_conc = any(len(S & c) / len(S | c) >= cover for c in conc)
        reason = ""
        if method == "count":
            verdict = "OUTAGE" if fills_zone else "COMMS_FAILURE"
        elif method == "structure":
            if is_conc and fills_zone:
                verdict, reason = "UNCERTAIN", "silent set is both a concentrator group and a zone"
            else:
                verdict = "OUTAGE" if fills_zone else "COMMS_FAILURE"
        elif method in ("step", "naive"):
            off = max(0, t0 - 96 * history_days - 1)
            known = A[off:tau] <= tau
            Ek = np.where(known, E[off:tau], np.nan)
            Tl = T[off:tau]
            t0l = t0 - off
            w = np.arange(t0l, tau - off)
            mu_all = np.nanmedian(slot_history(Ek, w, history_days), 1)
            mu = mu_all[:, group].sum(1)
            if method == "step":
                drop = np.mean(Tl[t0l - 2:t0l]) - Tl[t0l]
                verdict = "OUTAGE" if drop >= 0.5 * mu[0] and mu[0] > 0 else "COMMS_FAILURE"
            else:
                full = known[t0l - 96:t0l].all(1)
                gaps = (Tl[t0l - 96:t0l] - np.nansum(Ek[t0l - 96:t0l], 1))[full]
                gap0 = np.median(gaps) if full.any() else 0.0
                other = ~known[w]
                other[:, group] = False
                r = Tl[w] - np.nansum(Ek[w], 1) - gap0 - np.where(other, np.nan_to_num(mu_all), 0).sum(1)
                if abs(mu.sum()) < 0.5:
                    verdict, reason = "UNCERTAIN", "expected energy of silent group too small"
                else:
                    verdict = "COMMS_FAILURE" if r.sum() / mu.sum() > 0.5 else "OUTAGE"
        else:
            raise ValueError(method)
        out.append({"onset": index[t0], "decided_at": index[0] + STEP * tau,
                    "latency_intervals": tau - t0, "n_meters": len(group),
                    "meters": sorted(S), "verdict": verdict, "abstain_reason": reason,
                    "method": method})
    return pd.DataFrame(out)
