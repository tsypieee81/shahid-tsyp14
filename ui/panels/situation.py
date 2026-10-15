"""V1: situation (landing). KPI strip, grid-balance hero, analytics rail, event feed, selected item or grid health."""
import altair as alt
import pandas as pd
import streamlit as st

import state
from panels import detail, trace
from theme import (COLORS, DELTA, DELTA_BACK, GLYPH, SHORT, TEXT, VERDICTS, chip, fmt_hm, fmt_int,
                   fmt_kwh, fmt_num, fmt_p, fmt_pct, fmt_signed)

KPI_H = 178


def strip(scn, c):
    """Onset markers of the silent groups visible at cursor c, coloured by their state."""
    return pd.DataFrame([{"time": state.time_of(scn, g["onset_i"]), "meters": g["n_meters"],
                          "state": g["verdict"] if state.status(g, c) == "decided" else "UNCERTAIN",
                          "index": g["index"]} for g in state.visible(scn, c)],
                        columns=["time", "meters", "state", "index"])


def _delta(now, before, kind):
    d = now - before
    return (None if d == 0 else fmt_signed(d)), DELTA[kind]


def kpi_strip(ctx, k):
    cols = st.columns(6, gap="small")
    ago = f"Δ vs {fmt_int(DELTA_BACK * 15 // 60)} h ago"
    subs = {"OUTAGE": f"awaiting approval · of {fmt_int(k['decided'])} decided",
            "UNCERTAIN": f"abstained · accumulating {fmt_int(k['forming'])}",
            "COMMS_FAILURE": f"unconfirmed · re-check {fmt_int(k['recheck'])}"}
    names = {"OUTAGE": "Outages", "UNCERTAIN": "Uncertain", "COMMS_FAILURE": "Comms"}
    for col, key in zip(cols, VERDICTS):
        with col, st.container(key=f"kpi_{key}", height=KPI_H):
            d, dc = _delta(k["queue"][key], k["queue_before"][key], key)
            st.metric(names[key], fmt_int(k["queue"][key]), d, delta_color=dc, help=ago)
            st.html(f'<div class="kpi-sub">{subs[key]}{" · " + ago if d else ""}</div>')
    with cols[3], st.container(key="kpi_abstain", height=KPI_H):
        share = k["abstained"] / k["decided"] if k["decided"] else None
        st.metric("Abstention", fmt_pct(share), chart_data=k["share_series"] or None, chart_type="area")
        st.html(f'<div class="kpi-sub">{fmt_int(k["abstained"])} of {fmt_int(k["decided"])} groups · '
                f'band {fmt_num(ctx["thr"]["abstain_band"])}</div>')
    with cols[4], st.container(key="kpi_latency", height=KPI_H):
        st.metric("Latency", fmt_int(k["latency_median"], "int"), help="median decision latency",
                  chart_data=k["latency_series"] or None, chart_type="bar")
        iqr = (f"IQR {fmt_int(k['latency_q1'])}–{fmt_int(k['latency_q3'])}" if k["latency_median"] is not None else "no decisions yet")
        st.html(f'<div class="kpi-sub">{iqr} · window {fmt_int(state.K)}–{fmt_int(state.K + state.L_MAX)}</div>')
    with cols[5], st.container(key="kpi_reporting", height=KPI_H):
        d, dc = _delta(k["reporting"], k["reporting_before"], "reporting")
        st.metric("Reporting", f"{fmt_int(k['reporting'])}/{fmt_int(k['n_meters'])}", d, delta_color=dc,
                  help=f"meters reporting; {ago}", chart_data=k["reporting_series"][-24:] or None)
        st.html(f'<div class="kpi-sub">missing {fmt_int(k["n_meters"] - k["reporting"])} · late {fmt_int(k["late"])} · '
                f'outstanding {fmt_int(k["outstanding"])}</div>')


