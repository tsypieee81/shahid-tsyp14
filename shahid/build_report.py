"""Tooling: build an optional PDF of docs/EXTENDED_REPORT.md with Tectonic (no new dependency).

Run: python -m shahid.build_report   (writes docs/build/report.pdf; not tracked)
Converts the Markdown subset used by the report to LaTeX: headings (# title, ## section, ### subsection,
#### paragraph heading), paragraphs, **bold**, *italic*, `code`, [text](link), bullet and numbered lists
(one nesting level), pipe tables (longtable), images ![caption](path), block quotes and fenced code.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

from shahid.build_proposal import tectonic

SRC, OUT = Path("docs/EXTENDED_REPORT.md"), Path("docs/build")
SYM = {"≤": r"$\le$", "≥": r"$\ge$", "→": r"$\rightarrow$", "←": r"$\leftarrow$", "×": r"$\times$",
       "−": r"$-$", "±": r"$\pm$", "≈": r"$\approx$", "√": r"$\surd$", "✓": r"$\checkmark$", "≠": r"$\neq$"}
PREAMBLE = r"""\documentclass[10pt,a4paper]{article}
\usepackage[margin=2cm]{geometry}
\usepackage{fontspec}
\setmainfont{texgyretermes}[Extension=.otf, UprightFont=*-regular, BoldFont=*-bold, ItalicFont=*-italic, BoldItalicFont=*-bolditalic]
\setsansfont{texgyreheros}[Extension=.otf, UprightFont=*-regular, BoldFont=*-bold, ItalicFont=*-italic, BoldItalicFont=*-bolditalic]
\setmonofont{texgyrecursor}[Extension=.otf, UprightFont=*-regular, BoldFont=*-bold, ItalicFont=*-italic, BoldItalicFont=*-bolditalic, Scale=0.95]
\usepackage{unicode-math}
\setmathfont{texgyretermes-math.otf}
\usepackage{graphicx,booktabs,longtable,array,xcolor,enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyvrb}
\setlist{leftmargin=1.4em, itemsep=1pt, topsep=3pt, parsep=0pt}
\setlength{\parskip}{4pt}\setlength{\parindent}{0pt}
\renewcommand{\arraystretch}{1.15}
\setcounter{tocdepth}{2}
\hypersetup{pdftitle={SHAHID report}, pdfauthor={Anonymous submission}}
\begin{document}
"""


def esc(s):
    s = s.replace("\\", "\x00")
    for a, b in [("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
                 ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")]:
        s = s.replace(a, b)
    s = s.replace("\x00", r"\textbackslash{}")
    for a, b in SYM.items():
        s = s.replace(a, b)
    return s


def inline(s):
    """Inline Markdown -> LaTeX; code spans are protected first."""
    parts = re.split(r"(`[^`]+`)", s)
    out = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            out.append(r"\texttt{" + esc(p[1:-1]).replace("/", r"/\allowbreak{}").replace(r"\_", r"\_\allowbreak{}") + "}")
            continue
        p = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: "\x01" + m.group(1) + "\x02" + m.group(2) + "\x03", p)
        p = esc(p)
        p = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", p)
        p = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\\emph{\1}", p)

        def link(m):
            text, url = m.group(1), m.group(2)
            url_raw = url.replace(r"\_", "_").replace(r"\#", "#").replace(r"\%", "%").replace(r"\&", "&")
            if url_raw.startswith("http"):
                return text + r"\footnote{\url{" + url_raw + "}}"
            return text
        p = re.sub("\x01(.*?)\x02(.*?)\x03", link, p)
        out.append(p)
    return "".join(out)


def table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], [r for r in cells[2:]]
    n = len(head)
    widths = [max(len(r[i]) if i < len(r) else 0 for r in [head] + body) for i in range(n)]
    widths = [min(max(w, 6), 90) for w in widths]
    total = sum(widths)
    spec = "".join(r">{\raggedright\arraybackslash}p{%.3f\linewidth}" % (0.97 * w / total - 0.012) for w in widths)
    lines = [r"{\footnotesize", r"\begin{longtable}{@{}" + spec + "@{}}", r"\toprule",
             " & ".join(r"\textbf{" + inline(h) + "}" for h in head) + r" \\", r"\midrule", r"\endhead"]
    for r in body:
        r = (r + [""] * n)[:n]
        lines.append(" & ".join(inline(c) for c in r) + r" \\")
    lines += [r"\bottomrule", r"\end{longtable}}"]
    return "\n".join(lines)


def convert(md):
    out, i, L = [], 0, md.splitlines()
    title_done = False
    while i < len(L):
        ln = L[i]
        if ln.startswith("```"):
            j = i + 1
            while j < len(L) and not L[j].startswith("```"):
                j += 1
            out.append(r"\begin{Verbatim}[fontsize=\footnotesize]" + "\n" + "\n".join(L[i + 1:j]) + "\n" + r"\end{Verbatim}")
            i = j + 1
            continue
        m = re.match(r"^(#{1,4}) (.*)", ln)
        if m:
            lvl, text = len(m.group(1)), inline(m.group(2))
            if lvl == 1 and not title_done:
                out.append(r"\begin{center}{\LARGE\bfseries " + text + r"}\end{center}")
                title_done = True
            elif lvl == 1:
                out.append(r"\section*{" + text + "}")
            else:
                out.append({2: r"\section{", 3: r"\subsection{", 4: r"\paragraph{"}[lvl] + text + "}")
            i += 1
            continue
        if ln.strip() == "[TOC]":
            out.append(r"\tableofcontents\newpage")
            i += 1
            continue
        if ln.strip() == "[NEWPAGE]":
            out.append(r"\newpage")
            i += 1
            continue
        if ln.startswith("|"):
            j = i
            while j < len(L) and L[j].startswith("|"):
                j += 1
            out.append(table(L[i:j]))
            i = j
            continue
        m = re.match(r"^!\[(.*)\]\((.*)\)\s*$", ln)
        if m:
            out.append(r"\begin{figure}[h]\centering\includegraphics[width=0.95\linewidth]{" + Path(os.path.relpath(SRC.parent / m.group(2), OUT)).as_posix()
                       + r"}\par\smallskip{\small\itshape " + inline(m.group(1)) + r"}\end{figure}")
            i += 1
            continue
        if re.match(r"^\s*([-*]|\d+\.) ", ln):
            j, items = i, []
            while j < len(L) and (re.match(r"^\s*([-*]|\d+\.) ", L[j]) or (L[j].startswith("  ") and L[j].strip())):
                items.append(L[j])
                j += 1
            out.append(lists(items))
            i = j
            continue
        if ln.startswith(">"):
            j, q = i, []
            while j < len(L) and L[j].startswith(">"):
                q.append(L[j][1:].strip())
                j += 1
            out.append(r"\begin{quote}\itshape " + inline(" ".join(q)) + r"\end{quote}")
            i = j
            continue
        if not ln.strip() or ln.strip() == "---":
            out.append("")
            i += 1
            continue
        j, para = i, []
        while j < len(L) and L[j].strip() and not re.match(r"^(#|\||!\[|```|>|\s*([-*]|\d+\.) )", L[j]):
            para.append(L[j].strip())
            j += 1
        out.append(inline(" ".join(para)))
        i = j
    return "\n".join(out)


def lists(items):
    """Bullet/numbered list with one nesting level (two-space indent); continuation lines join the item."""
    merged = []
    for ln in items:
        if re.match(r"^\s*([-*]|\d+\.) ", ln):
            merged.append(ln)
        else:
            merged[-1] += " " + ln.strip()
    out, stack = [], []
    for ln in merged:
        depth = (len(ln) - len(ln.lstrip(" "))) // 2
        kind = "enumerate" if re.match(r"^\s*\d+\. ", ln) else "itemize"
        text = re.sub(r"^\s*([-*]|\d+\.) ", "", ln)
        while len(stack) > depth + 1:
            out.append(r"\end{" + stack.pop() + "}")
        if len(stack) < depth + 1:
            out.append(r"\begin{" + kind + "}")
            stack.append(kind)
        out.append(r"\item " + inline(text))
    while stack:
        out.append(r"\end{" + stack.pop() + "}")
    return "\n".join(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tex = OUT / "report.tex"
    tex.write_text(PREAMBLE + convert(SRC.read_text(encoding="utf8")) + "\n\\end{document}\n", encoding="utf8")
    r = subprocess.run([tectonic(), "-X", "compile", "--keep-logs", "--outdir", str(OUT), str(tex)])
    if r.returncode:
        sys.exit("report build failed: see docs/build/report.log")
    print("written", OUT / "report.pdf")


if __name__ == "__main__":
    main()
