"""Pure logic of the operator UI preview (no Streamlit): scenario loading, replay cursor, queues.

A scenario is the stored replay of one simulated day (results/demo/<name>.json, shahid.demo_day).
The cursor c is the number of 15-minute intervals elapsed in the day. A silent group with onset
interval o becomes visible at o + K (the detector's silence rule) and shows its evidence at lead
min(c - o - K, L_max); its verdict is final once c >= o + K + decided_lead.
"""
import functools
import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "results" / "demo"
K, L_MAX, INTERVALS = 2, 4, 96
AUDIT_SHARE = 0.2      # DESIGN CHOICE (A-UI-AUDIT): share of automatic comms closures sent to audit
QUEUE_ORDER = ("OUTAGE", "UNCERTAIN", "COMMS_FAILURE")


def scenarios():
    d = yaml.safe_load(open(ROOT / "configs" / "demo_scenarios.yaml", encoding="utf8"))
    return {k: v["description"] for k, v in d["scenarios"].items() if (DEMO / f"{k}.json").exists()}


def load(name):
    scn = json.loads((DEMO / f"{name}.json").read_text(encoding="utf8"))
    log = [json.loads(x) for x in (DEMO / f"{name}_log.jsonl").read_text(encoding="utf8").splitlines()]
    day0 = pd.Timestamp(scn["trace"][0]["interval_start"])
    for i, (g, entry) in enumerate(zip(scn["groups"], log)):
        g["index"], g["hash"], g["scenario"] = i, entry["hash"], name
        g["onset_i"] = int((pd.Timestamp(g["onset"]) - day0) / pd.Timedelta(minutes=15))
        g["decided_i"] = g["onset_i"] + K + g["decided_lead"]
    scn["day0"] = day0
    return scn


def thresholds():
    p = json.loads((ROOT / "results" / "detector_params.json").read_text(encoding="utf8"))
    return {"abstain_band": p["thresholds"]["bayes"]["abstain_band"],
            "prior_comms": p["fitted"]["prior_comms"]}


def resolution_snr():
    """Measured resolution limit (SNR at P(correct) = 0.9, nominal development cell, ledger CP10-T3)."""
    b = json.loads((ROOT / "results" / "cp10.json").read_text(encoding="utf8"))["boundary"]
    return b["cp6_nominal"]["snr"]["x90_logistic"]


def time_of(scn, i):
    return scn["day0"] + pd.Timedelta(minutes=15 * i)


def status(g, c):
    """'hidden', 'forming' (evidence accumulating) or 'decided' at cursor c."""
    if c < g["onset_i"] + K:
        return "hidden"
    return "decided" if c >= g["decided_i"] else "forming"


def lead_at(g, c):
    return max(0, min(c - g["onset_i"] - K, L_MAX))


def visible(scn, c):
    return [g for g in scn["groups"] if status(g, c) != "hidden"]


def acted(oplog_entries):
    """Item hash -> last operator action."""
    out = {}
    for a in oplog_entries:
        out[a["item"]] = a["action"]
    return out


def in_audit_sample(g, share=AUDIT_SHARE):
    """Deterministic sample of automatically handled comms verdicts (by record hash)."""
    return (g["verdict"] == "COMMS_FAILURE" and g["escalation"]["handled_by"] == "AUTOMATED"
            and int(g["hash"][:8], 16) % 100 < share * 100)


def recheck_pending(g, c, escalation):
    rule = next((r for r in escalation["rules"] if r["id"] == g["escalation"]["rule"]), {})
    n = rule.get("recheck_after_intervals")
    return bool(n) and c < g["decided_i"] + n


def queues(scn, c, oplog_entries):
    """The three queues, never merged, plus the separate audit sample. Decided, un-closed items only."""
    done = {h for h, a in acted(oplog_entries).items() if a in ("APPROVED", "OVERRIDDEN", "ESCALATED")}
    q = {k: [] for k in (*QUEUE_ORDER, "AUDIT")}
    for g in visible(scn, c):
        if status(g, c) != "decided" or g["hash"] in done:
            continue
        q[g["verdict"]].append(g)
        if in_audit_sample(g):
            q["AUDIT"].append(g)
    return q


