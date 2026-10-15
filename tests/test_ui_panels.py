"""Operator UI preview: pure logic of ui/state.py, panel data functions, headless render of every view,
and the operator path never opening simulation outcomes (decision 0007)."""
import builtins
import io
import sys
from pathlib import Path

import pytest

UI = Path(__file__).resolve().parents[1] / "ui"
sys.path.insert(0, str(UI))
import state  # noqa: E402

SCN = "feeder_outage_morning"


@pytest.fixture(scope="module")
def scn():
    return state.load(SCN)


def big(scn):
    return next(g for g in scn["groups"] if g["n_meters"] > 30)


def test_cursor_semantics(scn):
    g = big(scn)
    assert state.status(g, g["onset_i"] + 1) == "hidden"
    assert state.status(g, g["onset_i"] + state.K) in ("forming", "decided")
    assert state.status(g, g["decided_i"]) == "decided"
    assert state.lead_at(g, g["onset_i"] + state.K + 9) == state.L_MAX


def test_queues_never_merge_and_actions_close_items(scn):
    g = big(scn)
    c = g["decided_i"] + 1
    q = state.queues(scn, c, [])
    keys = list(state.QUEUE_ORDER)
    for i, a in enumerate(keys):  # every decided item sits in exactly one of the three queues
        for b in keys[i + 1:]:
            assert not {x["hash"] for x in q[a]} & {x["hash"] for x in q[b]}
    assert all(x["verdict"] == k for k in keys for x in q[k])
    assert g in q[g["verdict"]]
    closed = state.queues(scn, c, [{"item": g["hash"], "action": "APPROVED"}])
    assert g not in closed[g["verdict"]]
    deferred = state.queues(scn, c, [{"item": g["hash"], "action": "DEFERRED"}])
    assert g in deferred[g["verdict"]]


def test_audit_sample_is_automatic_comms_only(scn):
    for name in state.scenarios():
        s = state.load(name)
        for g in state.queues(s, state.INTERVALS - 1, [])["AUDIT"]:
            assert g["verdict"] == "COMMS_FAILURE" and g["escalation"]["handled_by"] == "AUTOMATED"


def test_tally_and_thresholds_come_from_result_files(scn):
    t = state.tally(scn, state.INTERVALS - 1)
    assert t["decided"] == sum(t["counts"].values()) > 0
    assert state.thresholds()["abstain_band"] == 0.03
    assert state.resolution_snr() > 0


def test_panel_data_functions(scn):
    pytest.importorskip("streamlit")
    from panels import detail, evaluation, situation, trace, trust
    g = big(scn)
    b = detail.bars(g)
    assert list(b.kwh) == [g["leads"][g["decided_lead"]]["M"], g["leads"][g["decided_lead"]]["R"]]
    w = detail.waterfall(g, state.thresholds())
    assert w["posterior"] == g["leads"][g["decided_lead"]]["posterior_comms"]
    assert abs(1 / (1 + 2.718281828459045 ** -w["posterior_logodds"]) - w["posterior"]) < 1e-6
    assert len(detail.accumulation(g)) == state.L_MAX + 1
    assert len(situation.strip(scn, state.INTERVALS - 1)) == len(scn["groups"])
    assert set(trace.series(scn, 10).series) == {"transformer_kwh", "reporting_meters_kwh"}
    assert set(trust.track_record(trust.outcomes()).verdict) == {"OUTAGE", "COMMS_FAILURE"}
    s = evaluation.episode_summary(evaluation.load_eval(SCN))
    assert s["episodes"] >= 1


def test_evaluation_view_imports_nothing_from_the_detector():
    import ast
    tree = ast.parse((UI / "panels" / "evaluation.py").read_text(encoding="utf8"))
    mods = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    mods += [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    mods += [a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names]
    assert not [m for m in mods if "detect" in m], mods


@pytest.mark.parametrize("view", ["Situation", "Queues", "Network", "Trace", "Audit", "Trust"])
def test_every_view_renders_headless(view, monkeypatch, tmp_path):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(UI / "app.py"), default_timeout=240)
    at.session_state["scenario"] = SCN
    at.session_state["sel"] = (SCN, big(state.load(SCN))["index"])
    at.run()
    at.session_state["view"] = view
    at.run()
    assert not at.exception


def test_evaluation_view_renders_behind_toggle():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(UI / "app.py"), default_timeout=240)
    at.session_state["evaluation"] = True
    at.run()
    assert not at.exception
    assert any("SIMULATION EVALUATION" in e.value for e in at.error)


