"""Truth-level energy balance closes, and pandapower sign conventions hold (prior P5)."""
import numpy as np
import pytest

from shahid.grid import load_grid, profile_arrays, run_steps


@pytest.mark.parametrize("code", ["1-LV-semiurb5--0-sw", "1-LV-semiurb5--2-sw"])
def test_truth_balance_closes(code):
    net, prof = load_grid(code)
    lp, lq, sp = profile_arrays(net, prof)
    steps = np.r_[0:8, 172 * 96 + 44:172 * 96 + 56]  # winter night + summer midday
    r = run_steps(net, lp, lq, sp, steps)
    assert r["converged"].all()
    delivered = -r["trafo_p_lv"][:, 0]
    rhs = r["load_p"].sum(1) - r["sgen_p"].sum(1) + r["storage_p"][:, 0] + r["line_pl"][:, 0]
    assert np.abs(delivered - rhs).max() < 1e-6  # MW, i.e. < 1 W
    # signs: loads consume (+), PV generates (+), line losses >= 0
    assert (r["load_p"] >= 0).all() and (r["sgen_p"] >= 0).all() and (r["line_pl"] >= 0).all()
    # HV side = LV delivered + trafo losses
    assert np.allclose(r["trafo_p_hv"][:, 0], delivered + r["trafo_pl"][:, 0], atol=1e-9)


def test_reverse_flow_sign():
    """At summer noon with PV scaled up, delivered power must go negative (export to MV)."""
    net, prof = load_grid("1-LV-semiurb5--0-sw")
    lp, lq, sp = profile_arrays(net, prof)
    r = run_steps(net, lp, lq, sp * 20, [172 * 96 + 52])
    assert -r["trafo_p_lv"][0, 0] < 0
