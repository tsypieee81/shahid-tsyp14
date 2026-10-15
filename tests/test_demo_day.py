"""Demo replay (shahid.demo_day): verdicts equal a direct shahid.detect call, the replay opens only
observed/context data, and the committed result files are stamped and carry no truth or labels."""
import builtins
import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from shahid import demo_day, detect, scenario
from tests.test_no_leak import CFG, PARAMS


@pytest.fixture(scope="module")
def scen(tmp_path_factory):
    d = tmp_path_factory.mktemp("demo")
    return scenario.write(scenario.simulate(CFG), d, CFG, "test")


def test_replay_matches_direct_detector_call(scen):
    inputs = detect.load_inputs(scen)
    day0 = 96 * 2
    out, log = demo_day.replay(inputs, PARAMS, day0)
    direct = detect.detect(inputs, PARAMS, "bayes")
    direct = direct[direct.onset >= inputs["trafo"].interval_start.iloc[day0]]
    assert len(out["groups"]) == len(direct) == len(log) > 0
    assert [g["verdict"] for g in out["groups"]] == direct.verdict.tolist()
    assert [g["n_meters"] for g in out["groups"]] == direct.n_meters.tolist()


def test_replay_opens_only_observed_and_context(scen, monkeypatch):
    seen = []

    def guard(fn):
        def wrapped(path, *a, **k):
            p = Path(str(path)).as_posix()
            seen.append(p)
            assert "/truth/" not in p and "/labels/" not in p, f"leak: {p}"
            return fn(path, *a, **k)
        return wrapped

    inputs = detect.load_inputs(scen)
    monkeypatch.setattr(pd, "read_parquet", guard(pd.read_parquet))
    monkeypatch.setattr(np, "load", guard(np.load))
    monkeypatch.setattr(builtins, "open", guard(builtins.open))
    demo_day.replay(inputs, PARAMS, 96 * 2)
    assert all("truth" not in p and "label" not in p for p in seen)


def test_demo_source_and_result_files_carry_no_truth_or_labels():
    src = inspect.getsource(demo_day).lower()
    assert "truth" not in src and "label" not in src
    files = sorted(Path("results/demo").glob("*.json"))
    replays = [f for f in files if not f.name.endswith("_eval.json")]
    assert replays
    for f in replays:
        d = json.loads(f.read_text(encoding="utf8"))
        assert d["stamp"]["command"].startswith("python -m shahid.demo_day")
        text = f.read_text(encoding="utf8").lower()
        assert '"truth"' not in text and '"labels"' not in text and "group_truth" not in text


def test_expected_series_adds_up_to_the_detector_window_evidence():
    """expected_kwh is the detector's own window evidence differenced: its cumulative sum over the first
    K + L intervals equals the stored M at lead L."""
    d = json.loads(Path("results/demo/showcase.json").read_text(encoding="utf8"))
    for g in d["groups"]:
        for ev in g["leads"]:
            n = 2 + ev["lead"]
            assert abs(sum(g["expected_kwh"][:n]) - ev["M"]) < 1e-6
    t = d["trace"]
    assert all(0 <= x["n_reporting"] <= d["n_meters"] for x in t)
