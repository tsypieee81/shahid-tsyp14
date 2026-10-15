"""Protocol 07a: reliability of version 1's P(comms) on held-out records, with the mid range examined.

Run: python -m shahid.p7_reliability   (results/p7/reliability.json, results/figs/p7_reliability.png)
Records only (no simulation): cp7_heldout_urban6 and rural3_eps groups, method bayes, test weeks.
"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from shahid import evaluate  # noqa: E402
from shahid.stamp import stamp, write_json  # noqa: E402

FAMS = {"urban6": "cp7_heldout_urban6", "rural3": "rural3_eps"}
EDGES = np.linspace(0, 1, 11)
MID = (0.1, 0.9)


def load(fam):
    g = pd.read_parquet(f"results/records/{fam}__groups.parquet")
    g = g[(g.method == "bayes") & (g.week == 3)]
    keep = g.truth.isin(["OUTAGE", "COMMS_FAILURE"]) & g.p_comms.notna()
    return g[keep], int((~keep).sum())


def table(g):
    b = np.clip(np.digitize(g.p_comms, EDGES) - 1, 0, 9)
    rows = []
    for k in range(10):
        s = g[b == k]
        n, c = len(s), int((s.truth == "COMMS_FAILURE").sum())
        rows.append({"bin": f"{EDGES[k]:.1f}-{EDGES[k + 1]:.1f}", "lo": float(EDGES[k]), "n": n,
                     "mean_predicted": float(s.p_comms.mean()) if n else None,
                     "observed_comms": c / n if n else None, "wilson95": evaluate.wilson(c, n) if n else None})
    ece = sum(r["n"] * abs(r["mean_predicted"] - r["observed_comms"]) for r in rows if r["n"]) / max(1, len(g))
    return rows, float(ece)


def h7(rows):
    mid = [r for r in rows if MID[0] <= r["lo"] < MID[1] and r["n"] >= 10]
    inside = sum(r["wilson95"][0] <= r["mean_predicted"] <= r["wilson95"][1] for r in mid)
    return {"mid_bins_with_n_ge_10": len(mid), "inside_interval": int(inside),
            "verdict": "underpowered" if len(mid) < 6 else ("supported" if inside >= 6 else "not supported")}


def main():
    Path("results/p7").mkdir(parents=True, exist_ok=True)
    out = {"stamp": stamp({"protocol": "docs/process/protocols/07a_reliability.md", "fams": FAMS},
                          "python -m shahid.p7_reliability"), "label": "held-out records, version 1 frozen"}
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], color="0.6", lw=1)
    pooled = []
    for name, fam in FAMS.items():
        g, excluded = load(fam)
        pooled.append(g)
        rows, ece = table(g)
        out[name] = {"n": len(g), "excluded": excluded, "bins": rows, "ece": ece}
        pts = [r for r in rows if r["n"]]
        ax.plot([r["mean_predicted"] for r in pts], [r["observed_comms"] for r in pts], "o-", label=name)
    g = pd.concat(pooled)
    rows, ece = table(g)
    out["pooled"] = {"n": len(g), "bins": rows, "ece": ece, "h7": h7(rows)}
    # descriptive, added after the registered analysis was seen: labelled episodes only (the C7-05 basis)
    ge = g[g.matched_episode >= 0]
    er, ee = table(ge)
    out["pooled_episodes_only_descriptive"] = {"n": len(ge), "bins": er, "ece": ee,
                                               "note": "added after the registered result; not a registered endpoint"}
    ax.axvspan(*MID, color="0.9", zorder=0)
    ax.set(xlabel="predicted P(comms)", ylabel="observed share of communication failures",
           title="Held-out reliability (version 1, SIMULATED)")
    ax.legend()
    fig.savefig("results/figs/p7_reliability.png", dpi=150, bbox_inches="tight")
    write_json("results/p7/reliability.json", out)
    print(json.dumps({"pooled_n": len(g), "ece": ece, "h7": out["pooled"]["h7"],
                      "bins": [(r["bin"], r["n"], r["mean_predicted"] and round(r["mean_predicted"], 3),
                                r["observed_comms"] and round(r["observed_comms"], 3)) for r in rows]}, indent=1))


if __name__ == "__main__":
    main()
