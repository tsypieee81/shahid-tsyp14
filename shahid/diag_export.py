"""Tooling (post-hoc diagnostic, SIMULATED): net-exporting silent groups in the demo replays.

Run: python -m shahid.diag_export

Decomposes the window evidence of two replayed groups at their deciding lead (lead 0):
  feeder_outage 10:00   the confidently wrong communication-failure verdict
  showcase 09:45        the communication failure with negative expected energy (midday export)
R = T - visible meters - gap baseline - expected other-missing (shahid.detect.evidence). The simulated
true energy of each meter is read to explain R; this is an evaluation-side diagnostic (like
shahid.demo_eval), never an input to the detector or the operator views.
Writes results/diagnostics/export_groups.json.
"""
from pathlib import Path

import numpy as np

from shahid import detect, scenario
from shahid.cp5_compare import inputs_of
from shahid.demo_day import frozen_params, scenario_cfg
from shahid.stamp import stamp, write_json

CASES = [("feeder_outage", 10.0), ("showcase", 9.75)]
OUT = Path("results/diagnostics/export_groups.json")


def decompose(name, hour):
    cfg, _, d0 = scenario_cfg(name)
    sim = scenario.simulate(cfg)
    p = {**detect.DEFAULTS, **frozen_params()}
    index, meters, E, A, T = detect.arrays(inputs_of(sim))
    t0 = d0 + round(hour * 4)
    grp = detect.silent_groups(A, p["K"])[t0]
    tau = t0 + p["K"]
    ev = detect.evidence(E, A, T, t0, grp, tau, p)
    post = detect.score(ev, "bayes", p)[1]
    w = np.arange(t0, tau)
    known = A[w] <= tau
    g = np.zeros(len(meters), bool)
    g[grp] = True
    true_e = sim["truth"]["meter_energy_true"].to_numpy()[w]
    pv = sim["context"]["meters"].pv_kw.to_numpy()
    powered = [{"meter": meters[i], "true_kwh": float(true_e[:, i].sum())} for i in grp if abs(true_e[:, i].sum()) > 0.05]
    return {"scenario": name, "onset": str(index[t0]), "n_meters": int(len(grp)), "lead": 0,
            "R": ev["R"], "M": ev["M"], "sd_O": ev["sd_O"], "sd_C": ev["sd_C"], "posterior_comms": post,
            "z_outage": ev["R"] / ev["sd_O"], "z_comms": (ev["R"] - ev["M"]) / ev["sd_C"],
            "transformer_kwh": float(T[w].sum()), "visible_meters_kwh": float(np.where(known, E[w], 0).sum()),
            "pv_meters_in_group": int((pv[grp] > 0).sum()), "pv_kw_in_group": float(pv[grp].sum()),
            "true_group_kwh": float(true_e[:, g].sum()), "group_meters_with_true_energy": powered,
            "stamp": stamp(cfg, f"python -m shahid.diag_export ({name})")}


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cases = [decompose(n, h) for n, h in CASES]
    write_json(OUT, {"note": "post-hoc diagnostic, SIMULATED; reads simulation truth (evaluation side only)",
                     "cases": cases})
    for c in cases:
        print(c["scenario"], c["onset"], "R", round(c["R"], 3), "M", round(c["M"], 3), "posterior", round(c["posterior_comms"], 4),
              "true group kWh", round(c["true_group_kwh"], 3), [m["meter"] for m in c["group_meters_with_true_energy"]][:5])


if __name__ == "__main__":
    main()
