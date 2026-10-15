"""SHAHID operator console — preview (decisions 0006 and 0007). Run from the repository root:

    streamlit run ui/app.py

Replays stored simulations (results/demo, shahid.demo_day) through the operator views. SIMULATED;
not a deployed or real-time system; not validated with operators.
"""
import sys
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "ui"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import oplog  # noqa: E402
import state  # noqa: E402
from panels import audit, detail, network, queues, situation, trace, trust  # noqa: E402
from theme import BANNER, CSS, VIEWS, chip, fmt_hm, fmt_int, fmt_num  # noqa: E402

OPLOG = ROOT / "ui" / "operator_log.jsonl"
SPEEDS = [0.5, 1.0, 2.0, 4.0]  # seconds per interval (A-UI-SPEED)

st.set_page_config(page_title="SHAHID console", page_icon=":material/bolt:", layout="wide")
st.html(CSS)
ss = st.session_state
ss.setdefault("sel", None)
ss.setdefault("opened_at", None)
ss.setdefault("act_error", None)
if "view" not in ss:
    ss.view = st.query_params.get("view", "Situation")


@st.cache_data(max_entries=16)
def load_scenario(name):
    return state.load(name)


@st.cache_resource
def load_topology(grid):
    from shahid.world import grid_meta
    return network.topology(grid_meta(grid))


def select(g):
    if ss.sel != (g["scenario"], g["index"]):
        ss.sel, ss.opened_at = (g["scenario"], g["index"]), time.time()


def goto(view):
    ss.view = view
    st.query_params["view"] = view


def step():
    ss.cursor = min(ss.cursor + 1, state.INTERVALS - 1)


def scenario_changed():
    ss.cursor = state.spec(ss.scenario)["default_cursor"]
    ss.sel = None


def next_event():
    n = state.next_event(load_scenario(ss.scenario), ss.cursor)
    if n is not None:
        ss.cursor = min(n, state.INTERVALS - 1)


def jump():
    g, c, hint = state.jump(load_scenario(ss.scenario), ss.get("jump", ""))
    ss.jump_hint = hint
    if c is not None:
        ss.cursor = min(c, state.INTERVALS - 1)
    if g is not None:
        select(g)


def act(g, action, reason_key):
    try:
        oplog.append_action(OPLOG, g["hash"], action, ss.get("operator", "operator"), ss.get(reason_key, ""),
                            seconds=time.time() - (ss.opened_at or time.time()), scenario=g["scenario"])
        ss.sel, ss.act_error = None, None
    except ValueError as err:
        ss.act_error = str(err)


# ---- sidebar: scenario, replay, session, evaluation, about, export ------------------------------------------
names = list(state.scenarios())
with st.sidebar:
    st.html('<div class="micro">Scenario</div>')
    name = st.selectbox("Scenario", names, key="scenario", bind="query-params", on_change=scenario_changed,
                        label_visibility="collapsed")
    sp = state.spec(name)
    st.caption(sp["description"])
    st.html('<ul class="shows">' + "".join(f"<li>{s}</li>" for s in sp["shows"]) + "</ul>")
    st.html('<div class="micro">Replay</div>')
    st.select_slider("Replay time", list(range(state.INTERVALS)), value=sp["default_cursor"], format_func=fmt_hm,
                     key="cursor", bind="query-params")
    with st.container(horizontal=True, gap="small"):
        st.button("Step", icon=":material/skip_next:", on_click=step)
        st.button("Next event", icon=":material/fast_forward:", on_click=next_event, help="Jump to the next silent group")
    playing = st.toggle("Play", key="playing")
    speed = st.select_slider("Seconds per interval", SPEEDS, value=1.0, key="speed")
    st.html('<div class="micro">Session</div>')
    st.text_input("Operator", "operator", key="operator")
    if st.button("Reset session", icon=":material/restart_alt:"):
        oplog.reset(OPLOG)
        ss.sel = None
        st.rerun()
    with st.expander("Evaluation", icon=":material/science:"):
        evaluate = st.toggle("SIMULATION EVALUATION — labels are not available to the detector",
                             disabled=ss.get("presentation", False), key="evaluation")
        st.caption("Decision 0007: an evaluation tool, not part of the operator path.")
    with st.expander("About", icon=":material/info:"):
        st.caption("Preview of the operator screen of proposal Section V-C (decisions 0006, 0007). See ui/README.md and "
                   "docs/LIMITATIONS.md.")

