"""CP1: cross-customer correlation of household loads vs the diversity knob (prior P2).

Run: python -m shahid.cp1_diversity   (writes results/cp1_diversity.json)
"""
import numpy as np

from shahid.grid import load_grid, profile_arrays
from shahid.stamp import stamp, write_json
from shahid.world import diversify

CFG = {"grid": "1-LV-semiurb5--0-sw", "d_values": [0.0, 0.25, 0.5, 1.0, 2.0], "seed": 0,
       "days": [0, 366]}


def main():
    net, prof = load_grid(CFG["grid"])
    lp, lq, _ = profile_arrays(net, prof)
    hh = net.load.profile.str.startswith("H0").to_numpy()
    out = {"stamp": stamp(CFG, "python -m shahid.cp1_diversity"), "n_households": int(hh.sum()),
           "by_d": {}}
    for d in CFG["d_values"]:
        p, _ = diversify(lp, lq, d, CFG["seed"])
        p = p[:, hh]
        c = np.corrcoef(p.T)
        iu = np.triu_indices_from(c, 1)
        out["by_d"][str(d)] = {
            "pairwise_corr_mean": float(c[iu].mean()),
            "pairwise_corr_share_above_0.999": float((c[iu] > 0.999).mean()),
            "annual_kwh_ratio_vs_d0": float(p.sum() / lp[:, hh].sum()),
        }
        print(d, out["by_d"][str(d)], flush=True)
    write_json("results/cp1_diversity.json", out)


if __name__ == "__main__":
    main()