def gauge(share, k, n):
    v = 0 if share is None else share
    bg = pd.DataFrame({"t": [1.0]})
    fg = pd.DataFrame({"t": [v]})
    th = alt.Theta("t:Q", scale=alt.Scale(domain=[0, 1]), stack=False)
    ch = (alt.Chart(bg).mark_arc(innerRadius=46, outerRadius=58, color="#1e293b", theta=0, theta2=6.2832).encode()
          + alt.Chart(fg).mark_arc(innerRadius=46, outerRadius=58, cornerRadius=4, color=COLORS["UNCERTAIN"]).encode(theta=th)
          + alt.Chart(pd.DataFrame({"s": [fmt_pct(share)]})).mark_text(fontSize=22, fontWeight=600, color=TEXT).encode(text="s:N"))
    return ch.properties(height=130, width=130).configure_view(stroke=None)


def matrix_html(m):
    rows = "".join(f'<div>{chip(SHORT[k], "chip-" + k)}</div><div><b>{fmt_int(m[k]["awaiting"])}</b></div>'
                   f'<div><b>{fmt_int(m[k]["resolved"])}</b></div>' for k in VERDICTS)
    return f'<div class="vm"><div></div><div class="micro">awaiting</div><div class="micro">resolved</div>{rows}</div>'


def confidence_html(q, c):
    out = []
    for k in VERDICTS:
        ps = [p for p in (state.strength(g, c) for g in q[k]) if p is not None]
        m = sum(ps) / len(ps) if ps else None
        lab = {"OUTAGE": "P(outage)", "UNCERTAIN": "P(comms)", "COMMS_FAILURE": "P(comms)"}[k]
        name = {"OUTAGE": "Outage", "UNCERTAIN": "Uncertain", "COMMS_FAILURE": "Comms"}[k]
        w = 0 if m is None else 100 * m
        out.append(f'<div class="probrow"><span>{name} · {lab}</span><div class="bar"><i style="width:{w}%;'
                   f'background:{COLORS[k]}"></i></div><b>{fmt_pct(m) if m is not None else "—"}</b></div>')
    return "".join(out)


def tickbar_html(scn, c):
    dec = sorted((g for g in state.visible(scn, c) if state.status(g, c) == "decided"), key=lambda g: g["decided_i"])
    ticks = "".join(f'<i title="{fmt_hm(g["decided_i"])} {SHORT[g["verdict"]]}" style="background:'
                    f'{COLORS["ABSTAIN"] if g["verdict"] == "UNCERTAIN" else COLORS[g["verdict"]]}"></i>' for g in dec)
    return f'<div class="tickbar">{ticks or "<span class=kpi-sub>no decisions yet</span>"}</div>'


def rail(ctx, k):
    scn, c = ctx["scn"], ctx["c"]
    q = state.queues(scn, c, ctx["log"])
    with st.container(key="card_rail_a"):
        a, b = st.columns([1, 1.15], vertical_alignment="center")
        with a:
            share = k["abstained"] / k["decided"] if k["decided"] else None
            st.altair_chart(gauge(share, k["abstained"], k["decided"]), alt="Abstention share today")
        with b:
            st.html('<div class="micro">Abstention today</div>'
                    f'<div class="railcard">{fmt_int(k["abstained"])} of {fmt_int(k["decided"])} decided groups</div>'
                    f'<div class="kpi-sub" style="margin-top:4px">abstain when {fmt_num(ctx["thr"]["abstain_band"])} &lt; '
                    f'P(comms) &lt; {fmt_num(1 - ctx["thr"]["abstain_band"])}</div>')
    with st.container(key="card_rail_b"):
        st.html('<div class="micro">Verdict matrix</div>' + matrix_html(state.matrix(scn, c, ctx["log"])))
    with st.container(key="card_rail_c"):
        st.html('<div class="micro">Open-item confidence</div>' + confidence_html(q, c)
                + '<div class="kpi-sub" style="margin-top:6px">current evidence strength, not validated accuracy</div>')
    with st.container(key="card_rail_d"):
        st.html('<div class="micro">Decisions today</div>' + tickbar_html(scn, c)
                + '<div class="kpi-sub" style="margin-top:6px">one tick per decision in time order; grey = abstained</div>')


