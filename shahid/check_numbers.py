"""Number integrity: every number in the proposal-facing documents must match a ledger entry or a
value in a result file (at its printed precision), or be listed in docs/number_allowlist.yaml with a
reason (parameter, date, design choice, assumption...).

Run: python -m shahid.check_numbers   (prints unmatched numbers; exit 1 if any)
     python -m shahid.check_numbers --doc proposal.docx [--ledger extra.md] [--results a.json,b.json]
         External document mode (.docx, .txt or .md): every number in the document must match the
         claims ledger (plus an optional extra ledger file, e.g. proposed rows from another branch)
         or a value in a result file the document cites (results/....json in its text) or that is
         listed with --results, at its printed precision.
"""
import glob
import json
import math
import re
import sys
from pathlib import Path

import yaml

DOCS = ["README.md", "docs/METHOD.md", "docs/REPRODUCE.md", "docs/COMPLIANCE.md", "docs/BRIEF_COVERAGE.md", "docs/BUSINESS_CASE.md", "docs/tunisia/README.md", "docs/tunisia/TUNISIA_COMPARISON.md", "docs/PRELIMINARY_DESIGN.md",
        *sorted(glob.glob("docs/studies/*/README.md")), "docs/process/AUDIT.md", "docs/RESULTS.md",
        *sorted(glob.glob("docs/process/checkpoints/CP*.md")), *sorted(Path(x).as_posix() for x in glob.glob("proposal/sections/*.tex"))]
# LaTeX: comments, cross-reference and file commands, and layout lengths are not numbers of the paper
TEX_SKIP = [re.compile(p) for p in [r"(?<!\\)%.*", r"\\(?:label|ref|eqref|cite|input|includegraphics|url)(?:\[[^\]]*\])?\{[^}]*\}",
                                    r"\d*\.?\d+\\(?:textwidth|columnwidth|linewidth)", r"\b\d+(?:\.\d+)?(?:pt|mm|cm|em|ex)\b",
                                    r"\\setlength\{[^}]*\}\{[^}]*\}", r"\\multicolumn\{\d+\}", r"\{@\{\}[^}]*\}"]]


def tex_text(text):
    for s in TEX_SKIP:
        text = s.sub(" ", text)
    return text
NUM = re.compile(r"(?<![\w.#@-])(−|-)?(\d{1,3}(?: \d{3})+|\d+)(?:\.(\d+))?(?![\w])")
SKIP = [re.compile(p) for p in [r"`[^`]*`", r"\b\d{4}-\d{2}-\d{2}\b", r"\b\d{1,2}:\d{2}\b",
                                r"\[[^\]]*\]\([^)]*\)", r"\b[0-9a-f]{7,40}\b", r"^\s*\d+\.\s",
                                r"<[^>]+>", r"CP\d+(-[A-Za-z0-9]+)?", r"\b[A-Z]{1,3}\d*-\d+\b",
                                r"§\s?\d+", r"\bd\s?=\s?[\d.]+", r"\bseeds? [\d–, ]+",
                                # section references ("Section 5.4", "Sections 6.9 and 11") are identifiers
                                r"\bSections? \d+(?:\.\d+)*(?:,? (?:and|or|to) \d+(?:\.\d+)*)*",
                                r"^#+ \d+(?:\.\d+)*"]]  # numbered Markdown headings


def harvest(obj, out):
    if isinstance(obj, dict):
        for v in obj.values():
            harvest(v, out)
    elif isinstance(obj, list):
        if len(obj) <= 5000:
            for v in obj:
                harvest(v, out)
    elif isinstance(obj, str) and re.fullmatch(r"-?\d+(\.\d+)?", obj.strip()):
        out.add(float(obj))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if obj == obj and abs(obj) != float("inf"):
            out.add(float(obj))


def numbers_in(text):
    for s in SKIP:
        text = s.sub(" ", text)
    for m in NUM.finditer(text):
        sign = "-" if m.group(1) else ""
        whole = m.group(2).replace(" ", "")
        frac = m.group(3)
        yield sign + whole + ("." + frac if frac else "")


def rounded_sets(vals, max_dec=5):
    """For each printed precision d: |v|, |v|*100 and, for rates in [0, 1], the complement 1 - v
    (coverage = 1 - abstention) and its percentage, rounded to d decimals."""
    out = {}
    for d in range(max_dec + 1):
        acc = set()
        for v in vals:
            acc.update((round(abs(v), d), round(abs(v) * 100, d)))
            if 0 <= v <= 1:
                acc.update((round(1 - v, d), round((1 - v) * 100, d)))
        out[d] = acc
    return out


