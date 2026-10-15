"""Reproducibility check: regenerate selected stages and compare with the committed results.

Meant for a fresh clone: `git clone ...; python -m shahid.verify_repro`. Stamps are ignored; every
other value must be identical. The long stages (cp4, cp5_compare, cp6, cp7) are not included here
because together they take hours; `python -m shahid.reproduce` runs everything.
Run: python -m shahid.verify_repro   (writes results/repro_check.json)
     python -m shahid.verify_repro --all [--compare-only]   (writes results/repro_check_all.json;
     --compare-only skips the pipeline and compares the existing results with git HEAD)
     python -m shahid.verify_repro --summary   (writes results/repro_summary.json: counts only)
"""
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

import pandas as pd

from shahid.stamp import stamp, write_json

JSON_STAGES = {"cp1_diversity": "cp1_diversity.json", "cp3_checks": "cp3_checks.json",
               "cp5_gap": "cp5_gap.json"}
TABLES = ["observed/meter_readings", "observed/transformer", "context/meters", "context/zones",
          "labels/episodes", "labels/cells"]


IGNORE = ("stamp", "files_mb", "dir", "ms_per_step", "cell_commits", "runtime_s")


def strip(d):
    """Drop provenance and wall-clock fields; make NaN compare equal to NaN."""
    if isinstance(d, dict):
        return {k: strip(v) for k, v in d.items() if k not in IGNORE}
    if isinstance(d, list):
        return [strip(x) for x in d]
    if isinstance(d, float) and d != d:
        return "NaN"
    return d


LONG = [("cp5_compare", [], ["cp5_compare.json", "detector_params.json"]),
        ("cp6_sweep", ["nominal"], ["cp6/nominal.json"]),
        ("cp7_heldout", [], ["cp7_heldout.json"]),
        ("leak_audit", [], ["leak_audit.json"])]


def long_check():
    """Re-run the headline stages (several hours of CPU) and compare with the committed files."""
    ref = Path(tempfile.mkdtemp())
    out = {"stamp": stamp({"long": [s for s, _, _ in LONG]}, "python -m shahid.verify_repro --long"),
           "checks": {}, "runtime_s": {}}
    for stage, args, files in LONG:
        for f in files:
            (ref / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(Path("results") / f, ref / f)
        t = time.time()
        subprocess.run([sys.executable, "-m", f"shahid.{stage}", *args], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        out["runtime_s"][stage] = round(time.time() - t)
        for f in files:
            out["checks"][f] = strip(json.load(open(ref / f))) ==                 strip(json.load(open(Path("results") / f)))
        print(stage, out["runtime_s"][stage], {f: out["checks"][f] for f in files}, flush=True)
    out["all_identical"] = all(out["checks"].values())
    write_json("results/repro_check_long.json", out)


def committed_results():
    """The committed results/ tree (git HEAD), never the working copy, which an interrupted run
    may have partly deleted."""
    root = Path(tempfile.mkdtemp())
    tar = subprocess.run(["git", "archive", "HEAD", "results"], check=True, capture_output=True).stdout
    tarfile.open(fileobj=io.BytesIO(tar)).extractall(root)
    return root / "results"


def all_check(compare_only=False):
    """Run the whole pipeline (unless compare_only), then compare every result file with the
    committed version (stamps excluded)."""
    ref = committed_results()
    runtime = None
    if not compare_only:
        # stages that skip existing outputs must regenerate them, or the comparison is trivial
        for f in list(Path("results/cp6").glob("*")) + list(Path("results/records").glob("*.parquet")):
            f.unlink()
        t = time.time()
        subprocess.run([sys.executable, "-m", "shahid.reproduce"], check=True)
        runtime = round(time.time() - t)
    checks = {}
    for f in sorted(ref.rglob("*")):
        rel = f.relative_to(ref).as_posix()
        new = Path("results") / rel
        if f.suffix == ".json" and not rel.startswith("repro_check"):
            checks[rel] = new.exists() and strip(json.load(open(f))) == strip(json.load(open(new)))
        elif f.suffix == ".parquet" and "__groups" not in rel:
            checks[rel] = new.exists() and pd.read_parquet(f).equals(pd.read_parquet(new))
    cmd = "python -m shahid.verify_repro --all" + (" --compare-only" if compare_only else "")
    out = {"stamp": stamp({"mode": "all", "compare_only": compare_only}, cmd),
           "runtime_s": runtime, "checks": checks, "all_identical": all(checks.values()),
           "differences": [k for k, v in checks.items() if not v]}
    write_json("results/repro_check_all.json", out)
    print("files", len(checks), "differences", out["differences"])


def summary():
    """Counts behind the reproducibility claims (ledger CP10-REC, CP11-REPRO, CP11-REPRO2)."""
    out = {"stamp": stamp({}, "python -m shahid.verify_repro --summary")}
    for f in ["repro_check_all.json", "repro_check_fresh_clone.json"]:
        d = json.load(open(Path("results") / f))
        out[f] = {"n_files": len(d["checks"]), "n_identical": sum(d["checks"].values()),
                  "n_differences": len(d["differences"]),
                  "n_parquet_differences": sum(x.endswith(".parquet") for x in d["differences"])}
    v = json.load(open("results/records/verify.json"))
    out["records/verify.json"] = {"n_checked": v["checked"], "n_mismatches": len(v["mismatches"])}
    write_json("results/repro_summary.json", out)
    print(json.dumps(out, indent=1))


def main():
    if "--summary" in sys.argv:
        return summary()
    if "--all" in sys.argv:
        return all_check("--compare-only" in sys.argv)
    if "--long" in sys.argv:
        return long_check()
    ref = Path(tempfile.mkdtemp())
    for f in [*JSON_STAGES.values(), "decision_log_demo.jsonl"]:
        shutil.copy(Path("results") / f, ref / f)
    out = {"stamp": stamp({"stages": list(JSON_STAGES), "tables": TABLES},
                          "python -m shahid.verify_repro"), "checks": {}}
    for stage, f in JSON_STAGES.items():
        subprocess.run([sys.executable, "-m", f"shahid.{stage}"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        same = strip(json.load(open(ref / f))) == strip(json.load(open(Path("results") / f)))
        out["checks"][f] = same
    subprocess.run([sys.executable, "-m", "shahid.explain"], check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    rec = lambda p: [{k: v for k, v in json.loads(l)["record"].items() if k != "detector_version"}
                     for l in open(p, encoding="utf8")]
    out["checks"]["decision_log_demo.jsonl"] = rec(ref / "decision_log_demo.jsonl") == \
        rec("results/decision_log_demo.jsonl")
    regen = Path(tempfile.mkdtemp()) / "baseline"
    subprocess.run([sys.executable, "-m", "shahid.scenario", "configs/baseline.yaml", str(regen)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for t in TABLES:
        a = pd.read_parquet(f"dataset/baseline_semiurb5/{t}.parquet")
        b = pd.read_parquet(regen / f"{t}.parquet")
        out["checks"][f"dataset/baseline_semiurb5/{t}"] = bool(a.equals(b))
    out["all_identical"] = all(out["checks"].values())
    from shahid import commits  # the compared files' stamps cite commits that exist here
    out["stamp_commits"] = commits.check(commits.stamp_hashes())
    out["stamp_commits_resolve"] = not out["stamp_commits"]["missing"]
    write_json("results/repro_check.json", out)
    print(out["checks"], "ALL IDENTICAL" if out["all_identical"] else "DIFFERENCES FOUND")


if __name__ == "__main__":
    main()
