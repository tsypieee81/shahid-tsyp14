"""Tooling: every number in every table of the LaTeX proposal must appear verbatim, exactly as
printed, in docs/RESULTS.md (generated from result files), the claims ledger, a study README, or a
tagged allowlist entry.

Run: python -m shahid.check_tables   (prints unmatched cells per table; exit 1 if any)
Stricter than shahid.check_numbers: no rounding, no x100, no complements, so a mistyped digit is
caught unless the mistyped string happens to be printed elsewhere in those documents.
"""
import glob
import re
import sys
from pathlib import Path

import yaml

from shahid.check_numbers import ledger_rows, numbers_in

SOURCES = ["docs/RESULTS.md", *sorted(glob.glob("docs/studies/*/README.md"))]
TABLE = re.compile(r"\\caption\{(.*?)\}.*?\\begin\{tabularx?\}(.*?)\\end\{tabularx?\}", re.S)


def reference_tokens():
    lines = ledger_rows() + [x for f in SOURCES for x in Path(f).read_text(encoding="utf8").splitlines()]
    return {t for line in lines for t in numbers_in(line)}  # per line: the skip patterns are line-based


def main():
    ref = reference_tokens()
    allow = {str(k) for k in (yaml.safe_load(open("docs/number_allowlist.yaml", encoding="utf8"))
                              .get("global") or {})}
    n_tables = n_cells = 0
    bad = []
    for f in sorted(glob.glob("proposal/sections/*.tex")):
        for cap, body in TABLE.findall(Path(f).read_text(encoding="utf8")):
            n_tables += 1
            body = re.sub(r"\\(cite|ref)\{[^}]*\}", " ", body)  # citation and section numbers
            for row in body.split(r"\\"):
                for tok in numbers_in(row.replace("--", "–")):
                    n_cells += 1
                    if tok not in allow and tok not in ref:
                        bad.append((f, cap[:50], tok))
    for f, cap, tok in bad:
        print(f"{f}  [{cap}]  {tok}")
    print(f"TABLES: {n_tables} tables, {n_cells} numbers checked, unmatched {len(bad)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
