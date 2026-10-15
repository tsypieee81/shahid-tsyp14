"""How permissive is the number checker? Share of random numbers that match the claims ledger under
the checker's rounding tolerance (value, x100 and complement, at the printed precision).

A high share means a wrong number of that form cannot be caught by the checker; only generating the
documents from result files protects it.
Run: python -m shahid.checker_limits   (writes results/checker_limits.json)
"""
import numpy as np

from shahid import check_numbers as cn
from shahid.stamp import stamp, write_json

FORMS = [("two decimals in [0, 1]", 2, 0, 1), ("three decimals in [0, 1]", 3, 0, 1),
         ("one decimal in [0, 100]", 1, 0, 100), ("two decimals in [0, 100]", 2, 0, 100),
         ("integers in [0, 1000]", 0, 0, 1000)]
N, SEED = 2000, 0


def main():
    lv = set()
    for r in cn.ledger_rows():
        for tok in cn.numbers_in(r):
            lv.add(float(tok))
    sets = cn.rounded_sets(lv)
    rng = np.random.default_rng(SEED)
    res = {}
    for name, d, lo, hi in FORMS:
        hits = sum(cn.matches(f"{x:.{d}f}", sets) for x in rng.uniform(lo, hi, N))
        res[name] = {"n": N, "share_matching_ledger": hits / N}
    write_json("results/checker_limits.json", {
        "stamp": stamp({"forms": FORMS, "n": N, "seed": SEED}, "python -m shahid.checker_limits"),
        "ledger_values": len(lv), "results": res})
    for k, v in res.items():
        print(f"{k}: {v['share_matching_ledger']:.3f} of {N} random numbers match the ledger")


if __name__ == "__main__":
    main()
