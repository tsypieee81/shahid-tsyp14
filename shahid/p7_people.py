"""Protocol 07b: people study pack. Run by the team with >= 8 people outside the team.

Run: python -m shahid.p7_people booklets   -> docs/process/people_study/booklet_1.md, booklet_2.md,
                                             answer_sheet_template.csv, results/p7/people_key.json
     python -m shahid.p7_people analyse    -> reads docs/process/people_study/answers/P*.csv,
                                             writes results/p7/people_study.json
Items are explanations verbatim from shahid.explain, taken from the stored demo replays (SIMULATED).
The answer key stays out of the participants' booklets.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from shahid.evaluate import wilson
from shahid.stamp import stamp, write_json

PACK = Path("docs/process/people_study")
KEY = Path("results/p7/people_key.json")
SEED = 7
DRAW = {"OUTAGE": 4, "COMMS_FAILURE": 4, "UNCERTAIN": 3}
WRONG = ("feeder_outage", "2016-06-09 10:00:00")  # finding 09
REDACT = [r"These customers most likely lost power\.", r"These customers most likely still have power; only their data stopped\.",
          r"The system cannot tell whether these customers lost power\.", r"Confidence in this cause: [^.]*\.[^.]*\.",
          r"The alternative considered was [A-Z_]+\.", r"Reason for not deciding: [^.]*\.[^.]*\."]
ACTION = {"OUTAGE": "crew", "COMMS_FAILURE": "data_link", "UNCERTAIN": "supervisor_or_wait"}
CAUSE = {"OUTAGE": "outage", "COMMS_FAILURE": "communication", "UNCERTAIN": "cannot_tell"}


def demo_groups():
    rows = []
    for f in sorted(Path("results/demo").glob("*.json")):
        if f.name.endswith("_eval.json"):
            continue
        d = json.loads(f.read_text(encoding="utf8"))
        for g in d["groups"]:
            if g["n_meters"] >= 2:
                rows.append({"scenario": d["scenario"], "onset": g["onset"], "n_meters": g["n_meters"],
                             "verdict": g["verdict"], "explanation": g["explanation"]})
    return pd.DataFrame(rows)


def pool():
    """Addendum A: version 1 verdicts on the held-out urban6 simulation (seed 301, test weeks, >= 2 meters),
    explained by shahid.explain; plus the demo groups (only the confident-wrong item is drawn from them)."""
    from shahid import detect, explain, scenario
    from shahid.cp5_compare import inputs_of, split_of
    from shahid.records import families, fitted_for
    sims, fit_cfg, mode = families()["cp7_heldout_urban6"]
    cfg = dict(sims)[301]
    fitted, thr = fitted_for(fit_cfg, mode)
    v = detect.detect(inputs_of(scenario.simulate(cfg)), {**fitted, **thr["bayes"]}, "bayes")
    v = v[(split_of(v.onset) == 3) & (v.n_meters >= 2)]
    rows = [{"scenario": "heldout_urban6_301", "onset": str(r.onset), "n_meters": int(r.n_meters), "verdict": r.verdict,
             "explanation": explain.explain(explain.verdict_record(r._asdict(), "bayes"))} for r in v.itertuples()]
    return pd.concat([pd.DataFrame(rows), demo_groups()], ignore_index=True)


def evidence_only(text):
    for r in REDACT:
        text = re.sub(r, "", text)
    return re.sub(r"\s+", " ", text).strip()


def booklets():
    rng = np.random.default_rng(SEED)
    p = pool()
    wrong = p[(p.scenario == WRONG[0]) & (p.onset == WRONG[1])]
    rest = p[p.scenario == "heldout_urban6_301"]
    items = []
    for v, k in DRAW.items():
        c = rest[rest.verdict == v]
        items += c.iloc[rng.choice(len(c), k, replace=False)].to_dict("records")
    items.append(wrong.iloc[0].to_dict())
    order = rng.permutation(len(items))
    items = [items[i] for i in order]
    key = []
    for n, it in enumerate(items, 1):
        key.append({"item": n, "scenario": it["scenario"], "onset": it["onset"], "verdict": it["verdict"],
                    "intended_cause": CAUSE[it["verdict"]], "intended_action": ACTION[it["verdict"]],
                    "confident_wrong": (it["scenario"], it["onset"]) == WRONG})
    PACK.mkdir(parents=True, exist_ok=True)
    (PACK / "answers").mkdir(exist_ok=True)
    for b in (1, 2):
        lines = [f"# SHAHID explanation study — booklet {b}", "",
                 "SIMULATED data from a research prototype. Read each text alone and answer on the answer sheet.", ""]
        for n, it in enumerate(items, 1):
            form = "B" if (n <= 6) == (b == 1) else "A"
            text = evidence_only(it["explanation"]) if form == "B" else it["explanation"]
            q = ("Form B — what happened? (outage / communication / cannot_tell) and your confidence 1-5"
                 if form == "B" else
                 "Form A — what should the operator do? (crew / data_link / supervisor_or_wait) and clarity 1-5")
            lines += [f"## Item {n} (form {form})", "", f"> {text}", "", f"*{q}*", ""]
        (PACK / f"booklet_{b}.md").write_text("\n".join(lines), encoding="utf8")
    sheet = pd.DataFrame({"participant": "P01", "booklet": 1, "background": "", "item": range(1, len(items) + 1),
                          "form": ["B" if n <= 6 else "A" for n in range(1, len(items) + 1)],
                          "cause": "", "confidence_1_5": "", "action": "", "clarity_1_5": "", "deciding_number": ""})
    sheet.to_csv(PACK / "answer_sheet_template.csv", index=False)
    write_json(KEY, {"stamp": stamp({"seed": SEED, "draw": DRAW}, "python -m shahid.p7_people booklets"), "items": key})
    print("items", len(items), [k["verdict"] for k in key])


def fleiss(table):
    """Fleiss' kappa: table = items x categories counts (same raters per item not required: per-item n)."""
    t = np.asarray(table, float)
    n = t.sum(1)
    ok = n > 1
    t, n = t[ok], n[ok]
    if not len(t):
        return None
    p_j = t.sum(0) / t.sum()
    P_i = ((t * (t - 1)).sum(1)) / (n * (n - 1))
    Pe = (p_j ** 2).sum()
    return float((P_i.mean() - Pe) / (1 - Pe)) if Pe < 1 else None


