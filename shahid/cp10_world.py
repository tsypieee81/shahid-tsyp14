"""CP10 Task 10b: spread of the nominal CP6 cell across simulated-world seeds (frozen method,
detector refitted on each world's fault-free year). Post-hoc descriptive analysis, added after CP7.
Run: python -m shahid.cp10_world   (writes results/cp10_world.json)
"""
import pandas as pd

from shahid import evaluate
from shahid.stamp import stamp, write_json

KEYS = ["abstention_rate", "accuracy_when_decided", "outage_recall", "comms_recall",
        "false_outage_rate", "missed_outage_rate", "balanced_correct"]


def main():
    out = {"stamp": stamp({"weeks": [0, 1, 2]}, "python -m shahid.cp10_world"),
           "label": "post-hoc descriptive analysis, added after CP7", "worlds": {}}
    for fam, w in [("cp6_nominal", 0), ("world1_nominal", 1), ("world2_nominal", 2),
                   ("world3_nominal", 3)]:
        t = pd.read_parquet(f"results/records/{fam}__episodes.parquet")
        b = t[(t.method == "bayes") & (t.week != 3)]
        r = evaluate.rates(b)
        out["worlds"][w] = {"n": len(b), **{k: float(r[k]) for k in KEYS}}
    write_json("results/cp10_world.json", out)
    print(out["worlds"])


if __name__ == "__main__":
    main()
