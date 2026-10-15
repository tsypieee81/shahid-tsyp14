"""V7: over-trust and under-trust instrumentation (proposal Section V-C).

Track record and override outcomes are computed from SIMULATED outcomes (results/demo/*_eval.json,
written by shahid.demo_eval). They stand in for field confirmations, which do not exist in Phase 1.
"""
import json

import altair as alt
import pandas as pd
import streamlit as st

import state
from theme import COLORS, GLYPH, SHORT, fmt_int, fmt_pct, icon


def outcomes():
    """(scenario, group index) -> simulated true cause, from every replayed scenario."""
    out = {}
    for f in sorted(state.DEMO.glob("*_eval.json")):
        name = f.name[: -len("_eval.json")]
        for i, g in enumerate(json.loads(f.read_text(encoding="utf8"))["group_truth"]):
            out[(name, i)] = (g["verdict"], g["truth"])
    return out


def track_record(oc):
    """Share of decided verdicts of each class that the simulated outcome confirms."""
    rows = []
    for k in ("OUTAGE", "COMMS_FAILURE"):
        v = [t for (verdict, t) in oc.values() if verdict == k]
        rows.append({"verdict": k, "decided": len(v), "confirmed": sum(t == k for t in v),
                     "share_confirmed": sum(t == k for t in v) / len(v) if v else None})
    return pd.DataFrame(rows)


def override_stats(entries, groups_by_hash, oc):
    acts = [e for e in entries if e["action"] in ("APPROVED", "OVERRIDDEN")]
    ov = [e for e in acts if e["action"] == "OVERRIDDEN"]
    res = []
    for e in ov:
        g = groups_by_hash.get(e["item"])
        if g:
            verdict, truth = oc.get((g["scenario"], g["index"]), (None, None))
            res.append({"onset": g["onset"][11:16], "verdict": verdict, "simulated outcome": truth,
                        "override was right": truth is not None and truth != verdict, "reason": e["reason"]})
    return {"rate": len(ov) / len(acts) if acts else None, "n": len(acts), "overrides": pd.DataFrame(res)}


CAPTION = "simulated outcomes standing in for field confirmations (decision 0007)"


def render(ctx):
    oc = outcomes()
    tr = track_record(oc)
    left, right = st.columns([1.4, 1], gap="small")
    with left, st.container(key="card_track"):
        st.html('<div class="micro">Track record per verdict class · all replayed scenarios</div>' + "".join(
            f'<div class="probrow" style="grid-template-columns:150px 1fr 150px"><span>{icon(GLYPH[r.verdict], COLORS[r.verdict])} '
            f'{SHORT[r.verdict]}</span><div class="bar"><i style="width:{0 if r.share_confirmed is None else 100 * r.share_confirmed}%;'
            f'background:{COLORS[r.verdict]}"></i></div><b>{fmt_int(r.confirmed)} confirmed of {fmt_int(r.decided)}</b></div>'
            for r in tr.itertuples()))
        st.caption(CAPTION)
        groups = {g["hash"]: g for g in ctx["scn"]["groups"]}
        o = override_stats(ctx["log"], groups, oc)
        st.html('<div class="micro" style="margin-top:10px">Overrides this session</div>'
                f'<div class="railcard">{fmt_pct(len(o["overrides"]), o["n"]) + " of approve or override actions" if o["n"] else "no approve or override action yet"}'
                '</div>')
        if len(o["overrides"]):
            st.dataframe(o["overrides"], hide_index=True, alt="Overrides with their simulated outcome")
    with right:
        with st.container(key="card_fast"):
            secs = pd.DataFrame([{"seconds": e["seconds"], "fast": e.get("fast", False)} for e in ctx["log"]
                                 if e["action"] == "APPROVED" and "seconds" in e], columns=["seconds", "fast"])
            st.html(f'<div class="micro">Approval time · under {fmt_int(ctx["fast_seconds"])} s flagged</div>')
            if len(secs):
                st.altair_chart(alt.Chart(secs).mark_bar().encode(
                    x=alt.X("seconds:Q", bin=alt.Bin(maxbins=20), title="seconds from opening the item to approval"),
                    y=alt.Y("count()", title=None),
                    color=alt.condition("datum.fast", alt.value(COLORS["OUTAGE"]), alt.value(COLORS["REPORTING"]))
                ).properties(height=140), alt="Approval-time distribution")
                st.caption(f"Fast approvals: {fmt_pct(int(secs.fast.sum()), len(secs))}")
            else:
                st.caption("No approval yet in this session.")
        with st.container(key="card_auditq"):
            q = state.queues(ctx["scn"], ctx["c"], ctx["log"])
            st.html(f'<div class="micro">Random audit sample · {fmt_pct(state.AUDIT_SHARE)} of automatic comms verdicts</div>'
                    f'<div class="railcard">{fmt_int(len(q["AUDIT"]))} pending at this replay time</div>')
            st.button("Open audit sample", icon=":material/fact_check:", on_click=ctx["goto"], args=("Queues",))
