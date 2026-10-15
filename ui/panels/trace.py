"""V5 Trace and the Situation hero: grid balance over the replayed day.

Three series up to the replay time: transformer energy, the sum of meters that reported on time, and
reporting + expected energy of the selected silent group (the communication-failure hypothesis; the
outage hypothesis is the reporting line itself). The gap between transformer and reporting is shaded.
"""
import altair as alt
import pandas as pd
import streamlit as st

import state
from theme import COLORS, FAINT, MUTED, SHORT, TEXT, VERDICTS, fmt_hm, fmt_int

SERIES = {"transformer": "Transformer", "reporting": "Reporting meters", "hypothesis": "If only data were lost"}


def series(scn, c):
    """Intervals complete at replay time c (interval t is known at t + 1 <= c), long format."""
    t = pd.DataFrame(scn["trace"][: max(c, 1)])
    t["time"] = pd.to_datetime(t.interval_start)
    return t.melt(id_vars="time", value_vars=["transformer_kwh", "reporting_meters_kwh"], var_name="series", value_name="kwh")


def hypothesis(scn, c, g):
    """Reporting + expected energy of group g from its onset, up to the replay time (detector evidence)."""
    if g is None:
        return pd.DataFrame(columns=["time", "kwh"])
    rows = []
    cols = [scn["meter_id"].index(m) for m in g["meters"]]
    for k, e in enumerate(g.get("expected_kwh", [])):
        t = g["onset_i"] + k
        if t >= min(c, state.INTERVALS):
            break
        late = sum(not (0 <= scn["arrival"][t][m] <= t + 1) for m in cols)  # readings of t not on time
        if 2 * late < len(cols):  # the group reports again: the hypothesis no longer applies
            break
        rows.append({"time": state.time_of(scn, t), "kwh": scn["trace"][t]["reporting_meters_kwh"] + e})
    return pd.DataFrame(rows, columns=["time", "kwh"])


def default_group(scn, c, g):
    """The selected group, else the largest visible group (ties: most recent)."""
    if g is not None:
        return g
    vis = state.visible(scn, c)
    return max(vis, key=lambda x: (x["n_meters"], x["onset_i"])) if vis else None


