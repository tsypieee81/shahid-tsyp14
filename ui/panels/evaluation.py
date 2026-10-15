"""V8: SIMULATION EVALUATION (decision 0007). Verdicts of the replayed day against simulation labels.

Strictly separate from the operator path: imports nothing from shahid.detect, reads only
results/demo/<scenario>_eval.json (shahid.demo_eval), and is reached only through an explicit toggle.
"""
import json

import pandas as pd
import streamlit as st

import state
from theme import fmt_num


def load_eval(name):
    return json.loads((state.DEMO / f"{name}_eval.json").read_text(encoding="utf8"))


def confusion(ev):
    g = pd.DataFrame(ev["group_truth"], columns=["onset", "n_meters", "verdict", "truth"])
    return pd.crosstab(g.truth, g.verdict) if len(g) else pd.DataFrame()


def episode_summary(ev):
    e = pd.DataFrame(ev["episodes"], columns=["cause", "start", "n_meters", "verdict"])
    dec = e.verdict.isin(["OUTAGE", "COMMS_FAILURE"])
    return {"episodes": len(e), "decided": int(dec.sum()),
            "coverage": dec.mean() if len(e) else None,
            "false_outage": int(((e.cause == "COMMS_FAILURE") & (e.verdict == "OUTAGE")).sum()),
            "missed_outage": int(((e.cause == "OUTAGE") & e.verdict.isin(["COMMS_FAILURE", "MISSED"])).sum()),
            "table": e}


def render(ctx):
    st.error("SIMULATION EVALUATION — labels are not available to the detector. This view is an evaluation "
             "tool, not part of the operator path.", icon=":material/science:")
    ev = load_eval(ctx["name"])
    s = episode_summary(ev)
    with st.container(horizontal=True):
        st.metric("Labelled episodes today", s["episodes"])
        st.metric("Decided", s["decided"])
        st.metric("Coverage", fmt_num(s["coverage"]))
        st.metric("False outages", s["false_outage"])
        st.metric("Missed outages", s["missed_outage"])
    st.dataframe(s["table"], hide_index=True, alt="Labelled episodes with the verdict each received")
    st.markdown("**Every silent group of the day: simulated cause (rows) against verdict (columns)**")
    st.dataframe(confusion(ev), alt="Confusion of the replayed day")
    st.caption("One day, one scenario: these counts illustrate behaviour and are not results. The measured rates "
               "are in the proposal (Section VI) and docs/RESULTS.md.")
