"""Operator action log for the UI preview: append-only, hash-chained like the decision log.

Reuses the chaining of shahid.explain (same SHA-256 over the sorted-JSON entry, same genesis and
verification), so `shahid.explain.verify_log` checks this file too. No Streamlit import here.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from shahid.explain import GENESIS, _hash, verify_log  # noqa: F401  (verify_log re-exported)

ACTIONS = ("APPROVED", "OVERRIDDEN", "DEFERRED", "ESCALATED")
FAST_SECONDS = 5.0  # DESIGN CHOICE (A-UI-FAST); kept in sync with ui/state.py


def append_action(path, item_hash, action, user, reason="", seconds=None, scenario=None):
    """Append one operator action that points to a decision-log entry (by its hash).
    seconds: time from opening the item to the action; approvals under FAST_SECONDS are flagged."""
    if action not in ACTIONS:
        raise ValueError(action)
    if action == "OVERRIDDEN" and not reason.strip():
        raise ValueError("an override needs a reason")
    path = Path(path)
    prev = GENESIS
    if path.exists() and path.stat().st_size:
        prev = json.loads(path.read_text(encoding="utf8").splitlines()[-1])["hash"]
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "action": action, "user": user, "item": item_hash, "reason": reason, "prev": prev}
    if scenario is not None:
        entry["scenario"] = scenario
    if seconds is not None:
        entry["seconds"] = round(float(seconds), 1)
        entry["fast"] = action == "APPROVED" and seconds < FAST_SECONDS
    entry["hash"] = _hash(entry)
    with open(path, "a", encoding="utf8") as f:  # append-only
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def read(path):
    p = Path(path)
    return [json.loads(x) for x in p.read_text(encoding="utf8").splitlines()] if p.exists() else []


def reset(path):
    """Start a new session log (the demo keeps no history between sessions)."""
    Path(path).unlink(missing_ok=True)