def chart(scn, c, g, height=300):
    dom = [scn["day0"].isoformat(), state.time_of(scn, state.INTERVALS).isoformat()]
    x = alt.X("time:T", title=None, scale=alt.Scale(domain=dom),
              axis=alt.Axis(format="%H:%M", tickCount=12, labelColor=MUTED,
                            gridColor="#1a2438", domainColor="#1e293b", tickColor="#1e293b", labelFlush=True))
    y_ax = alt.Axis(title="kWh per 15-min interval", titleColor=MUTED, titleFontWeight=400, labelColor=MUTED,
                    gridColor="#1a2438", domainColor="#1e293b", tickColor="#1e293b")
    t = pd.DataFrame(scn["trace"][: max(c, 1)])
    t["time"] = pd.to_datetime(t.interval_start)
    layers = []
    bands = pd.DataFrame([{"a": state.time_of(scn, x["onset_i"]), "b": state.time_of(scn, min(x["decided_i"], c)),
                           "v": x["verdict"] if state.status(x, c) == "decided" else "UNCERTAIN"}
                          for x in state.visible(scn, c) if x["n_meters"] > 1], columns=["a", "b", "v"])
    cs = alt.Scale(domain=list(VERDICTS), range=[COLORS[k] for k in VERDICTS])
    if len(bands):
        layers.append(alt.Chart(bands).mark_rect(opacity=0.08).encode(
            x="a:T", x2="b:T", color=alt.Color("v:N", scale=cs, legend=None)))
    layers.append(alt.Chart(t).mark_area(opacity=0.12, color=COLORS["UNCERTAIN"]).encode(
        x=x, y=alt.Y("reporting_meters_kwh:Q", axis=y_ax), y2="transformer_kwh:Q"))
    layers.append(alt.Chart(t).mark_line(color=FAINT, strokeWidth=1.6).encode(
        x="time:T", y="reporting_meters_kwh:Q", tooltip=[alt.Tooltip("time:T", format="%H:%M"),
                                                          alt.Tooltip("reporting_meters_kwh:Q", title="reporting kWh", format=".2f")]))
    layers.append(alt.Chart(t).mark_line(color=TEXT, strokeWidth=1.8).encode(
        x="time:T", y="transformer_kwh:Q", tooltip=[alt.Tooltip("time:T", format="%H:%M"),
                                                     alt.Tooltip("transformer_kwh:Q", title="transformer kWh", format=".2f"),
                                                     alt.Tooltip("gap_kwh:Q", title="gap kWh", format=".2f")]))
    g = default_group(scn, c, g)
    h = hypothesis(scn, c, g)
    if len(h):
        layers.append(alt.Chart(h).mark_line(color=COLORS["COMMS_FAILURE"], strokeDash=[4, 3], strokeWidth=2.2,
                                             point=alt.OverlayMarkDef(size=14, color=COLORS["COMMS_FAILURE"])).encode(
            x="time:T", y="kwh:Q", tooltip=[alt.Tooltip("time:T", format="%H:%M"),
                                           alt.Tooltip("kwh:Q", title="if only data lost, kWh", format=".2f")]))
    marks = pd.DataFrame([{"t": state.time_of(scn, x["decided_i"]), "v": x["verdict"], "y": 0}
                          for x in state.visible(scn, c) if state.status(x, c) == "decided" and x["n_meters"] > 1],
                         columns=["t", "v", "y"])
    if len(marks):
        layers.append(alt.Chart(marks).mark_point(shape="triangle-up", size=70, filled=True, opacity=0.95).encode(
            x="t:T", y=alt.Y("y:Q"), color=alt.Color("v:N", scale=cs, legend=None)))
    now = pd.DataFrame({"t": [state.time_of(scn, c)]})
    layers.append(alt.Chart(now).mark_rule(color="#cbd5e1", strokeWidth=1, strokeDash=[2, 2]).encode(x="t:T"))
    return alt.layer(*layers).properties(height=height).configure_view(stroke=None), g


def legend(g):
    from theme import chip
    who = "" if g is None else f" · group {fmt_int(g['n_meters'])} m from {fmt_hm(g['onset'])}"
    return ('<div class="topbar">'
            + chip(f'<i style="width:14px;height:2px;background:{TEXT};display:inline-block"></i> Transformer')
            + chip(f'<i style="width:14px;height:2px;background:{FAINT};display:inline-block"></i> Reporting meters')
            + chip(f'<i style="width:14px;border-top:2px dashed {COLORS["COMMS_FAILURE"]};display:inline-block"></i> If only data were lost{who}')
            + chip('<i style="width:12px;height:8px;background:rgba(245,158,11,.35);display:inline-block"></i> Gap')
            + "</div>")


CAPTION = ("If only data were lost, the transformer tracks the dotted line; if power were lost, it tracks the grey line.")


def render(ctx, g):
    scn, c = ctx["scn"], ctx["c"]
    vis = [x for x in state.visible(scn, c) if x["n_meters"] > 1]
    if vis:
        opts = {x["index"]: f"{fmt_int(x['n_meters'])} m · {fmt_hm(x['onset'])}" for x in vis}
        cur = g["index"] if g is not None and g["index"] in opts else None
        pick = st.pills("Silent group", list(opts), format_func=opts.get, default=cur, key=f"tracepick_{ctx['name']}_{cur}",
                        label_visibility="collapsed")
        if pick is not None and pick != cur:
            ctx["select"](next(x for x in vis if x["index"] == pick))
            st.rerun()
    ch, shown = chart(scn, c, g, height=420)
    st.html(legend(shown))
    st.altair_chart(ch, alt="Transformer energy, reporting meters and the communication-failure hypothesis over the day")
    st.caption(CAPTION + " Triangles: verdicts of multi-meter groups; tinted bands: from onset to verdict.")
    if shown is not None:
        st.caption(f"Dotted line for: {SHORT[shown['verdict']] if state.status(shown, c) == 'decided' else 'evidence accumulating'}, "
                   f"{fmt_int(shown['n_meters'], 'meters')} silent from {fmt_hm(shown['onset'])}.")
