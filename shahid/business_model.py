"""Business-case model: operator workload, avoided false outage verdicts, compute and storage sizing,
and one-off and recurring cost tables in TND.

Reads only `configs/business.yaml`, existing result files cited by the ledger (`results/p2/confirm.json`,
rows P2C-04) and committed dataset files. Writes `results/business/business.json` (stamped).
Status: every output is an ESTIMATE built on SIMULATED rates, except the timing, which is MEASURED on
this machine. A unit cost that is null in the config is reported as a formula, never as a number.

Run: python -m shahid.business_model   (--retime remeasures the compute timing)
Origin: ORIGINAL.
"""
import json
import os
import platform
import sys
import time
from pathlib import Path

import yaml

from shahid import detect
from shahid.stamp import stamp, write_json

CFG_PATH = "configs/business.yaml"
OUT = Path("results/business/business.json")
DATA = "dataset/episodes_semiurb5_seed101"
GRIDS = ["rural2", "semiurb4"]
SCENARIOS = {"ff_1pct": "1% random data loss (nominal)", "loss10": "10% random data loss"}
POLICIES = ["v1", "v1+gate-close", "v1+gate-escalate"]


def val(cfg, key):
    for sect in cfg.values():
        if key in sect:
            return sect[key]["value"]
    raise KeyError(key)


def money(amount_expr, value):
    """A cost cell: the number when every input is known, otherwise the formula."""
    return {"tnd": None if value is None else round(value, 2), "formula": amount_expr}


def workload(cfg, gate):
    days, minutes, n_sub = val(cfg, "days_per_year"), val(cfg, "review_minutes_per_item"), \
        val(cfg, "pilot_district_substations")
    rate = val(cfg, "operator_hourly_cost")
    out = {}
    for grid in GRIDS:
        for scen in SCENARIOS:
            for pol in POLICIES:
                r = gate[grid][scen][pol]
                items_year = r["human_items_per_transformer_day"] * days
                row = {"human_items_per_transformer_day": r["human_items_per_transformer_day"],
                       "human_items_per_transformer_year": items_year, "by_review_minutes": {}}
                for m in minutes:
                    h_tr = items_year * m / 60
                    h_dist = h_tr * n_sub
                    row["by_review_minutes"][str(m)] = {
                        "hours_per_transformer_year": h_tr,
                        "hours_per_district_year": h_dist,
                        "hours_per_district_day": h_dist / days,
                        "district_cost": money("hours_per_district_year x operator_hourly_cost",
                                               None if rate is None else h_dist * rate)}
                out[f"{grid}/{scen}/{pol}"] = row
    return out


def avoided(gate):
    out = {}
    for grid in GRIDS:
        for scen in SCENARIOS:
            g = gate[grid][scen]
            base = g["v1"]["false_outage_verdicts_per_transformer_year"]
            out[f"{grid}/{scen}"] = {
                pol: {"false_outage_verdicts_per_transformer_year": g[pol]["false_outage_verdicts_per_transformer_year"],
                      "avoided_vs_v1": base - g[pol]["false_outage_verdicts_per_transformer_year"]}
                for pol in POLICIES}
    return out


def timing(budget):
    """MEASURED: frozen detector on the committed episode dataset (whole simulated year, one transformer)."""
    params = json.load(open("results/detector_params.json"))
    p = {**params["fitted"], **params["thresholds"]["bayes"]}
    inputs = detect.load_inputs(DATA)
    n_meters, n_rows = len(inputs["meters"]), len(inputs["trafo"])
    t0 = time.perf_counter()
    table = detect.evidence_table(inputs, p)
    verdicts = detect.decide_table(table, "bayes", p)
    secs = time.perf_counter() - t0
    assert secs <= budget, f"benchmark exceeded its {budget} s budget"
    days = n_rows / 96
    return {"status": "MEASURED", "dataset": DATA, "meters": n_meters, "simulated_days": days,
            "silent_groups_scored": len(verdicts), "wall_seconds": secs,
            "seconds_per_transformer_year": secs * 365 / days,
            "cpu": platform.processor(), "logical_cpus": os.cpu_count(), "os": platform.platform(),
            "note": "single process; includes evidence and decision for every silent group of the year"}


