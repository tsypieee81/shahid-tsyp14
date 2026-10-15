"""Tooling: build the submission paper PDF from proposal/main.tex with Tectonic (XeTeX).

Run: python -m shahid.build_proposal --draft    placeholders printed in red (default)
     python -m shahid.build_proposal --final    stops with the list of unfilled placeholders
Writes proposal/build/main.pdf and copies it to SHAHID_Phase1_Proposal.pdf. Tectonic is found on PATH, in $TECTONIC, or in the per-user install
folder %LOCALAPPDATA%/Programs/tectonic.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

SRC = Path("proposal")
PDF = Path("SHAHID_Phase1_Proposal.pdf")


def tectonic():
    for c in [os.environ.get("TECTONIC"), shutil.which("tectonic"),
              str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/tectonic/tectonic.exe")]:
        if c and Path(c).is_file():
            return c
    sys.exit("tectonic not found: install it (https://tectonic-typesetting.github.io) or set TECTONIC")


def main(argv):
    final = "--final" in argv
    mode = SRC / "buildmode.tex"
    mode.write_text("\\finaltrue\n" if final else "\\finalfalse\n", encoding="utf8")
    out = SRC / "build"
    out.mkdir(exist_ok=True)
    try:
        r = subprocess.run([tectonic(), "-X", "compile", "--keep-logs", "--outdir", str(out), str(SRC / "main.tex")])
    finally:
        mode.unlink()
    if r.returncode:
        log = out / "main.log"
        if final and log.exists():
            text = log.read_text(encoding="utf8", errors="replace")
            if "UNFILLED PLACEHOLDERS" in text:
                print(text[text.index("UNFILLED PLACEHOLDERS"):].split("\n\n")[0])
        sys.exit(f"build failed ({'final' if final else 'draft'} mode)")
    clean_metadata(out / "main.pdf", PDF)
    print("written", PDF, "(final)" if final else "(draft)")


def clean_metadata(src, dst):
    """Keep only the title and an anonymous author in the PDF information dictionary (no producer or
    creator tool names). Needs pypdf (requirements-dev.txt); without it the PDF is copied unchanged."""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        shutil.copyfile(src, dst)
        print("pypdf not installed: PDF metadata left as produced")
        return
    title = (PdfReader(src).metadata or {}).get("/Title", "")
    w = PdfWriter(clone_from=src)
    w.metadata = None
    w.add_metadata({"/Title": title, "/Author": "Anonymous"})
    with open(dst, "wb") as f:
        w.write(f)


if __name__ == "__main__":
    main(sys.argv[1:])
