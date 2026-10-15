"""Classifier-comparison leak controls (docs/studies/classifier_comparison/PROTOCOL.md section 4):
no truth, label or ground-truth column in the features; no urban or rural row in training or
validation."""
import numpy as np
import pandas as pd

from shahid import classifier_study as cs


def toy_groups(family, n=6):
    g = pd.DataFrame({"family": family, "seed": 1, "gid": range(n),
                      "onset": pd.date_range("2016-02-01", periods=n, freq="7D"),
                      "n_meters": 3, "outage_share": [0.0, 1.0] * (n // 2), "frozen_verdict": "OUTAGE",
                      "frozen_latency": 2})
    for L in range(cs.LEADS):
        for k in cs.EV:
            g[f"{k}_{L}"] = np.arange(n, dtype=float) + 1 + L
    g["week"] = [0, 1, 2, 3, 0, 2][:n]
    g["label"] = (g.outage_share > 0.5).astype(int)
    return g


def test_features_never_contain_truth_or_labels():
    f = cs.feature_frame(toy_groups("cp5"), 2)
    assert list(f.columns) == cs.FEATURES
    bad = {"outage_share", "label", "frozen_verdict", "frozen_latency", "cause", "episode_id", "truth"}
    assert not (set(f.columns) & bad)
    assert not (set(cs.FEATURES_ABL) & set(cs.ABLATED))


def test_training_and_validation_use_only_the_development_network():
    G = {f: toy_groups(f) for f in cs.FAMILIES}
    tr, va = cs.split_frames(G)
    assert set(tr.family) | set(va.family) <= {"cp5", "ff_semiurb5"}
    assert set(tr.week) <= {0, 1} and set(va.week) == {2}
    held = {f for fams, _ in cs.TEST.values() for f in fams}
    assert not (held & (set(tr.family) | set(va.family)))