def storage(cfg):
    """ESTIMATE from committed parquet sizes (one transformer, one simulated year)."""
    d = Path(DATA)
    n_meters = len(detect.load_inputs(DATA)["meters"])
    days = 366  # the committed dataset covers the 2016 profile year
    mr = (d / "observed/meter_readings.parquet").stat().st_size
    tr = (d / "observed/transformer.parquet").stat().st_size
    log = Path("results/decision_log_demo.jsonl")
    log_entries = sum(1 for _ in log.open(encoding="utf8"))
    per_meter_year = mr / n_meters * 365 / days
    return {"status": "ESTIMATE", "basis": "committed parquet sizes (energy, arrival time, voltage per reading)",
            "bytes_meter_readings_per_meter_year": per_meter_year,
            "mb_per_1000_meter_years": per_meter_year * 1000 / 1e6,
            "bytes_transformer_series_per_transformer_year": tr * 365 / days,
            "bytes_per_decision_log_entry": log.stat().st_size / log_entries,
            "hosting_cost": money("hosting_monthly x 12", None)}


def costs(cfg):
    g = lambda k: val(cfg, k)
    n = g("pilot_district_substations")
    share, unit, inst = g("share_substations_without_lv_meter"), g("transformer_lv_meter_unit"), \
        g("transformer_lv_meter_install")
    meters = None if None in (share, unit, inst) else n * share * (unit + inst)
    integ = None if None in (g("integration_person_days"), g("engineer_day_rate")) else \
        g("integration_person_days") * g("engineer_day_rate")
    train = None if None in (g("pilot_operators"), g("operator_training_per_person")) else \
        g("pilot_operators") * g("operator_training_per_person")
    host = None if g("hosting_monthly") is None else 12 * g("hosting_monthly")
    one_off = {
        "transformer_lv_meters": money("substations x share_without_lv_meter x (meter_unit + install)", meters),
        "integration": money("integration_person_days x engineer_day_rate", integ),
        "operator_training": money("pilot_operators x operator_training_per_person", train)}
    recurring = {
        "operator_review_time": money("hours_per_district_year x operator_hourly_cost (main recurring cost; "
                                      "hours in workload)", None),
        "hosting": money("12 x hosting_monthly", host),
        "storage": money("GB stored x 12 x storage_per_gb_month (size in storage)", None),
        "recalibration_review": money("(days_per_year / recalibration_interval_days) x review person-days x "
                                      "engineer_day_rate", None),
        "operator_refresher_training": money("pilot_operators x operator_training_per_person x refresher share", None)}
    return {"currency": "TND", "usd_rate_tnd_per_usd": g("bct_tnd_per_usd"),
            "usd_lines": "none: no cost has a USD source", "one_off": one_off, "recurring_per_year": recurring}


def compute_block(cfg):
    """The timing is a measurement: a cost-only rerun keeps the stored one (ledger BUS-04); --retime remeasures."""
    if OUT.exists() and "--retime" not in sys.argv:
        return json.load(open(OUT))["compute"]
    return timing(val(cfg, "timing_budget_seconds"))


def main():
    cfg = yaml.safe_load(open(CFG_PATH, encoding="utf8"))
    gate = {k: json.load(open("results/p2/confirm.json"))[k]["gate"] for k in GRIDS}
    out = {"stamp": stamp({"business": cfg, "source_rows": "P2C-04 (results/p2/confirm.json *.gate)"},
                          "python -m shahid.business_model"),
           "label": "ESTIMATE on SIMULATED rates, except timing (MEASURED); unknown unit costs are formulas",
           "workload": workload(cfg, gate), "false_outage_verdicts": avoided(gate),
           "compute": compute_block(cfg), "storage": storage(cfg), "costs": costs(cfg)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    write_json(OUT, out)
    print(json.dumps({k: out[k] for k in ["compute", "storage"]}, indent=1))


if __name__ == "__main__":
    main()
