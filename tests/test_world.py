"""World and observation model behave as documented in docs/anomaly_generation.md."""
import json

import numpy as np
import pandas as pd
import pytest

from shahid import scenario

CFG = scenario.merge(scenario.load_cfg("configs/smoke.yaml"), {
    "world": {"grid": "1-LV-semiurb4--0-sw", "start_day": 100, "days": 4,
              "unmetered": {"kind": "constant", "kw": 2.0}},
    "events": [{"type": "outage", "feeder": 0, "start_step": 300, "duration_steps": 4},
               {"type": "comms_failure", "concentrator": 1, "start_step": 340,
                "duration_steps": 4}]})


@pytest.fixture(scope="module")
def sim():
    return scenario.simulate(CFG)


def test_outage_cuts_supply_and_readings(sim):
    ep = sim["labels"]["episodes"]
    out = ep[ep.cause == "OUTAGE"].iloc[0]
    meters = json.loads(out.meters)
    e = sim["truth"]["meter_energy_true"].to_numpy()
    assert np.all(e[300:304, meters] == 0)
    assert np.all(e[296:300, meters].sum(0) != 0)
    r = sim["observed"]["meter_readings"]
    ids = [f"m{m:03d}" for m in meters]
    hit = r[r.meter_id.astype(str).isin(ids) & (r.interval_start >= out.start)
            & (r.interval_start < out.end)]
    assert hit.empty  # unpowered meters send nothing (backfill and last gasp are off)


def test_comms_backlog_arrives_after_link_returns(sim):
    ep = sim["labels"]["episodes"]
    c = ep[ep.cause == "COMMS_FAILURE"].iloc[0]
    ids = [f"m{m:03d}" for m in json.loads(c.meters)]
    r = sim["observed"]["meter_readings"]
    hit = r[r.meter_id.astype(str).isin(ids) & (r.interval_start >= c.start)
            & (r.interval_start < c.end)]
    assert len(hit) > 0 and (hit.arrival_ts >= c.end).all()
    # power was not lost: true energy is non-zero
    e = sim["truth"]["meter_energy_true"].loc[c.start:c.end - pd.Timedelta(minutes=15), ids]
    assert (e.abs().sum(0) > 0).all()


def test_unmetered_energy_added_to_transformer(sim):
    u = sim["truth"]["unmetered_kwh"]
    assert np.allclose(u, 2.0 * 0.25)
    assert np.allclose(sim["truth"]["trafo_true_kwh"]
                       - (-sim["truth"]["powerflow"]["trafo_p_lv"][:, 0] * 250), u)


def test_deterministic(sim):
    again = scenario.simulate(CFG)
    pd.testing.assert_frame_equal(sim["observed"]["meter_readings"],
                                  again["observed"]["meter_readings"])
    pd.testing.assert_frame_equal(sim["observed"]["transformer"], again["observed"]["transformer"])


def test_labels_cover_every_silent_cell(sim):
    cells = sim["labels"]["cells"]
    assert set(cells.cause.unique()) >= {"OUTAGE", "COMMS_FAILURE", "RANDOM_LOSS"}