def analyse():
    key = {k["item"]: k for k in json.loads(KEY.read_text(encoding="utf8"))["items"]}
    files = sorted((PACK / "answers").glob("P*.csv"))
    a = pd.concat([pd.read_csv(f) for f in files], ignore_index=True) if files else pd.DataFrame()
    out = {"stamp": stamp({"files": [f.name for f in files]}, "python -m shahid.p7_people analyse"),
           "participants": int(a.participant.nunique()) if len(a) else 0}
    if not len(a):
        write_json("results/p7/people_study.json", out)
        print("no answers yet")
        return
    a["wrong_item"] = a["item"].map(lambda i: key[i]["confident_wrong"])
    b = a[(a.form == "B") & ~a.wrong_item]
    f = a[(a.form == "A") & ~a.wrong_item]
    kb = int((b.cause == b["item"].map(lambda i: key[i]["intended_cause"])).sum())
    kf = int((f.action == f["item"].map(lambda i: key[i]["intended_action"])).sum())
    out["H7a_form_B_cause"] = {"agree": kb, "n": len(b), "rate": kb / len(b) if len(b) else None,
                               "wilson95": wilson(kb, len(b))}
    out["H7b_form_A_action"] = {"agree": kf, "n": len(f), "rate": kf / len(f) if len(f) else None,
                                "wilson95": wilson(kf, len(f))}
    for k in ("H7a_form_B_cause", "H7b_form_A_action"):
        lo = out[k]["wilson95"][0]
        out[k]["verdict"] = ("underpowered" if out["participants"] < 8 else
                             "supported" if lo is not None and lo > 1 / 3 else "not supported")
    cats = {"B": ("cause", list(CAUSE.values())), "A": ("action", list(ACTION.values()))}
    out["fleiss_kappa"] = {form: fleiss([[int((g[col] == c).sum()) for c in cs] for _, g in a[a.form == form].groupby("item")])
                           for form, (col, cs) in cats.items()}
    w = a[a.wrong_item]
    out["confident_wrong_item"] = {"n": len(w), "followed_system": int(((w.form == "B") & (w.cause == "communication")).sum()
                                                                       + ((w.form == "A") & (w.action == "data_link")).sum()),
                                   "note": "over-trust indicator, not a success measure"}
    out["per_item"] = [{"item": i, "form_answers": g.form.value_counts().to_dict(),
                        "agree": int(((g.form == "B") & (g.cause == key[i]["intended_cause"])).sum()
                                     + ((g.form == "A") & (g.action == key[i]["intended_action"])).sum()), "n": len(g)}
                       for i, g in a.groupby("item")]
    write_json("results/p7/people_study.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "per_item"}, default=str, indent=1))


if __name__ == "__main__":
    {"booklets": booklets, "analyse": analyse}[sys.argv[1]]()
