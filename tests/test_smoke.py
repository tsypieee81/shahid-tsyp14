"""The README quickstart command must keep running end to end."""
from shahid import smoke


def test_smoke_runs():
    res = smoke.main(write=False)
    assert len(res) == 2 and set(res.truth) == {"OUTAGE", "COMMS_FAILURE"}