scn = load_scenario(name)
c = ss.cursor
log = oplog.read(OPLOG)
ok_chain, bad_line = oplog.verify_log(OPLOG) if log else (True, None)
ctx = {"name": name, "scn": scn, "c": c, "log": log, "escalation": state.escalation(), "thr": state.thresholds(),
       "snr_limit": state.resolution_snr(), "select": select, "goto": goto, "oplog_path": OPLOG,
       "fast_seconds": oplog.FAST_SECONDS, "act": act, "act_error": ss.act_error}

with st.sidebar:
    st.download_button("Export shift report", state.shift_report(name, scn, c, log), file_name=f"shift_report_{name}.md",
                       mime="text/markdown", icon=":material/download:", type="primary", width="stretch")

presentation = ss.get("presentation", False)
if presentation:
    st.html("<style>.stMarkdown p,.railcard{font-size:1.1rem}[data-testid='stMetricValue']{font-size:34px!important}</style>")


def selected():
    """The selected group, resolved when needed (a click in the main panel can change it)."""
    if not (ss.sel and ss.sel[0] == name):
        return None
    g = next((x for x in scn["groups"] if x["index"] == ss.sel[1]), None)
    return None if g is None or state.status(g, c) == "hidden" else g  # hidden: replay moved before detection


# ---- top bar -------------------------------------------------------------------------------------------------
tl, tj, tp = st.columns([7.0, 1.6, 1.4], vertical_alignment="center", gap="small")
tl.html('<div class="topbar" style="justify-content:space-between">'
        '<div class="topbar"><span class="mark">⚡ SHAHID</span>' + chip(scn["grid"]) + chip("detector v1 (frozen)") + "</div>"
        '<div class="topbar">' + chip(f"scenario · {name}", "chip-active") + chip(f"window 00:00–{fmt_hm(c)}")
        + chip(f"{fmt_num(speed, 1)} s / interval" + (" · playing" if playing else "")) + "</div>"
        f'<div class="topbar"><span class="clock">{scn["day0"]:%Y-%m-%d} {fmt_hm(c)}</span>'
        + chip("LINK: SIMULATED REPLAY", "chip-amber")
        + (chip(f"chain intact · {fmt_int(len(log))}", "chip-ok") if ok_chain else chip(f"chain broken · line {fmt_int(bad_line)}", "chip-bad"))
        + f'</div></div><div class="simline">{BANNER}</div>')
with tj:
    st.text_input("Jump", key="jump", on_change=jump, placeholder="m042 · 7 · 10:15", label_visibility="collapsed",
                  icon=":material/search:")
    if ss.get("jump_hint"):
        st.caption(ss.jump_hint)
with tp:
    initials = "".join(w[0] for w in ss.get("operator", "operator").split()[:2]).upper() or "OP"
    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        st.html(f'<span class="chip" style="border-radius:50%;width:30px;height:30px;justify-content:center;padding:0">{initials}</span>')
        st.toggle("Present", key="presentation")  # recording aid: larger type; evaluation toggle disabled

# ---- icon rail + main ----------------------------------------------------------------------------------------
rail, main = st.columns([0.045, 1], gap="small")
with rail, st.container(key="rail", gap="small"):
    for v, ic in VIEWS.items():
        st.button(ic, key=f"nav_{v}", help=v, on_click=goto, args=(v,),
                  type="primary" if ss.view == v and not (evaluate and not presentation) else "tertiary")
    st.button(":material/science:", key="nav_Evaluation", disabled=not evaluate or presentation,
              help="Simulation evaluation — enable the toggle under Evaluation in the sidebar (decision 0007)",
              type="primary" if evaluate and not presentation else "tertiary")

with main:
    view = ss.view if ss.view in VIEWS else "Situation"
    g = selected()
    ctx["selected"] = g
    if evaluate and not presentation:
        from panels import evaluation  # only reachable through the explicit toggle (decision 0007)
        evaluation.render(ctx)
    elif view == "Situation":
        situation.render(ctx, g)
    elif view in ("Queues", "Network", "Trace"):
        left, right = st.columns([2.3, 1], gap="small")
        with left:
            if view == "Queues":
                queues.render(ctx)
            elif view == "Network":
                network.render(ctx, load_topology(scn["grid"]), g)
            else:
                trace.render(ctx, g)
        with right:
            g = selected()
            if g is not None:
                detail.render(ctx, g)
            else:
                situation.health(ctx, state.kpis(scn, c, log))
    elif view == "Audit":
        audit.render(ctx)
    elif view == "Trust":
        trust.render(ctx)


@st.fragment(run_every=speed if playing else None)
def ticker():
    if ss.get("playing") and ss.cursor < state.INTERVALS - 1:
        ss.cursor += 1
        st.rerun(scope="app")


ticker()