def feed_items(scn, c, log):
    done = state.closed(log)
    vis = sorted(state.visible(scn, c), key=lambda g: (g["onset_i"], g["index"]), reverse=True)
    out = []
    for g in vis:
        dec = state.status(g, c) == "decided"
        v = g["verdict"] if dec else "UNCERTAIN"
        p = g["leads"][g["decided_lead"] if dec else state.lead_at(g, c)]["posterior_comms"]
        f = state.feeder_of(scn, g)
        title = (f"{fmt_int(g['n_meters'])} m silent — {SHORT[v] if dec else 'evidence accumulating'}"
                 + (f" · P(comms) {fmt_p(p)}" if p is not None else ""))
        sub = " · ".join([fmt_hm(g["onset"]), f"feeder {fmt_int(f)}" if f is not None else "several feeders",
                          ("to human" if g["escalation"]["handled_by"] == "HUMAN" else "automatic") if dec else "forming",
                          g["escalation"]["rule"].split("-")[0]] + (["closed"] if g["hash"] in done else []))
        out.append({"g": g, "v": v, "title": title, "sub": sub, "active": g["hash"] not in done})
    return out


def feed(ctx, sel):
    items = feed_items(ctx["scn"], ctx["c"], ctx["log"])
    with st.container(key="card_feed"):
        st.html(f'<div class="topbar"><span class="micro" style="margin:0">Event feed</span>'
                f'{chip(fmt_int(sum(i["active"] for i in items)) + " active")}</div>')
        if not items:
            st.caption("No silent group yet at this replay time.")
        for it in items[:12]:
            g = it["g"]
            on = sel is not None and sel["index"] == g["index"]
            st.button(f":material/{GLYPH[it['v']]}: **{it['title']}**   :gray[{it['sub']}]",
                      key=f"{'feedsel' if on else 'feed'}_{g['index']}", on_click=ctx["select"], args=(g,), width="stretch")


def health(ctx, k):
    scn, c = ctx["scn"], ctx["c"]
    s = state.stats_at(scn, c)
    gap = scn["trace"][c - 1]["gap_kwh"] if c > 0 else None
    base, sd = scn.get("gap_baseline_kwh"), scn.get("gap_sd_kwh")
    fast = sum(bool(e.get("fast")) for e in ctx["log"])
    with st.container(key="card_health"):
        st.html('<div class="micro">Grid health · nothing selected</div>'
                '<div class="meta-strip" style="grid-template-columns:repeat(2,1fr);border-top:none;margin-top:0">'
                f'<div><span>Gap now</span><b>{fmt_kwh(gap)} ± {fmt_num(sd, 3)}</b></div>'
                f'<div><span>Gap baseline</span><b>{fmt_kwh(base)}</b></div></div>'
                '<div class="meta-strip" style="grid-template-columns:repeat(3,1fr)">'
                f'<div><span>Outstanding</span><b>{fmt_int(s["n_outstanding"])}</b></div>'
                f'<div><span>Late today</span><b>{fmt_int(s["n_late"])}</b></div>'
                f'<div><span>Link</span><b style="color:{COLORS["UNCERTAIN"]}">simulated replay</b></div></div>'
                '<div class="meta-strip" style="grid-template-columns:repeat(3,1fr)">'
                f'<div><span>Decided</span><b>{fmt_int(k["decided"])}</b></div>'
                f'<div><span>Audit pending</span><b>{fmt_int(k["audit"])}</b></div>'
                f'<div><span>Fast approvals</span><b>{fmt_int(fast)}</b></div></div>')
        st.caption("Gap: transformer minus reporting meters, with its fitted per-interval spread; baseline: median gap of "
                   "the previous day. Select an item in the event feed, a queue or the network to see its evidence.")


def render(ctx, sel):
    scn, c = ctx["scn"], ctx["c"]
    k = state.kpis(scn, c, ctx["log"])
    kpi_strip(ctx, k)
    left, right = st.columns([2.3, 1], gap="small")  # one row: no void when the rail and the hero differ in height
    with left:
        with st.container(key="card_hero_chart"):
            st.html('<div class="micro">Grid balance — replayed day</div>')
            ch, shown = trace.chart(scn, c, sel, height=300)
            st.html(trace.legend(shown))
            st.altair_chart(ch, alt="Grid balance over the replayed day with the communication-failure hypothesis")
            st.caption(trace.CAPTION)
        feed(ctx, sel)
    with right:
        if sel is not None:
            detail.render(ctx, sel)
        rail(ctx, k)
        if sel is None:
            health(ctx, k)
