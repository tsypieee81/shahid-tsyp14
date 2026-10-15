"""'lr_band' is a rename of 'bayes' (prior 0.5): identical verdicts, probabilities and evidence."""
import json

import numpy as np
import pandas as pd

from shahid import detect


def test_lr_band_equals_bayes():
    rng = np.random.default_rng(0)
    table = [{"onset": pd.Timestamp("2016-01-20") + pd.Timedelta(minutes=15 * i), "t0": i,
              "n_meters": 3, "meters": ["m001"],
              "evs": [{"R": float(rng.normal(1, 2)), "M": float(rng.normal(2, 2)),
                       "sd_O": float(rng.uniform(0.05, 0.5)), "sd_C": float(rng.uniform(0.3, 2)),
                       "n_intervals": 2 + L, "gap0": 0.0, "dev_before_onset": 0.0}
                      for L in range(5)]} for i in range(400)]
    p = {**json.load(open("results/detector_params.json"))["fitted"],
         **json.load(open("results/detector_params.json"))["thresholds"]["bayes"]}
    a = detect.decide_table(table, "bayes", p).drop(columns="method")
    b = detect.decide_table(table, "lr_band", p).drop(columns="method")
    pd.testing.assert_frame_equal(a, b)
    # and the explicit rule: comms iff llr >= logit(1-band), outage iff llr <= -logit(1-band)
    assert set(a.verdict) <= {"OUTAGE", "COMMS_FAILURE", "UNCERTAIN"}
    lim = np.log((1 - p["abstain_band"]) / p["abstain_band"])
    llr = np.log(a.p_comms / (1 - a.p_comms))
    assert ((a.verdict == "COMMS_FAILURE") == (llr >= lim - 1e-9)).all()
    assert ((a.verdict == "OUTAGE") == (llr <= -lim + 1e-9)).all()
