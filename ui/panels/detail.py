"""V3: selected-item hero card — the method at one glance (expected vs visible energy, posterior scale,
explanation verbatim from shahid.explain, meta strip, operator actions)."""
import math

import altair as alt
import pandas as pd
import streamlit as st

import state
from theme import COLORS, FAINT, MUTED, SHORT, TEXT, chip, fmt_hm, fmt_int, fmt_kwh, fmt_num, fmt_p, icon, GLYPH

ACTIONS = [("Approve", "APPROVED", ":material/check:"), ("Override", "OVERRIDDEN", ":material/swap_horiz:"),
           ("Defer", "DEFERRED", ":material/schedule:"), ("Escalate to supervisor", "ESCALATED", ":material/supervisor_account:")]


def bars(g, lead=None):
    """Expected energy (spread if only data were lost) and visible energy at the transformer (spread
    if power were lost), at the decided lead or a given lead. kWh, as stored."""
    ev = g["leads"][g["decided_lead"] if lead is None else lead]
    return pd.DataFrame([
        {"what": "Expected if only data lost", "kwh": ev["M"], "lo": ev["M"] - ev["sd_C"], "hi": ev["M"] + ev["sd_C"],
         "spread": ev["sd_C"], "colour": COLORS["COMMS_FAILURE"]},
        {"what": "Visible at transformer", "kwh": ev["R"], "lo": ev["R"] - ev["sd_O"], "hi": ev["R"] + ev["sd_O"],
         "spread": ev["sd_O"], "colour": FAINT}])


def waterfall(g, thr, lead=None):
    """Log-odds of a communication failure: prior, likelihood ratio, posterior, and the band edges."""
    L = g["decided_lead"] if lead is None else lead
    post = g["leads"][L]["posterior_comms"]
    prior = math.log(thr["prior_comms"] / (1 - thr["prior_comms"]))
    edge = math.log((1 - thr["abstain_band"]) / thr["abstain_band"])
    llr = g["leads"][L]["llr"]
    return {"prior_logodds": prior, "llr": llr, "posterior": post, "lead": L,
            "posterior_logodds": None if llr is None else prior + llr, "band_edge_logodds": edge}


def accumulation(g):
    return pd.DataFrame([{"lead": x["lead"], "R": x["R"], "M": x["M"], "M_lo": x["M"] - x["sd_C"],
                          "M_hi": x["M"] + x["sd_C"], "posterior_comms": x["posterior_comms"]} for x in g["leads"]])


def resolution(g, limit):
    """Signal-to-noise of the group at its decided lead, as in the resolution-limit analysis
    (expected silent energy / its predictive sd); below the measured limit = not resolvable."""
    ev = g["leads"][g["decided_lead"]]
    sd = math.sqrt(max(ev["sd_C"] ** 2 - ev["sd_O"] ** 2, 0.0))
    snr = abs(ev["M"]) / sd if sd else float("inf")
    return {"snr": snr, "limit": limit, "below": snr < limit}


def whiskers(b):
    """Two whisker bars on one shared kWh scale (mean marker, one spread each side, zero rule)."""
    y = alt.Y("what:N", sort=None, axis=None)
    base = alt.Chart(b)
    ch = (alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=COLORS["OUTAGE"], strokeDash=[3, 3]).encode(x="x:Q")
          + base.mark_rule(strokeWidth=6, opacity=0.45).encode(
              y=y, x=alt.X("lo:Q", title=None, axis=alt.Axis(labelColor=MUTED, gridColor="#1a2438", tickCount=4,
                                                             domainColor="#1e293b", format=".1f")),
              x2="hi:Q", color=alt.Color("colour:N", scale=None))
          + base.mark_tick(thickness=3, size=16).encode(y=y, x="kwh:Q", color=alt.value(TEXT)))
    return ch.properties(height=64, padding={"left": 6, "right": 18, "top": 4, "bottom": 2}).configure_view(stroke=None)


def pscale(p, band):
    if p is None:
        return '<div class="scale-ends"><span>posterior not computed: expected energy too small for the balance</span></div>'
    lo, hi = band * 100, (1 - band) * 100
    return (f'<div class="scale"><div class="band" style="left:{lo}%;width:{hi - lo}%"></div>'
            f'<div class="mk" style="left:calc({p * 100}% - 2px)"></div></div>'
            '<div class="scale-ends"><span>0 · outage</span><span>abstention band</span><span>comms failure · 1</span></div>')


