"""Operator log of the UI preview: hash chain verifies, tampering is detected, override needs a reason."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ui"))
import oplog  # noqa: E402


def test_operator_log_chain(tmp_path):
    p = tmp_path / "log.jsonl"
    oplog.append_action(p, "a" * 64, "APPROVED", "op")
    oplog.append_action(p, "b" * 64, "DEFERRED", "op")
    oplog.append_action(p, "c" * 64, "OVERRIDDEN", "op", "readings arrived late")
    assert oplog.verify_log(p) == (True, None)
    lines = p.read_text(encoding="utf8").splitlines()
    e = json.loads(lines[1])
    e["action"] = "APPROVED"
    lines[1] = json.dumps(e, sort_keys=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf8")
    assert oplog.verify_log(p) == (False, 1)
    with pytest.raises(ValueError):
        oplog.append_action(p, "d" * 64, "OVERRIDDEN", "op", "")


def test_escalate_and_fast_approval_flag(tmp_path):
    p = tmp_path / "log.jsonl"
    a = oplog.append_action(p, "a" * 64, "APPROVED", "op", seconds=2.0, scenario="calm")
    b = oplog.append_action(p, "b" * 64, "APPROVED", "op", seconds=30.0)
    e = oplog.append_action(p, "c" * 64, "ESCALATED", "op", seconds=1.0)
    assert a["fast"] is True and b["fast"] is False and e["fast"] is False
    assert a["scenario"] == "calm" and oplog.verify_log(p) == (True, None)
    oplog.reset(p)
    assert oplog.read(p) == []
