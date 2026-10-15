"""Deterministic episode generator: expands a `generator` block into explicit scenario events.

Origin: ORIGINAL. The expanded events are stored in labels/episodes.parquet by scenario.py, so
labels are always emitted by the injector, never written by hand.

generator:
  n: number of episodes (non-overlapping in time, spaced across the period)
  first_day: first day eligible (history must precede it)
  mix: {outage: p, comms_zone: p, comms_concentrator: p, comms_random: p,
        comms_load_change: p, outage_plus_comms: p}
  duration_steps: [lo, hi]
  zone_sizes: [lo, hi]       # meters in the silent set (zones restricted to this range)
  hours: [lo, hi]            # onset hour window
  offset_min: [a, b, ...]    # protocol 02: every event starts a minutes into its first 15-min step,
                             # drawn from this list on a separate random stream (absent: aligned)
Silent sets for outage and comms_zone come from the same zone distribution, so the structure of
the silent set carries no information; only energy evidence can separate them.
"""
import numpy as np

from shahid.world import grid_meta


def expand(cfg):
    g = cfg.get("generator")
    if not g:
        return cfg["events"]
    rng = np.random.default_rng(cfg["seed"] + 1000)
    meta = grid_meta(cfg["world"]["grid"])
    lo, hi = g.get("zone_sizes", [1, 10 ** 6])
    zones = [li for li, z in meta["zones"].items() if lo <= len(z) <= hi]
    n_rows = cfg["world"]["days"] * 96
    first = g.get("first_day", 15) * 96
    slots = np.linspace(first, n_rows - 96, g["n"] + 1).astype(int)
    kinds, p = zip(*g["mix"].items())
    h0, h1 = g.get("hours", [0, 24])
    events = list(cfg.get("events", []))
    for i in range(g["n"]):
        day0 = slots[i] // 96 * 96
        span = max(96, slots[i + 1] - slots[i]) // 96 * 96
        day = day0 + 96 * rng.integers(0, max(1, span // 96 - 1))
        start = int(day + rng.integers(h0 * 4, h1 * 4))
        dur = int(rng.integers(g["duration_steps"][0], g["duration_steps"][1] + 1))
        if start + dur + 8 >= n_rows:
            continue
        k = rng.choice(kinds, p=np.array(p) / sum(p))
        if k == "outage":
            ev = {"type": "outage", "line": int(rng.choice(zones))}
        elif k == "comms_zone":
            ev = {"type": "comms_failure", "zone": int(rng.choice(zones))}
        elif k == "comms_concentrator":
            ev = {"type": "comms_failure", "concentrator": int(rng.integers(len(meta["feeders"])))}
        elif k == "comms_load_change":  # hard negative: data stops while real load changes
            z = int(rng.choice(zones))
            f = float(rng.choice([0.3, 0.5, 2.0, 2.5]))
            events.append({"type": "load_change", "zone": z, "factor": f, "start_step": start,
                           "duration_steps": dur})
            ev = {"type": "comms_failure", "zone": z}
        elif k == "outage_plus_comms":  # hard negative: both causes at once, disjoint zones
            za = int(rng.choice(zones))
            disjoint = [z for z in zones if not (meta["zones"][z] & meta["zones"][za])]
            zb = int(rng.choice(disjoint))
            events.append({"type": "outage", "line": za, "start_step": start,
                           "duration_steps": dur})
            ev = {"type": "comms_failure", "zone": zb}
        elif k == "comms_random":
            size = len(meta["zones"][rng.choice(zones)])
            ev = {"type": "comms_failure",
                  "meters": sorted(rng.choice(meta["n_meters"], size, replace=False).tolist())}
        else:
            raise ValueError(k)
        events.append({**ev, "start_step": start, "duration_steps": dur})
    if g.get("offset_min"):  # separate stream: the aligned event stream above is unchanged
        orng = np.random.default_rng(cfg["seed"] + 2000)
        events = [{**e, "offset_min": int(orng.choice(g["offset_min"]))} for e in events]
    return events
