"""Phase 2 studies: version 1 stays reproducible through the new code paths (protocols 01-05)."""
import json

import numpy as np
import pytest

from shahid import detect, detect_v2, p2cache, p2eval, scenario
from shahid.cp5_compare import inputs_of

FROZEN = json.load(open("results/detector_params.json"))
P = {**FROZEN["fitted"], **FROZEN["thresholds"]["bayes"]}


def short_cfg(**gen):
    return scenario.merge(scenario.load_cfg("configs/cp5_episodes.yaml"),
                          {"world": {"start_day": 120, "days": 30}, "seed": 101,
                           "generator": {"n": 12, "first_day": 15, **gen}})


@pytest.fixture(scope="module")
def inputs():
    return inputs_of(scenario.simulate(short_cfg()))


def test_v2_module_with_switches_off_equals_frozen_detector(inputs):
    a = detect.detect(inputs, P, "bayes")
    t = detect_v2.evidence_table(inputs, P, detect_v2.RULES_V1)
    b = detect_v2.decide_table(t, P, detect_v2.RULES_V1, 0.03)
    assert len(a) == len(b) > 0
    assert (a.verdict.values == b.verdict.values).all()
    assert np.allclose(a.p_comms.values.astype(float), b.p_comms.values.astype(float), equal_nan=True)


def test_cache_v1_grouping_reproduces_frozen_detector(inputs):
    a = detect.detect(inputs, P, "bayes")
    g, _, _ = p2cache.build(inputs, FROZEN["fitted"])
    g = g[g["mode"] == "v1"].reset_index(drop=True)
    d = p2eval.decide(g, p2eval.v1_posterior, 0.03)
    assert (d.verdict.values == a.verdict.values).all()
    assert np.allclose(d.p_comms.values, a.p_comms.values.astype(float))


def test_split_groups_partition_every_v1_group(inputs):
    g, _, _ = p2cache.build(inputs, FROZEN["fitted"])
    for onset, s in g.groupby("onset"):
        v1 = set(s[s["mode"] == "v1"].meters.iloc[0])
        parts = [set(m) for m in s[s["mode"] == "split"].meters]
        assert set().union(*parts) == v1 and sum(map(len, parts)) == len(v1)


def test_simulator_defaults_unchanged_and_offsets_only_touch_onset_step():
    base = scenario.simulate(short_cfg(mix={"outage": 1.0}))
    again = scenario.simulate(short_cfg(mix={"outage": 1.0}))
    off = scenario.simulate(short_cfg(mix={"outage": 1.0}, offset_min=[10]))
    assert base["observed"]["meter_readings"].equals(again["observed"]["meter_readings"])
    e0, e1 = base["truth"]["meter_energy_true"], off["truth"]["meter_energy_true"]
    ep = off["labels"]["episodes"]
    assert (ep.offset_min == 10).all()
    starts = set(ep.start)
    diff_rows = set(e0.index[(e0 - e1).abs().sum(1) > 0])
    assert diff_rows and diff_rows <= starts  # only onset steps change