def header(scn, g, c):
    final = state.status(g, c) == "decided"
    v = g["verdict"] if final else "UNCERTAIN"
    f = state.feeder_of(scn, g)
    where = f"feeder {fmt_int(f)}" if f is not None else "several feeders"
    title = {"OUTAGE": "Outage verdict", "UNCERTAIN": "Uncertain — abstained", "COMMS_FAILURE": "Communication-failure verdict"}[v]
    if not final:
        title = "Evidence accumulating"
    st_chip = chip("decided", f"chip-{v}") if final else chip("forming", "chip-amber")
    return v, (f'<div class="feed-row"><div class="feed-icon">{icon(GLYPH[v], COLORS[v], 20)}</div><div>'
               f'<div style="font-size:16px;font-weight:650;color:{TEXT}">{title} {st_chip}</div>'
               f'<div class="kpi-sub" style="margin-top:2px">{fmt_int(g["n_meters"])} m · {where} · {fmt_hm(g["onset"])}</div>'
               '</div></div>')


def render(ctx, g):
    """Hero card for group g, or None when nothing is selected (the caller shows grid health instead)."""
    scn, c, thr = ctx["scn"], ctx["c"], ctx["thr"]
    final = state.status(g, c) == "decided"
    lead = None if final else state.lead_at(g, c)
    L = g["decided_lead"] if final else lead
    ev = g["leads"][L]
    v, head = header(scn, g, c)
    with st.container(key=f"card_hero_{v}_{g['index']}"):
        st.html(head)
        a, b = st.columns(2)
        a.html(f'<div class="micro">Expected if only data lost</div><div class="hero-num" style="color:{COLORS["COMMS_FAILURE"]}">'
               f'{fmt_kwh(ev["M"], False)}<span class="unit">kWh ± {fmt_num(ev["sd_C"])}</span></div>')
        b.html(f'<div class="micro">Visible at transformer</div><div class="hero-num">'
               f'{fmt_kwh(ev["R"], False)}<span class="unit">kWh ± {fmt_num(ev["sd_O"])}</span></div>')
        st.altair_chart(whiskers(bars(g, L)), alt="Expected and visible energy with one spread each")
        w = waterfall(g, thr, L)
        st.html(f'<div class="micro">Probability of a communication failure · {fmt_p(w["posterior"])}</div>'
                + pscale(w["posterior"], thr["abstain_band"]))
        st.caption(f"prior {fmt_num(thr['prior_comms'])} · log-LR {fmt_num(w['llr'])} · "
                   + (f"decided at lead {fmt_int(L)}" if final else f"lead {fmt_int(L)} of {fmt_int(state.L_MAX)}, not final"))
        st.markdown(g["explanation"] if final else "The explanation is issued when the verdict is final.")
        rec = g["record"]
        if final and rec.get("runner_up") and rec.get("probability") is not None:
            st.caption(f"Alternative cause considered: {SHORT[rec['runner_up']]}, probability {fmt_p(1 - rec['probability'])}")
        esc = g["escalation"]
        st.html('<div class="meta-strip">'
                f'<div><span>Onset</span><b>{fmt_hm(g["onset"])}</b></div>'
                f'<div><span>Decided</span><b>{fmt_hm(g["decided_i"]) if final else "pending"}</b></div>'
                f'<div><span>Handled</span><b>{"human" if esc["handled_by"] == "HUMAN" else "automatic"}</b></div>'
                f'<div><span>Rule</span><b title="{esc["action"]}">{esc["rule"].split("-")[0]}</b></div></div>')
        r = resolution(g, ctx["snr_limit"])
        if final and r["below"]:
            st.warning(f"Signal-to-noise {fmt_num(r['snr'], 1)} is below the measured resolution limit "
                       f"({fmt_num(r['limit'], 1)}, Section VI-D): in simulation the balance gives the right cause less "
                       "than 90% of the time at this level. Treat the verdict with extra care.", icon=":material/visibility_off:")
        if final and "act" in ctx:
            st.text_input("Reason (required to override)", key=f"reason_{g['hash']}",
                                   placeholder="Reason (required to override)", label_visibility="collapsed")
            with st.container(horizontal=True, gap="small"):
                for label, action, ic in ACTIONS:
                    st.button(label, icon=ic, key=f"{action}_{g['hash']}", on_click=ctx["act"],
                              args=(g, action), kwargs={"reason_key": f"reason_{g['hash']}"},
                              type="primary" if action == "APPROVED" else "secondary")
            if ctx.get("act_error"):
                st.warning(ctx["act_error"])
