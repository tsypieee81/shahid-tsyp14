"""G2/G3 artefacts: verdict record, template explanation, append-only decision log, escalation.

Origin: ORIGINAL. Status: IMPLEMENTED (no UI). The escalation table is a DESIGN CHOICE that has not
been validated with operators.

Every number in an explanation is copied from the verdict record (tests/test_explain.py enforces
this). The decision log is append-only JSON lines; each entry carries the SHA-256 of the previous
entry, so any edit or deletion breaks the chain (`verify_log`).
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml

GENESIS = "0" * 64


def _num(x, nd=2):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), nd)


def verdict_record(row, detector_version):
    """Build the auditable record from one detector output row (pandas Series or dict)."""
    r = dict(row)
    p_comms = r.get("p_comms")
    p_comms = None if p_comms is None or (isinstance(p_comms, float) and np.isnan(p_comms)) \
        else float(p_comms)
    verdict = r["verdict"]
    if verdict == "OUTAGE":
        runner_up, p_cause = "COMMS_FAILURE", None if p_comms is None else 1 - p_comms
    elif verdict == "COMMS_FAILURE":
        runner_up, p_cause = "OUTAGE", p_comms
    else:
        runner_up, p_cause = None, None
    return {
        "onset": str(r["onset"]), "decided_at": str(r["decided_at"]),
        "latency_intervals": int(r["latency_intervals"]), "method": r["method"],
        "detector_version": detector_version,
        "cause": verdict, "probability": _num(p_cause, 3), "runner_up": runner_up,
        "abstain_reason": r.get("abstain_reason") or None,
        "evidence": {
            "n_meters": int(r["n_meters"]), "meters": list(r["meters"]),
            "window_intervals": int(r["n_intervals"]),
            "visible_kwh": _num(r["R"]), "expected_kwh": _num(r["M"]),
            "visible_share": _num(r.get("visible_share")),
            "sd_if_outage_kwh": _num(r["sd_O"]), "sd_if_comms_kwh": _num(r["sd_C"]),
            "gap_baseline_kwh": _num(r["gap0"], 3),
        },
    }


def explain(rec):
    """Deterministic plain-language explanation. Every number comes from `rec`."""
    e = rec["evidence"]
    head = {
        "OUTAGE": "These customers most likely lost power.",
        "COMMS_FAILURE": "These customers most likely still have power; only their data stopped.",
        "UNCERTAIN": "The system cannot tell whether these customers lost power.",
    }[rec["cause"]]
    lines = [
        f"{e['n_meters']} meters stopped reporting at {rec['onset']}. {head}",
        f"Over the {e['window_intervals']} intervals checked, these meters would normally use "
        f"{e['expected_kwh']} kWh. The transformer still shows {e['visible_kwh']} kWh that no "
        f"reporting meter accounts for (visible share {e['visible_share']}).",
        f"If power were lost, that figure should be close to zero (typical spread {e['sd_if_outage_kwh']} "
        f"kWh). If only data were lost, it should be near {e['expected_kwh']} (typical spread "
        f"{e['sd_if_comms_kwh']} kWh).",
    ]
    if rec["probability"] is not None:
        lines.append(f"Confidence in this cause: {rec['probability']}. "
                     f"The alternative considered was {rec['runner_up']}.")
    if rec["abstain_reason"]:
        lines.append(f"Reason for not deciding: {rec['abstain_reason']}.")
    lines.append(f"Decided at {rec['decided_at']}, {rec['latency_intervals']} intervals after "
                 f"the meters went silent, by method {rec['method']}.")
    return " ".join(lines)


def load_escalation(path="configs/escalation.yaml"):
    return yaml.safe_load(open(path))


def escalate(rec, table):
    """First matching rule wins. Returns {'rule', 'action', 'handled_by'}."""
    e = rec["evidence"]
    for rule in table["rules"]:
        w = rule["when"]
        if "cause" in w and rec["cause"] != w["cause"]:
            continue
        if "min_probability" in w and (rec["probability"] or 0) < w["min_probability"]:
            continue
        if "max_meters" in w and e["n_meters"] > w["max_meters"]:
            continue
        if "min_meters" in w and e["n_meters"] < w["min_meters"]:
            continue
        return {"rule": rule["id"], "action": rule["action"], "handled_by": rule["handled_by"]}
    d = table["default"]
    return {"rule": "default", "action": d["action"], "handled_by": d["handled_by"]}


def _hash(entry):
    return hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()


def append_log(path, rec, explanation, escalation):
    path = Path(path)
    prev = GENESIS
    if path.exists() and path.stat().st_size:
        prev = json.loads(path.read_text(encoding="utf8").splitlines()[-1])["hash"]
    entry = {"record": rec, "explanation": explanation, "escalation": escalation, "prev": prev}
    entry["hash"] = _hash(entry)
    with open(path, "a", encoding="utf8") as f:  # append-only
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry["hash"]


def verify_log(path):
    prev = GENESIS
    for i, line in enumerate(Path(path).read_text(encoding="utf8").splitlines()):
        e = json.loads(line)
        h = e.pop("hash")
        if e["prev"] != prev or _hash(e) != h:
            return False, i
        prev = h
    return True, None


def demo(config="configs/smoke.yaml", out="results/decision_log_demo.jsonl"):
    """Run the frozen primary detector on one scenario and write a fresh demo decision log.

    Run: python -m shahid.explain   (prints the explanations of the decided labelled episodes)
    """
    from shahid import detect, scenario
    from shahid.cp5_compare import primary_method
    from shahid.stamp import git_commit
    params = json.load(open("results/detector_params.json"))
    method = primary_method()
    p = {**params["fitted"], **params["thresholds"][method]}
    d = scenario.main(config)
    verdicts = detect.detect(detect.load_inputs(d), p, method)
    table = load_escalation()
    version = f"{method}@{git_commit()}"  # before touching the tracked demo log
    Path(out).unlink(missing_ok=True)  # a demo log starts empty; production logs only append
    big = verdicts[verdicts.n_meters >= 3]
    for _, row in big.iterrows():
        rec = verdict_record(row, version)
        text = explain(rec)
        append_log(out, rec, text, escalate(rec, table))
        print(text, "\n ->", escalate(rec, table), "\n")
    print("log valid:", verify_log(out), "entries:", len(big))


if __name__ == "__main__":
    demo()
