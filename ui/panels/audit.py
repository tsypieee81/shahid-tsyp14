"""V6: the hash-chained operator log, chain verification and a tamper test."""
import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

import oplog
from theme import chip, fmt_hm, fmt_int


def verify_text(text):
    """Verify a log given as text (the tamper test edits a copy, never the log file)."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "log.jsonl"
        p.write_text(text if text.endswith("\n") or not text else text + "\n", encoding="utf8")
        try:
            return oplog.verify_log(p)
        except (json.JSONDecodeError, KeyError):
            return False, "unreadable line"


def table(entries):
    rows = [{"time": fmt_hm(pd.Timestamp(e["timestamp"]).tz_convert(None)), "action": e["action"].lower(),
             "user": e["user"], "hash": e["hash"][:10] + "…", "reason": e.get("reason", ""),
             "fast": "fast approval" if e.get("fast") else ""} for e in entries]
    return pd.DataFrame(rows, columns=["time", "action", "user", "hash", "reason", "fast"])


def chain_state(path, entries):
    ok, bad = oplog.verify_log(path) if entries else (True, None)
    return ok, bad


def render(ctx):
    entries = ctx["log"]
    ok, bad = chain_state(ctx["oplog_path"], entries)
    head = entries[-1]["hash"][:10] + "…" if entries else "genesis"
    st.html('<div class="topbar">'
            + (chip(f"chain intact · {fmt_int(len(entries))}", "chip-ok") if ok else chip(f"chain broken at line {fmt_int(bad)}", "chip-bad"))
            + chip(f"head {head}") + chip("append-only · SHA-256, same chaining as the decision log") + "</div>")
    with st.container(key="card_audit"):
        if entries:
            st.dataframe(table(entries), hide_index=True, alt="Operator log", width="stretch")
        else:
            st.markdown(":material/receipt_long: **No operator action yet in this session.**")
            st.caption("Approve, override, defer or escalate an item; each action is appended here with the time it took.")
        if st.button("Verify chain", icon=":material/verified:"):
            (st.success if ok else st.error)("Chain intact" if ok else f"Chain broken at line {fmt_int(bad)}")
    with st.expander("Tamper test — edit a copy of the log, then verify", icon=":material/gpp_maybe:"):
        text = "\n".join(json.dumps(e, sort_keys=True) for e in entries)
        edited = st.text_area("Copy of the operator log", text, height=160, key="tamper")
        if st.button("Verify edited copy", icon=":material/gpp_maybe:"):
            ok2, bad2 = verify_text(edited) if edited.strip() else (True, None)
            (st.success if ok2 else st.error)("Copy verifies: no change detected" if ok2
                                              else f"Verification fails at line {bad2}: the edit is detected")
