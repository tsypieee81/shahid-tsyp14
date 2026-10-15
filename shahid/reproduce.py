"""Regenerate every result and figure in order. Cross-platform (pure Python entry points).

Run: python -m shahid.reproduce [--from STAGE]
Stages run as separate processes so each writes its own stamped result file.
Rough runtimes on a 24-thread laptop are in docs/REPRODUCE.md.
"""
import platform
import subprocess
import sys
import time

STAGES = ["cp1_facts", "cp1_diversity", "cp3_checks", "cp4_expected_load", "cp5_gap",
          "cp5_compare", "cp6_sweep", "cp6_summary", "cp7_heldout", "leak_audit",
          "cp8_single_meter", "explain", "audit_faults", "audit", "records", "iforest", "cp10",
          "cp10_world", "cp11_sims", "cp11 select", "cp11 evaluate", "cp12", "figures", "make_docs"]


def main(argv):
    start = STAGES.index(argv[argv.index("--from") + 1]) if "--from" in argv else 0
    print(f"{platform.system()} {platform.release()}, Python {platform.python_version()}")
    for s in STAGES[start:]:
        t = time.time()
        print(f"== {s}", flush=True)
        mod, *args = s.split()
        r = subprocess.run([sys.executable, "-m", f"shahid.{mod}", *args])
        if r.returncode:
            sys.exit(f"stage {s} failed with exit code {r.returncode}")
        print(f"== {s} done in {time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
