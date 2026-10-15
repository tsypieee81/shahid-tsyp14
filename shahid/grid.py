"""SimBench grid loading, power-flow time series and topology helpers.

Origin: ADAPTED. Network data and power-flow solver are REUSED (simbench, pandapower);
the stepping loop, result collection and zone derivation are ORIGINAL.
"""
import warnings

import networkx as nx
import numpy as np
import pandapower as pp
import pandapower.topology as top
import simbench as sb

warnings.filterwarnings("ignore", category=FutureWarning)

DT_H = 0.25  # 15-min interval in hours


def load_grid(code):
    net = sb.get_simbench_net(code)
    prof = sb.get_absolute_values(net, profiles_instead_of_study_cases=True)
    return net, prof


def profile_arrays(net, prof):
    """Absolute profiles as arrays aligned to net.load / net.sgen index. Units: MW, Mvar."""
    lp = prof[("load", "p_mw")][net.load.index].to_numpy()
    lq = prof[("load", "q_mvar")][net.load.index].to_numpy()
    sp = prof[("sgen", "p_mw")][net.sgen.index].to_numpy() if len(net.sgen) else np.zeros((len(lp), 0))
    return lp, lq, sp


def run_steps(net, lp, lq, sp, steps, sgen_on=None):
    """Run one power flow per step. Returns dict of arrays (steps x elements), MW.

    Sign conventions (pandapower, verified empirically in CP1, see tests/test_balance.py):
    res_load.p_mw >0 consumed; res_sgen.p_mw >0 generated; res_trafo.p_lv_mw >0 flows INTO the
    trafo at the LV terminal, so LV-side delivered power = -p_lv_mw; res_line.pl_mw = line loss; res_storage.p_mw >0 charging.
    Storage is held at its static SimBench setpoint (SimBench gives it no profile).
    """
    n = len(steps)
    out = {k: np.full((n, m), np.nan) for k, m in [
        ("load_p", len(net.load)), ("sgen_p", len(net.sgen)), ("vm_load", len(net.load)),
        ("trafo_p_hv", 1), ("trafo_p_lv", 1), ("trafo_pl", 1), ("trafo_loading", 1),
        ("line_pl", 1), ("storage_p", 1), ("vm_min", 1), ("vm_max", 1)]}
    out["converged"] = np.zeros(n, bool)
    load_bus = net.load.bus.to_numpy()
    for i, t in enumerate(steps):
        net.load["p_mw"] = lp[t]
        net.load["q_mvar"] = lq[t]
        if sp.shape[1]:
            net.sgen["p_mw"] = sp[t] if sgen_on is None else sp[t] * sgen_on
        try:
            pp.runpp(net, numba=True)
        except pp.LoadflowNotConverged:
            continue
        out["converged"][i] = True
        out["load_p"][i] = net.res_load.p_mw.to_numpy()
        out["sgen_p"][i] = net.res_sgen.p_mw.to_numpy()
        out["vm_load"][i] = net.res_bus.vm_pu.loc[load_bus].to_numpy()
        tr = net.res_trafo.iloc[0]
        out["trafo_p_hv"][i] = tr.p_hv_mw
        out["trafo_p_lv"][i] = tr.p_lv_mw
        out["trafo_pl"][i] = tr.pl_mw
        out["trafo_loading"][i] = tr.loading_percent
        out["line_pl"][i] = net.res_line.pl_mw.sum()
        out["storage_p"][i] = net.res_storage.p_mw.sum() if len(net.storage) else 0.0
        vm = net.res_bus.vm_pu[net.bus.vn_kv < 1]
        out["vm_min"][i], out["vm_max"][i] = vm.min(), vm.max()
    return out


def candidate_zones(net):
    """For every line, the loads isolated from the trafo LV bus when that line is opened.

    DESIGN CHOICE: SimBench has no protection data, so a 'zone' is any set of customers a single
    line opening would isolate. Returns {line_idx: frozenset(load_idx)} and feeder head lines.
    """
    g = top.create_nxgraph(net, respect_switches=True, include_trafos=False)
    root = int(net.trafo.lv_bus.iloc[0])
    loads_at = net.load.groupby("bus").groups
    zones = {}
    for li, row in net.line[net.line.in_service].iterrows():
        a, b = int(row.from_bus), int(row.to_bus)
        key = ("line", li)
        if not g.has_edge(a, b, key):
            continue  # open via switch
        attrs = g.get_edge_data(a, b, key)
        g.remove_edge(a, b, key)
        cut = set()
        for comp in nx.connected_components(g):
            if root not in comp:
                cut |= comp
        g.add_edge(a, b, key, **attrs)
        zl = frozenset(i for bus in cut for i in loads_at.get(bus, []))
        if zl:
            zones[li] = zl
    feeders = [li for li, r in net.line.iterrows() if root in (r.from_bus, r.to_bus) and li in zones]
    return zones, feeders