@pytest.mark.parametrize("view", ["Situation", "Queues", "Network", "Trace", "Audit"])
def test_operator_views_never_open_outcomes_labels_or_truth(view, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    seen = []

    def guard(fn):
        def wrapped(path, *a, **k):
            seen.append(Path(str(path)).as_posix())
            return fn(path, *a, **k)
        return wrapped

    monkeypatch.setattr(builtins, "open", guard(builtins.open))
    monkeypatch.setattr(io, "open", guard(io.open))
    at = AppTest.from_file(str(UI / "app.py"), default_timeout=240)
    at.session_state["sel"] = (SCN, 0)
    at.session_state["scenario"] = SCN
    at.run()
    at.session_state["view"] = view
    at.run()
    assert not at.exception
    bad = [p for p in seen if p.endswith("_eval.json") or "/labels/" in p or "/truth/" in p]
    assert not bad, bad


# ---- console redesign (phase2-dashboard-v2) ----------------------------------------------------------------
import re  # noqa: E402

import theme  # noqa: E402


def test_formatters():
    assert theme.fmt_kwh(2.371) == "2.37 kWh" and theme.fmt_kwh(None) == "—"
    assert theme.fmt_p(0.0034) == "0.003"
    assert theme.fmt_p(0.9995) == ">0.999" and theme.fmt_p(0.99949) == "0.999" and theme.fmt_p(1.0) == ">0.999"
    assert theme.fmt_p(0.0005) == "<0.001" and theme.fmt_p(0.00051) == "0.001" and theme.fmt_p(0.0) == "<0.001"
    assert theme.fmt_hm(41) == "10:15" and theme.fmt_hm("2016-06-09 06:15:00") == "06:15"
    assert theme.fmt_pct(3, 7) == "43% (3 of 7)" and theme.fmt_pct(0.75) == "75%" and theme.fmt_pct(1, 0) == "—"
    assert theme.fmt_int(6, "int") == "6 int" and theme.fmt_signed(-25) == "-25"


def test_panels_format_numbers_only_through_theme():
    """No Python format spec or round() in the app or panels: every numeral goes through theme.fmt_*."""
    spec = re.compile(r"\{[^{}]*:[+ ,.0-9]*[dfge%]\}|round\(|%\.\d+f\" %")
    for f in [UI / "app.py", *sorted((UI / "panels").glob("*.py"))]:
        bad = [ln for ln in f.read_text(encoding="utf8").splitlines() if spec.search(ln)]
        assert not bad, (f.name, bad)


def test_showcase_default_cursor_fills_every_queue():
    sp = state.spec("showcase")
    s = state.load("showcase")
    q = state.queues(s, sp["default_cursor"], [])
    assert all(q[k] for k in state.QUEUE_ORDER), {k: len(v) for k, v in q.items()}
    assert len(state.visible(s, sp["default_cursor"])) >= 6  # event feed rows
    assert list(state.scenarios())[0] == "showcase"  # the console opens on it


def test_jump_search_parsing():
    s = state.load("showcase")
    g, c, hint = state.jump(s, "m042")
    assert g is not None and "m042" in g["meters"] and c == g["onset_i"] + state.K and not hint
    g, c, _ = state.jump(s, "#4")
    assert g["index"] == 4
    assert state.jump(s, "10:15")[1] >= 41
    for bad in ("zz", "m999", "25:00", "99"):
        g, c, hint = state.jump(s, bad)
        assert g is None and hint
    assert state.jump(s, "") == (None, None, "")


def test_default_cursor_honoured_and_shim_renders():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(UI / "app.py"), default_timeout=240)
    at.run()
    assert not at.exception
    assert at.session_state["scenario"] == "showcase"
    assert at.session_state["cursor"] == state.spec("showcase")["default_cursor"]
    assert any("SIMULATED DATA — Phase 1/2 prototype, not a deployed system." in str(h.proto) for h in at.get("html"))
    shim = AppTest.from_file(str(UI / "dashboard.py"), default_timeout=240)
    shim.run()
    assert not shim.exception


def test_queue_survives_stale_selection(monkeypatch):
    """After the selected last row of a queue is acted on, Streamlit still reports its old row index; the
    queue must ignore an index past the end instead of raising IndexError (queues.py)."""
    pytest.importorskip("streamlit")
    import types

    import streamlit
    from streamlit.testing.v1 import AppTest
    real = streamlit.dataframe

    def stale(*a, **k):
        real(*a, **k)
        if str(k.get("key", "")).startswith("q_"):
            return types.SimpleNamespace(selection=types.SimpleNamespace(rows=[999]))
    monkeypatch.setattr(streamlit, "dataframe", stale)
    at = AppTest.from_file(str(UI / "app.py"), default_timeout=240)
    at.run()
    at.session_state["view"] = "Queues"
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_replay_time_in_the_url():
    """ui/README.md: the replay time is kept in the URL as HH:MM."""
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(UI / "app.py"), default_timeout=240)
    at.query_params["scenario"] = "showcase"
    at.query_params["cursor"] = "11:30"
    at.run()
    assert not at.exception
    assert at.session_state["cursor"] == 46
