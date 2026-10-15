"""Audit: does each scenario change what it claims to change? Plus one conservation example.

Each event is simulated against an identical no-event scenario (same world, same seed). For the
event window we check whether the physical state, the true meter energy, the true transformer
energy and the observations differ, and whether any detector input column carries a label.
Run: python -m shahid.audit_faults   (writes results/audit_faults.json)
"""
import json

import numpy as np
import pandas as pd

from shahid import scenario
from shahid.cp5_compare import inputs_of
from shahid.cp8_single_meter import inject
from shahid.grid import DT_H
from shahid.stamp import stamp, write_json

W = {"start_day": 100, "days": 16}
A, DUR = 15 * 96 + 40, 8  # event window rows [A, A+DUR), day 15 10:00


def sim(events, world=None):
    cfg = scenario.merge(scenario.load_cfg("configs/smoke.yaml"),
                         {"world": {**W, **(world or {})}, "events": events})
    return scenario.simulate(cfg)


def compare(base, s, meters):
    w = slice(A, A + DUR)
    pf_b, pf_s = base["truth"]["powerflow"], s["truth"]["powerflow"]
    phys = not np.allclose(np.nan_to_num(pf_b["load_p"][w]), np.nan_to_num(pf_s["load_p"][w])) or \
        not np.array_equal(np.isnan(pf_b["vm_load"][w]), np.isnan(pf_s["vm_load"][w]))
    eb = base["truth"]["meter_energy_true"].iloc[w, meters].to_numpy()
    es = s["truth"]["meter_energy_true"].iloc[w, meters].to_numpy()
    tb, ts = base["truth"]["trafo_true_kwh"][w], s["truth"]["trafo_true_kwh"][w]
    rb, rs = (x["observed"]["meter_readings"] for x in (base, s))
    key = lambda r: set(zip(r.meter_id.astype(str), r.interval_start, r.arrival_ts))
    obs = key(rb) != key(rs) or not np.allclose(base["observed"]["transformer"].energy_kwh,
                                                s["observed"]["transformer"].energy_kwh)
    label_cols = {c for df in s["labels"].values() for c in df.columns} - {"interval_start",
                                                                           "meter_id"}
    seen = {c for df in inputs_of(s).values() for c in map(str, df.columns)}
    return {"physical_state_changes": bool(phys),
            "meter_truth_changes": bool(not np.allclose(eb, es)),
            "transformer_truth_changes": bool(not np.allclose(tb, ts)),
            "observations_change": bool(obs),
            "detector_sees_label_columns": sorted(seen & label_cols),
            "meter_truth_kwh_window_base_vs_event": [round(float(eb.sum()), 3), round(float(es.sum()), 3)],
            "transformer_truth_kwh_window_base_vs_event": [round(float(tb.sum()), 3), round(float(ts.sum()), 3)]}


def main():
    base = sim([])
    ev = lambda t, **k: [{"type": t, "start_step": A, "duration_steps": DUR, **k}]
    out = {"stamp": stamp({"world": W, "window": [A, DUR]}, "python -m shahid.audit_faults"),
           "scenarios": {}}
    from shahid.world import grid_meta
    meta = grid_meta(scenario.load_cfg("configs/smoke.yaml")["world"]["grid"])
    feeder = meta["feeders"][1]
    zone = sorted(meta["zones"][feeder])
    conc = scenario.concentrator_map(meta, "aligned", 0)
    conc0 = np.flatnonzero(conc == 0).tolist()
    cases = {
        "physical_outage (feeder line opened)": (ev("outage", feeder=1), zone, None),
        "comms_failure (zone)": (ev("comms_failure", zone=int(feeder)), zone, None),
        "concentrator_failure": (ev("comms_failure", concentrator=0), conc0, None),
        "real_load_change (x2, no comms fault)": (ev("load_change", zone=int(feeder), factor=2.0), zone, None),
        "unmetered_energy (load-shaped 5 kW)": ([], zone, {"unmetered": {"kind": "profile", "kw": 5.0}}),
    }
    for name, (events, meters, world) in cases.items():
        out["scenarios"][name] = compare(base, sim(events, world), meters)
    # stuck meter: CP8 injects into OBSERVED readings only; truth and transformer untouched
    E = np.full((len(base["observed"]["transformer"]), len(conc)), np.nan)
    r = base["observed"]["meter_readings"]
    idx = pd.DatetimeIndex(base["observed"]["transformer"].interval_start)
    E[idx.get_indexer(r.interval_start), r.meter_id.cat.codes.to_numpy()] = r.energy_kwh
    X = inject(E, 5, A, A + DUR, "stuck", None, np.random.default_rng(0))
    out["scenarios"]["stuck_meter (CP8, observed readings only)"] = {
        "physical_state_changes": False, "meter_truth_changes": False,
        "transformer_truth_changes": False,
        "observations_change": bool(not np.allclose(np.nan_to_num(E[A:A + DUR, 5]),
                                                    np.nan_to_num(X[A:A + DUR, 5]))),
        "true_load_varies_in_window": bool(np.ptp(base["truth"]["meter_energy_true"].iloc[A:A + DUR, 5]) > 0),
        "observed_frozen_in_window": bool(np.ptp(X[A:A + DUR, 5]) == 0),
        "note": "inject() edits a copy of the observed array; truth arrays are never passed to it"}

    # conservation example, one interval of the no-event scenario
    t = A
    pf = base["truth"]["powerflow"]
    kwh = lambda mw: float(mw * 1000 * DT_H)
    load, pv = kwh(pf["load_p"][t].sum()), kwh(pf["sgen_p"][t].sum())
    lines, tr_loss = kwh(pf["line_pl"][t, 0]), kwh(pf["trafo_pl"][t, 0])
    lv = kwh(-pf["trafo_p_lv"][t, 0])
    obs_t = float(base["observed"]["transformer"].energy_kwh.iloc[t])
    obs_m = float(r[r.interval_start == idx[t]].energy_kwh.sum())
    out["conservation_example"] = {
        "interval": str(idx[t]),
        "customer_load_kwh": load, "pv_generation_kwh": pv, "line_losses_kwh": lines,
        "transformer_lv_delivered_kwh_truth": lv,
        "check_load_minus_pv_plus_losses_kwh": load - pv + lines,
        "residual_kwh": lv - (load - pv + lines),
        "transformer_losses_kwh_outside_lv_meter": tr_loss,
        "transformer_hv_side_kwh (= LV delivered + transformer losses)": lv + tr_loss,
        "observed_transformer_kwh": obs_t,
        "observed_sum_of_reported_meters_kwh": obs_m,
        "n_meters_reported_this_interval": int((r.interval_start == idx[t]).sum()),
        "observed_gap_kwh": obs_t - obs_m}
    write_json("results/audit_faults.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "stamp"}, indent=1, default=str))


if __name__ == "__main__":
    main()
