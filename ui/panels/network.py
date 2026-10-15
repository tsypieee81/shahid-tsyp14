"""V4: the LV network from the SimBench grid (bus coordinates and lines), meters coloured by state."""
import json

import altair as alt
import pandas as pd
import streamlit as st

import state
from theme import COLORS, SHORT, TEXT, chip


def topology(meta):
    """Bus coordinates, line segments and meter positions from the grid (shahid.world.grid_meta)."""
    net = meta["net"]
    xy = {b: json.loads(g)["coordinates"] for b, g in net.bus.geo.items() if isinstance(g, str)}
    edges = pd.DataFrame([{"x": xy[r.from_bus][0], "y": xy[r.from_bus][1], "x2": xy[r.to_bus][0], "y2": xy[r.to_bus][1]}
                          for r in net.line.itertuples() if r.from_bus in xy and r.to_bus in xy])
    lv = int(net.trafo.lv_bus.iloc[0])
    meters = pd.DataFrame({"meter": range(meta["n_meters"]), "bus": list(meta["load_bus"])})
    meters["x"] = [xy[b][0] for b in meters.bus]
    meters["y"] = [xy[b][1] for b in meters.bus]
    return {"edges": edges, "meters": meters, "transformer": xy.get(lv)}


def meter_states(scn, c, meters):
    """State per meter at cursor c: the verdict colour of the silent group it belongs to, else reporting;
    with its feeder, PV size, previous-day energy, lag and last voltage (observed data only)."""
    ids = scn["meter_id"]
    st_, grp = ["REPORTING"] * len(ids), [None] * len(ids)
    mv = state.meter_view(scn, c)
    for g in state.visible(scn, c):  # later groups overwrite earlier ones
        s = g["verdict"] if state.status(g, c) == "decided" else "UNCERTAIN"
        for m in g["meters"]:
            i = ids.index(m)
            if mv[i]["lag"] >= 1:  # still silent at the replay time; a restored meter is shown reporting
                st_[i], grp[i] = s, g["index"]
    out = meters.copy()
    out["state"] = [st_[i] for i in out.meter]
    out["group"] = [grp[i] for i in out.meter]
    out["pv"] = [scn["pv_kw"][i] > 0 for i in out.meter]
    out["pv_kw"] = [scn["pv_kw"][i] for i in out.meter]
    out["meter_id"] = [ids[i] for i in out.meter]
    out["feeder"] = [scn["feeder"][i] for i in out.meter]
    out["kwh"] = [max(scn["prev_day_kwh"][i], 0.0) for i in out.meter]
    out["lag"] = [mv[i]["lag"] for i in out.meter]
    out["voltage_v"] = [mv[i]["voltage_v"] for i in out.meter]
    # meters sharing a bus are spread on a small ring so each stays visible
    k = out.groupby("bus").cumcount()
    out["x"] = out.x + 0.00006 * (k % 4)
    out["y"] = out.y + 0.00006 * (k // 4)
    return out


def legend_html():
    keys = ["REPORTING", "OUTAGE", "UNCERTAIN", "COMMS_FAILURE"]
    dots = "".join(chip(f'<i style="width:9px;height:9px;border-radius:50%;background:{COLORS[k]};display:inline-block"></i> '
                        f'{SHORT.get(k, "Reporting")}') for k in keys)
    return ('<div class="topbar">' + dots
            + chip(f'<i style="width:9px;height:9px;border-radius:50%;border:2px solid {COLORS["PV"]};display:inline-block"></i> rooftop PV')
            + chip(f'<i style="width:9px;height:9px;background:{TEXT};display:inline-block"></i> transformer')
            + chip("size = energy on the previous day") + "</div>")


def render(ctx, topo, sel=None):
    m = meter_states(ctx["scn"], ctx["c"], topo["meters"])
    keys = ["REPORTING", "OUTAGE", "UNCERTAIN", "COMMS_FAILURE"]
    m["shown"] = [SHORT.get(x, "Reporting") for x in m.state]
    names = [SHORT.get(k, "Reporting") for k in keys]
    ax = dict(axis=None, scale=alt.Scale(zero=False))
    lines = alt.Chart(topo["edges"]).mark_rule(color=COLORS["LINE"], strokeWidth=1.5).encode(
        x=alt.X("x:Q", **ax), y=alt.Y("y:Q", **ax), x2="x2:Q", y2="y2:Q")
    layers = [lines]
    if sel is not None:
        halo = m[m.group == sel["index"]]
        if len(halo):
            v = halo.state.iloc[0]
            layers.append(alt.Chart(halo).mark_circle(size=520, opacity=0.18, color=COLORS[v]).encode(x="x:Q", y="y:Q"))
            layers.append(alt.Chart(halo).mark_circle(size=240, opacity=0.25, color=COLORS[v]).encode(x="x:Q", y="y:Q"))
    pick = alt.selection_point(fields=["group"], name="pick")
    pts = alt.Chart(m).mark_circle(stroke=COLORS["PV"], opacity=0.95).encode(
        x="x:Q", y="y:Q",
        size=alt.Size("kwh:Q", scale=alt.Scale(range=[30, 260]), legend=None),
        color=alt.Color("shown:N", scale=alt.Scale(domain=names, range=[COLORS[k] for k in keys]), legend=None),
        strokeWidth=alt.condition("datum.pv", alt.value(2.2), alt.value(0)),
        tooltip=[alt.Tooltip("meter_id:N", title="meter"), alt.Tooltip("shown:N", title="state"),
                 alt.Tooltip("feeder:Q", title="feeder"), alt.Tooltip("pv_kw:Q", title="PV kW", format=".1f"),
                 alt.Tooltip("lag:Q", title="intervals since last reading"),
                 alt.Tooltip("voltage_v:Q", title="last voltage V", format=".1f")]).add_params(pick)
    layers.append(pts)
    if topo["transformer"]:
        tr = pd.DataFrame([{"x": topo["transformer"][0], "y": topo["transformer"][1]}])
        layers.append(alt.Chart(tr).mark_square(size=260, color=COLORS["TRANSFORMER"]).encode(x="x:Q", y="y:Q"))
    st.html(legend_html())
    ev = st.altair_chart(alt.layer(*layers).properties(height=460).configure_view(stroke=None), on_select="rerun",
                         key=f"net_{ctx['name']}", alt="LV network with meters coloured by state")
    st.caption("Lines and bus positions from the SimBench grid. Click a silent meter to select its group; "
               "only the selected group glows.")
    hit = [p.get("group") for p in ev.selection.get("pick", []) if p.get("group") is not None] if ev and ev.selection else []
    if hit:
        g = next((x for x in ctx["scn"]["groups"] if x["index"] == int(hit[0])), None)
        if g is not None and (sel is None or sel["index"] != g["index"]):
            ctx["select"](g)
            st.rerun()