def matches(tok, sets):
    d = len(tok.split(".")[1]) if "." in tok else 0
    return d in sets and round(abs(float(tok)), d) in sets[d]


def ledger_rows(path="docs/CLAIMS_LEDGER.md"):
    rows = []
    for line in Path(path).read_text(encoding="utf8").splitlines():
        if line.startswith("| ") and not line.startswith("| ID") and not line.startswith("|--"):
            rows.append(line)
    return rows


def level2(rows):
    """Ledger row numbers (claim column) must match values in the result files the row cites."""
    allow = (yaml.safe_load(open("docs/number_allowlist.yaml", encoding="utf8")) or {}).get("ledger") or {}
    total, bad = 0, []
    for r in rows:
        cells = [c.strip() for c in r.strip("|").split("|")]
        if len(cells) < 3:
            continue
        rid, claim, src = cells[0], cells[1], " ".join(cells[2:3])
        paths = re.findall(r"results/[\w./*{},_-]+", src)
        files = []
        for p in paths:
            p = p.rstrip(".,")
            if "{" in p:  # results/cp6/{a,b}.json
                head, tail = p.split("{", 1)
                inner, rest = tail.split("}", 1)
                for part in inner.split(","):
                    files += glob.glob(head + part + rest)
            else:
                files += glob.glob(p)
        vals = set()
        for f in files:
            if f.endswith(".json"):
                harvest(json.load(open(f, encoding="utf8")), vals)
        if not vals:
            continue  # source not machine-readable here (parquet, test output, arithmetic)
        sets = rounded_sets(vals)
        for tok in numbers_in(claim):
            total += 1
            if not matches(tok, sets) and tok not in {str(k) for k in allow.get(rid, {})}:
                bad.append((rid, tok, claim[:100]))
    return total, bad


def check():
    rows = ledger_rows()
    ledger_vals = set()
    for r in rows:
        for tok in numbers_in(r):
            ledger_vals.add(float(tok))
    sets = rounded_sets(ledger_vals)
    allow = yaml.safe_load(open("docs/number_allowlist.yaml", encoding="utf8")) or {}
    allowed = {str(k) for k in (allow.get("global") or {})}
    per_file = {f: {str(k) for k in v} for f, v in (allow.get("files") or {}).items()}
    total, bad = 0, []
    for f in DOCS:
        if not Path(f).exists():
            continue
        raw = Path(f).read_text(encoding="utf8")
        text = tex_text(raw) if f.endswith(".tex") else raw
        cited = set()  # values of the result files this document cites (LaTeX: also in % source comments)
        for pth in set(re.findall(r"results/[\w./*-]+\.json", raw)):
            for g in glob.glob(pth):
                harvest(json.load(open(g, encoding="utf8")), cited)
        csets = rounded_sets(cited)
        for ln, line in enumerate(text.splitlines(), 1):
            for tok in numbers_in(line):
                total += 1
                if (tok in allowed or tok in per_file.get(f, set()) or matches(tok, sets)
                        or matches(tok, csets)):
                    continue
                bad.append((f, ln, tok, line.strip()[:110]))
    return total, bad


GENERATED = ["docs/RESULTS.md"]
TAGS = ("[date]", "[identifier]", "[parameter]", "[environment]", "[derived]", "[count]")
EST = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?) \((\d+(?:\.\d+)?)–(\d+(?:\.\d+)?)\)")


def decimals_allowed(lo, hi):
    """Rounding rule (CP12): an estimate gets the decimal place of the leading digit of its 95%
    interval half-width; the interval bounds get one place more. A rate (interval inside [0, 1]) keeps
    at least two decimals, so one rate is printed the same way in every table (e.g. 0.42, not 0.4)."""
    hw = (float(hi) - float(lo)) / 2
    d = 3 if hw <= 0 else max(0, -int(math.floor(math.log10(hw))))
    return max(d, 2) if 0 <= float(lo) and float(hi) <= 1 else d


def level3():
    """Every 'estimate (lo–hi)' in the generated documents obeys the rounding rule."""
    total, bad = 0, []
    for f in GENERATED:
        for ln, line in enumerate(Path(f).read_text(encoding="utf8").splitlines(), 1):
            for m in EST.finditer(line):
                total += 1
                d = decimals_allowed(m.group(2), m.group(3))
                dec = lambda s: len(s.split(".")[1]) if "." in s else 0
                if dec(m.group(1)) > d or dec(m.group(2)) > d + 1 or dec(m.group(3)) > d + 1:
                    bad.append((f, ln, m.group(0), d))
    return total, bad


