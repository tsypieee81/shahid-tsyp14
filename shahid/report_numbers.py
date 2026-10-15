"""Tooling: values the report states that are simple derivations of existing result files.

Run: python -m shahid.report_numbers   (writes results/report_numbers.json)
- confirmatory coverage = 1 - abstention rate (results/p2/confirm.json, version 1, test weeks);
- 30-minute missed-outage interval of the reporting-interval study (results/studies/reporting_interval/summary.json).
No new computation on data; every value is read from a stamped result file.
"""
import json

from shahid.stamp import stamp, write_json


def main():
    c = json.load(open("results/p2/confirm.json"))
    s = json.load(open("results/studies/reporting_interval/summary.json"))
    out = {"stamp": stamp({"sources": ["results/p2/confirm.json", "results/studies/reporting_interval/summary.json"]},
                          "python -m shahid.report_numbers"),
           "confirmatory_coverage_v1": {g: round(1 - c[g]["detection"]["v1"]["abstention_rate"], 4)
                                        for g in ("rural2", "semiurb4")},
           "reporting_interval_30min_missed": {"rate": s["conditions"]["C30"]["bayes"]["missed_outage_rate"]["rate"],
                                               "ci95": s["conditions"]["C30"]["bayes"]["missed_outage_rate"]["ci95"]}}
    write_json("results/report_numbers.json", out)
    print(json.dumps(out, default=str)[:400])


if __name__ == "__main__":
    main()
