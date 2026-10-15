"""V2: the three queues, never merged, and the separate audit sample."""
import pandas as pd
import streamlit as st

import state
from theme import ICONS, TABS, fmt_int, fmt_p, fmt_pct

EMPTY = {"OUTAGE": "No outage verdict is waiting for approval.",
         "UNCERTAIN": "No abstained group is waiting for a person.",
         "COMMS_FAILURE": "No communication-failure verdict is waiting for confirmation.",
         "AUDIT": "No automatically handled communication verdict fell into the random audit sample."}


def rows(items, c, escalation):
    return pd.DataFrame([{"onset": pd.Timestamp(g["onset"]).to_pydatetime(), "meters": g["n_meters"],
                          "p_comms": fmt_p(g["posterior_comms"]),
                          "evidence": [x["R"] for x in g["leads"]],
                          "waiting": c - g["decided_i"],
                          "handled_by": "human" if g["escalation"]["handled_by"] == "HUMAN" else "automatic",
                          "status": "re-check pending" if state.recheck_pending(g, c, escalation) else "open"}
                         for g in items],
                        columns=["onset", "meters", "p_comms", "evidence", "waiting", "handled_by", "status"])


COLUMNS = {
    "onset": st.column_config.DatetimeColumn("Onset", format="HH:mm"),
    "meters": st.column_config.NumberColumn("Meters", format="%d"),
    "p_comms": st.column_config.TextColumn("P(comms)"),  # fmt_p text: never a rounded 1.000
    "evidence": st.column_config.LineChartColumn("Visible energy by lead"),
    "waiting": st.column_config.NumberColumn("Waiting", format="%d int"),
    "handled_by": st.column_config.TextColumn("Handled by"),
    "status": st.column_config.TextColumn("Status"),
}


def render(ctx):
    scn, c = ctx["scn"], ctx["c"]
    q = state.queues(scn, c, ctx["log"])
    decided = sum(state.status(g, c) == "decided" for g in scn["groups"])
    keys = (*state.QUEUE_ORDER, "AUDIT")
    picked = ctx.get("selected")
    tabs = st.tabs([f"{ICONS[k]} {TABS[k]} · {fmt_int(len(q[k]))}" for k in keys])
    for tab, key in zip(tabs, keys):
        with tab:
            if key == "AUDIT":
                st.caption(f"A random {fmt_pct(state.AUDIT_SHARE)} of automatically handled communication verdicts, "
                           "kept apart from the three queues (over-trust check).")
            if not q[key]:
                with st.container(key=f"card_empty_{key}"):
                    st.markdown(f":material/inbox: **{EMPTY[key]}**")
                    st.caption(f"{fmt_int(decided)} groups decided by this replay time; "
                               f"{fmt_int(len(q[key]))} of them open here. Items leave a queue when approved, "
                               "overridden or escalated.")
                continue
            sel = st.dataframe(rows(q[key], c, ctx["escalation"]), hide_index=True, column_config=COLUMNS,
                               on_select="rerun", selection_mode="single-row", key=f"q_{key}_{ctx['name']}",
                               alt=f"{TABS[key]} queue")
            # the grid keeps its old row index after the selected item leaves the queue: ignore it then
            if sel.selection.rows and sel.selection.rows[0] < len(q[key]):
                picked = q[key][sel.selection.rows[0]]
                ctx["select"](picked)
    from panels import trace  # the balance behind the selected item, below the queue
    with st.container(key="card_queue_trace"):
        st.html('<div class="micro">Grid balance — selected item</div>')
        ch, shown = trace.chart(scn, c, picked, height=260)
        st.html(trace.legend(shown))
        st.altair_chart(ch, alt="Grid balance behind the selected queue item")
        st.caption(trace.CAPTION)
