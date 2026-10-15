"""Business model: a null unit cost gives a formula, never a number; workload follows the ledger rates."""
import copy
import json

import yaml

from shahid import business_model as bm


def test_null_costs_are_formulas_and_filled_costs_are_numbers():
    cfg = yaml.safe_load(open(bm.CFG_PATH, encoding="utf8"))
    c = bm.costs(cfg)
    assert all(v["tnd"] is None and v["formula"] for v in c["one_off"].values())
    filled = copy.deepcopy(cfg)
    for k, v in {"share_substations_without_lv_meter": 0.5, "transformer_lv_meter_unit": 2.0,
                 "transformer_lv_meter_install": 1.0}.items():
        filled["unit_costs"][k]["value"] = v
    n = cfg["design"]["pilot_district_substations"]["value"]
    assert bm.costs(filled)["one_off"]["transformer_lv_meters"]["tnd"] == round(n * 0.5 * 3.0, 2)


def test_workload_uses_the_confirmatory_rates():
    cfg = yaml.safe_load(open(bm.CFG_PATH, encoding="utf8"))
    gate = {k: json.load(open("results/p2/confirm.json"))[k]["gate"] for k in bm.GRIDS}
    w = bm.workload(cfg, gate)["rural2/ff_1pct/v1"]
    rate = gate["rural2"]["ff_1pct"]["v1"]["human_items_per_transformer_day"]
    assert w["human_items_per_transformer_year"] == rate * cfg["design"]["days_per_year"]["value"]
    b = w["by_review_minutes"]["5"]
    assert b["district_cost"]["tnd"] == round(b["hours_per_district_year"] * cfg["unit_costs"]["operator_hourly_cost"]["value"], 2)
