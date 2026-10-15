"""One command, whole path: simulate -> observe -> detect -> verdict vs truth.

Run: python -m shahid.smoke [config] [--no-write]   (default configs/smoke.yaml; --no-write leaves
     results/smoke.json untouched, for a demo run)
"""
import json
import sys
import time

import pandas as pd

from shahid import detect, scenario
from shahid.stamp import stamp, write_json


def match(labels, verdicts):
    """Label episode <-> detected episode: same start and meter-set Jaccard >= 0.5."""
    rows = []
    for _, l in labels.iterrows():
        lm = {f"m{m:03d}" for m in json.loads(l.meters)}
        best = None
        cand = verdicts[verdicts.onset == l.start] if len(verdicts) else verdicts
        for _, v in cand.iterrows():
            j = len(lm & set(v.meters)) / len(lm | set(v.meters))
            if j >= 0.5 and (best is None or j > best[0]):
                best = (j, v)
        v = best[1] if best else None
        rows.append({"truth": l.cause, "start": l.start, "n_meters": l.n_meters,
                     "verdict": v.verdict if v is not None else "MISSED",
                     "visible_share": None if v is None else round(v.visible_share, 3)})
    return pd.DataFrame(rows)


def main(cfg="configs/smoke.yaml", write=True):
    t = time.time()
    d = scenario.main(cfg)
    import json
    from shahid.cp5_compare import primary_method
    frozen = json.load(open("results/detector_params.json"))
    method = primary_method()  # frozen CP5 detector and thresholds
    v = detect.detect(detect.load_inputs(d), {**frozen["fitted"], **frozen["thresholds"][method]},
                      method)
    labels = pd.read_parquet(d / "labels" / "episodes.parquet")
    res = match(labels, v)
    print(res.to_string(index=False))
    dt = time.time() - t
    print(f"detected episodes: {len(v)}, runtime {dt:.1f}s")
    # results/cp2_smoke.json is the CP2 record (ledger C2-01); later smoke runs write here instead
    if write:
        write_json("results/smoke.json", {
            "stamp": stamp(scenario.load_cfg(cfg), f"python -m shahid.smoke {cfg}"),
            "runtime_s": dt, "detected_episodes": len(v),
            "episodes": res.astype(str).to_dict("records")})
    return res


if __name__ == "__main__":
    main(*[a for a in sys.argv[1:] if a != "--no-write"], write="--no-write" not in sys.argv)