def allowlist_tags():
    """Every allowlisted number carries a non-result category tag; returns counts per tag."""
    allow = yaml.safe_load(open("docs/number_allowlist.yaml", encoding="utf8")) or {}
    reasons = list((allow.get("global") or {}).values())
    for sect in ["files", "ledger"]:
        for v in (allow.get(sect) or {}).values():
            reasons += list(v.values())
    counts = {t: sum(r.startswith(t) for r in reasons) for t in TAGS}
    untagged = [r for r in reasons if not r.startswith(TAGS)]
    return counts, untagged


def document_text(path):
    """Plain text of a .docx (paragraphs from word/document.xml, standard library only) or text file."""
    p = Path(path)
    if p.suffix.lower() == ".docx":
        import zipfile
        from xml.etree import ElementTree
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        root = ElementTree.fromstring(zipfile.ZipFile(p).read("word/document.xml"))
        paras = ("".join(t.text or "" for t in para.iter(ns + "t")) for para in root.iter(ns + "p"))
        return "\n".join(paras)
    text = p.read_text(encoding="utf8")
    return tex_text(text) if p.suffix.lower() == ".tex" else text


def check_external(path, extra_ledger=None, result_files=()):
    """Numbers in an external document that match neither the ledger(s) nor a result file the
    document cites (results/....json in its text) or that is named in result_files. Matching against
    ALL result files would be vacuous: about 23 000 harvested values match almost any number."""
    rows = ledger_rows() + (ledger_rows(extra_ledger) if extra_ledger else [])
    lv = set()
    for r in rows:
        for tok in numbers_in(r):
            lv.add(float(tok))
    text = document_text(path)
    rv = set()
    for pth in set(re.findall(r"results/[\w./*-]+\.json", text)) | set(result_files):
        for f in glob.glob(pth):
            harvest(json.load(open(f, encoding="utf8")), rv)
    lsets, rsets = rounded_sets(lv), rounded_sets(rv)
    allow = yaml.safe_load(open("docs/number_allowlist.yaml", encoding="utf8")) or {}
    allowed = {str(k) for k in (allow.get("global") or {})}
    allowed |= {str(k) for k in ((allow.get("files") or {}).get(Path(path).as_posix()) or {})}  # this document's entries
    total, bad = 0, []
    for ln, line in enumerate(text.splitlines(), 1):
        for tok in numbers_in(line):
            total += 1
            if tok in allowed or matches(tok, lsets) or matches(tok, rsets):
                continue
            bad.append((ln, tok, line.strip()[:110]))
    return total, bad


def main():
    if "--doc" in sys.argv:
        doc = sys.argv[sys.argv.index("--doc") + 1]
        extra = sys.argv[sys.argv.index("--ledger") + 1] if "--ledger" in sys.argv else None
        files = sys.argv[sys.argv.index("--results") + 1].split(",") if "--results" in sys.argv else ()
        total, bad = check_external(doc, extra, files)
        for ln, tok, line in bad:
            print(f"{doc} paragraph {ln}  {tok}  | {line}")
        print(f"EXTERNAL ({doc}{', extra ledger ' + extra if extra else ''}): checked {total} numbers, "
              f"unmatched {len(bad)}")
        sys.exit(1 if bad else 0)
    total, bad = check()
    for f, ln, tok, line in bad:
        print(f"{f}:{ln}  {tok}  | {line}")
    print(f"LEVEL 1 (documents -> ledger): checked {total} numbers, unmatched {len(bad)}")
    t2, bad2 = level2(ledger_rows())
    for rid, tok, claim in bad2:
        print(f"ledger {rid}  {tok}  | {claim}")
    print(f"LEVEL 2 (ledger -> cited result files): checked {t2} numbers, unmatched {len(bad2)}")
    t3, bad3 = level3()
    for f, ln, s, d in bad3:
        print(f"{f}:{ln}  {s}  | estimate allows {d} decimals")
    print(f"LEVEL 3 (rounding rule in generated documents): checked {t3} estimates, violations {len(bad3)}")
    counts, untagged = allowlist_tags()
    print(f"ALLOWLIST: {counts}; untagged {len(untagged)}")
    from shahid import commits  # every cited commit must exist in this repository
    c4 = {k: commits.check(f()) for k, f in (("ledger", commits.ledger_hashes), ("stamps", commits.stamp_hashes))}
    for k, r in c4.items():
        print(f"LEVEL 4 ({k} commits): found {r['found']}, missing {len(r['missing'])} {r['missing'][:5]}")
    missing4 = any(r["missing"] for r in c4.values())
    sys.exit(1 if bad or bad2 or bad3 or untagged or missing4 else 0)


if __name__ == "__main__":
    main()