def tally(scn, c):
    dec = [g for g in visible(scn, c) if status(g, c) == "decided"]
    counts = {k: sum(g["verdict"] == k for g in dec) for k in QUEUE_ORDER}
    lat = sorted(g["decided_lead"] + K for g in dec)
    return {"counts": counts, "decided": len(dec),
            "abstention_share": counts["UNCERTAIN"] / len(dec) if dec else None,
            "median_latency": lat[len(lat) // 2] if lat else None,
            "forming": sum(status(g, c) == "forming" for g in scn["groups"])}


# ---- console redesign (phase2-dashboard-v2): everything below is derived from the replay files ---------------
def spec(name):
    """Scenario entry of configs/demo_scenarios.yaml: description, shows, default_cursor."""
    d = yaml.safe_load(open(ROOT / "configs" / "demo_scenarios.yaml", encoding="utf8"))["scenarios"][name]
    return {"description": d["description"], "shows": d.get("shows", []),
            "default_cursor": int(d.get("default_cursor", 40))}


def feeder_of(scn, g):
    """Feeder index shared by the group's meters (network topology), or None when they span feeders."""
    f = {scn["feeder"][scn["meter_id"].index(m)] for m in g["meters"]}
    return f.pop() if len(f) == 1 and -1 not in f else None


def closed(log):
    return {h for h, a in acted(log).items() if a in ("APPROVED", "OVERRIDDEN", "ESCALATED")}


def stats_at(scn, c):
    """Reporting counts known at replay time c (results/demo trace, shahid.demo_day.cursor_stats)."""
    return scn["trace"][max(0, min(c, INTERVALS - 1))]


def kpis(scn, c, log):
    """Values of the six KPI tiles at replay time c, with the 1-hour-earlier comparator where defined."""
    q, q0 = queues(scn, c, log), queues(scn, max(c - 4, 0), log)
    dec = sorted((g for g in visible(scn, c) if status(g, c) == "decided"), key=lambda g: g["decided_i"])
    lat = sorted(g["decided_lead"] + K for g in dec)
    share, k = [], 0
    for i, g in enumerate(dec, 1):  # abstention share after each decision, in time order
        k += g["verdict"] == "UNCERTAIN"
        share.append(k / i)
    s, s0 = stats_at(scn, c), stats_at(scn, max(c - 4, 0))
    quart = (lambda p: lat[min(len(lat) - 1, int(p * len(lat)))]) if lat else (lambda p: None)
    return {"queue": {key: len(q[key]) for key in QUEUE_ORDER}, "queue_before": {key: len(q0[key]) for key in QUEUE_ORDER},
            "decided": len(dec), "abstained": k, "share_series": share,
            "forming": sum(status(g, c) == "forming" for g in scn["groups"]),
            "recheck": sum(recheck_pending(g, c, escalation()) for g in q["COMMS_FAILURE"]),
            "latency_median": quart(0.5), "latency_q1": quart(0.25), "latency_q3": quart(0.75),
            "latency_series": [g["decided_lead"] + K for g in dec],
            "n_meters": scn["n_meters"], "reporting": s["n_reporting"], "reporting_before": s0["n_reporting"],
            "late": s["n_late"], "outstanding": s["n_outstanding"],
            "reporting_series": [t["n_reporting"] for t in scn["trace"][: c + 1]],
            "audit": len(q["AUDIT"])}


@functools.lru_cache(1)
def escalation():
    from shahid.explain import load_escalation
    return load_escalation(ROOT / "configs" / "escalation.yaml")


def matrix(scn, c, log):
    """Decided items per class: awaiting (open in a queue) and resolved (closed by an operator action)."""
    done = closed(log)
    dec = [g for g in visible(scn, c) if status(g, c) == "decided"]
    return {k: {"awaiting": sum(g["verdict"] == k and g["hash"] not in done for g in dec),
                "resolved": sum(g["verdict"] == k and g["hash"] in done for g in dec)} for k in QUEUE_ORDER}


def strength(g, c):
    """Current evidence strength for the group's own verdict: P(outage), P(comms), or P(comms) when uncertain."""
    p = g["leads"][g["decided_lead"] if status(g, c) == "decided" else lead_at(g, c)]["posterior_comms"]
    return None if p is None else (1 - p if g["verdict"] == "OUTAGE" and status(g, c) == "decided" else p)


def meter_view(scn, c):
    """Per meter at replay time c: intervals since its last known reading (lag) and its last voltage."""
    rel, V = scn["arrival"], scn["voltage_v"]
    out = []
    for m in range(scn["n_meters"]):
        s = next((s for s in range(c - 1, -1, -1) if 0 <= rel[s][m] <= c), None)
        out.append({"lag": c - 1 - s if s is not None else c, "voltage_v": V[s][m] if s is not None else None})
    return out


def jump(scn, text):
    """Jump-search: a meter id ('m042'), a group number ('7' or '#7') or a time ('hh:mm').
    Returns (group or None, cursor or None, hint)."""
    t = (text or "").strip().lower().lstrip("#")
    if not t:
        return None, None, ""
    if t.startswith("m") and t[1:].isdigit():
        mid = f"m{int(t[1:]):03d}"
        if mid not in scn["meter_id"]:
            return None, None, f"no meter {mid} on this grid"
        hits = [g for g in scn["groups"] if mid in g["meters"]]
        if not hits:
            return None, None, f"{mid} was never silent on this day"
        g = hits[-1]
        return g, g["onset_i"] + K, ""
    if t.isdigit():
        i = int(t)
        g = next((x for x in scn["groups"] if x["index"] == i), None)
        return (g, g["onset_i"] + K, "") if g else (None, None, f"no silent group {i} (0 to {len(scn['groups']) - 1})")
    if ":" in t:
        try:
            h, mnt = (int(x) for x in t.split(":"))
            assert 0 <= h < 24 and 0 <= mnt < 60
        except (ValueError, AssertionError):
            return None, None, "time as hh:mm"
        c = (h * 60 + mnt) // 15
        g = next((x for x in scn["groups"] if x["onset_i"] <= c < x["onset_i"] + K + L_MAX + 1), None)
        return g, (max(c, g["onset_i"] + K) if g else c), ""
    return None, None, "type a meter id (m042), a group number (7) or a time (10:15)"


def next_event(scn, c):
    """Replay time at which the next silent group becomes visible after c, or None."""
    return min((g["onset_i"] + K for g in scn["groups"] if g["onset_i"] + K > c), default=None)


def shift_report(name, scn, c, log):
    """Markdown shift summary at replay time c: decisions, open queues, operator actions, chain head."""
    from theme import BANNER, fmt_hm, fmt_int, fmt_p  # theme is pure (no Streamlit)
    by_hash = {g["hash"]: g for g in scn["groups"]}
    dec = sorted((g for g in visible(scn, c) if status(g, c) == "decided"), key=lambda g: g["decided_i"])
    q = queues(scn, c, log)
    lines = [f"# SHAHID shift report — {name}", "", f"**{BANNER}**", "",
             f"Replayed day {scn['day0']:%Y-%m-%d}, report at replay time {fmt_hm(c)}; frozen detector version 1.", "",
             "## Decisions", "", "| Decided | Onset | Meters | Verdict | P(comms) | Handled by | Rule |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {fmt_hm(g['decided_i'])} | {fmt_hm(g['onset'])} | {fmt_int(g['n_meters'])} | {g['verdict']} | "
              f"{fmt_p(g['posterior_comms'])} | {g['escalation']['handled_by']} | {g['escalation']['rule']} |" for g in dec]
    lines += ["", "## Open at hand-over", ""] + [f"- {k}: {fmt_int(len(q[k]))}" for k in (*QUEUE_ORDER, "AUDIT")]
    lines += ["", "## Operator actions", "", "| Time (UTC) | Action | User | Item onset | Seconds | Reason |", "|---|---|---|---|---|---|"]
    for e in log:
        g = by_hash.get(e["item"])
        lines.append(f"| {e['timestamp']} | {e['action']} | {e['user']} | {fmt_hm(g['onset']) if g else 'other scenario'} | "
                     f"{e.get('seconds', '')} | {e.get('reason', '')} |")
    lines += ["", f"Operator-log chain head: `{log[-1]['hash'] if log else 'genesis (no action)'}`", ""]
    return "\n".join(lines)
