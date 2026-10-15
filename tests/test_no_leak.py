"""The detector must never see truth/ or labels/ (data contract, integrity rule)."""
import builtins
import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from shahid import detect, scenario

CFG = scenario.merge(scenario.load_cfg("configs/smoke.yaml"), {
    "world": {"grid": "1-LV-semiurb4--0-sw", "start_day": 100, "days": 4},
    "events": [{"type": "outage", "feeder": 0, "start_step": 300, "duration_steps": 4},
               {"type": "comms_failure", "concentrator": 1, "start_step": 340,
                "duration_steps": 4}]})


PARAMS = {"history_days": 1, "gap_const": 0.0, "gap_sd": 0.02, "gap_acf1": 0.3,
          "rho_by_lead": [0.9], "sigma_mult_by_lead": [1.0], "rho1_by_lead": [0.8],
          "sigma1_mult_by_lead": [1.0], "t_df": 4, "prior_comms": 0.5, "abstain_band": 0.05}


@pytest.fixture(scope="module")
def scen(tmp_path_factory):
    d = tmp_path_factory.mktemp("scen")
    return scenario.write(scenario.simulate(CFG), d, CFG, "test")


def test_detector_source_never_names_truth_or_labels():
    src = inspect.getsource(detect).lower()
    assert "truth" not in src and "label" not in src


def test_detector_reads_only_observed_and_context(scen, monkeypatch):
    seen = []

    def guard(fn):
        def wrapped(path, *a, **k):
            p = Path(str(path)).as_posix()
            seen.append(p)
            assert "/truth/" not in p and "/labels/" not in p, f"leak: {p}"
            return fn(path, *a, **k)
        return wrapped

    monkeypatch.setattr(pd, "read_parquet", guard(pd.read_parquet))
    monkeypatch.setattr(np, "load", guard(np.load))
    monkeypatch.setattr(builtins, "open", guard(builtins.open))
    inputs = detect.load_inputs(scen)
    detect.detect(inputs, PARAMS)
    assert seen and all(("/observed/" in p or "/context/" in p) for p in seen)


def test_inputs_have_no_truth_columns(scen):
    inputs = detect.load_inputs(scen)
    truth_cols = set(pd.read_parquet(scen / "truth" / "meter_energy_true.parquet").columns)
    label_cols = set(pd.read_parquet(scen / "labels" / "episodes.parquet").columns)
    for name, df in inputs.items():
        assert not (set(df.columns) & (label_cols - {"start", "end", "n_meters", "meters", "meter_id", "interval_start"})), name
        assert not (set(df.columns) & truth_cols), name
