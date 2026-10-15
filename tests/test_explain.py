"""Explanations only contain numbers from the verdict record; the decision log is tamper-evident."""
import json
import re

import pandas as pd
import pytest

from shahid import explain

NUM = re.compile(r"-?\d+(?:\.\d+)?")
ROWS = [
    {"onset": pd.Timestamp("2016-06-23 10:00"), "decided_at": pd.Timestamp("2016-06-23 10:30"),
     "latency_intervals": 2, "method": "bayes", "n_meters": 7, "meters": ["m004", "m060"],
     "n_intervals": 2, "R": 0.0312, "M": 2.3061, "visible_share": 0.0135, "sd_O": 0.1311,
     "sd_C": 0.7432, "gap0": 0.0161, "verdict": "OUTAGE", "p_comms": 0.0021,
     "abstain_reason": ""},
    {"onset": pd.Timestamp("2016-03-01 03:15"), "decided_at": pd.Timestamp("2016-03-01 04:15"),
     "latency_intervals": 6, "method": "bayes", "n_meters": 1, "meters": ["m011"],
     "n_intervals": 6, "R": 0.05, "M": 0.12, "visible_share": 0.4167, "sd_O": 0.05,
     "sd_C": 0.09, "gap0": 0.002, "verdict": "UNCERTAIN", "p_comms": None,
     "abstain_reason": "expected energy of silent group too small for the balance"},
]


@pytest.mark.parametrize("row", ROWS)
def test_every_number_in_explanation_comes_from_record(row):
    rec = explain.verdict_record(row, "test")
    text = explain.explain(rec)
    allowed = set(NUM.findall(json.dumps(rec)))
    for n in NUM.findall(text):
        assert n in allowed, f"{n} not in record"


def test_escalation_and_log(tmp_path):
    table = explain.load_escalation()
    log = tmp_path / "decisions.jsonl"
    for row in ROWS:
        rec = explain.verdict_record(row, "test")
        explain.append_log(log, rec, explain.explain(rec), explain.escalate(rec, table))
    assert explain.verify_log(log) == (True, None)
    assert explain.escalate(explain.verdict_record(ROWS[1], "t"), table)["handled_by"] == "HUMAN"
    lines = log.read_text(encoding="utf8").splitlines()
    e = json.loads(lines[0])
    e["record"]["cause"] = "COMMS_FAILURE"  # tamper with the first entry
    log.write_text("\n".join([json.dumps(e, sort_keys=True)] + lines[1:]) + "\n", encoding="utf8")
    assert explain.verify_log(log) == (False, 0)
