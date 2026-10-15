"""Tooling: every commit cited by a result stamp or by the claims ledger must exist in this repository.

Used by `python -m shahid.check_numbers` (level 4) and `python -m shahid.verify_repro`. A fresh clone
needs the full history (the CI workflow fetches every branch and tag) for cited commits to resolve.
"""
import json
import re
import subprocess
from pathlib import Path

HEX = re.compile(r"\b[0-9a-f]{7,40}\b")


def exists(h):
    return subprocess.run(["git", "cat-file", "-e", f"{h}^{{commit}}"], capture_output=True).returncode == 0


def check(hashes):
    """Counts of cited hashes found in the repository, and the list of those missing."""
    out = {"found": 0, "missing": []}
    for h in sorted(set(hashes)):
        if exists(h.split("-")[0]):
            out["found"] += 1
        else:
            out["missing"].append(h)
    return out


def ledger_hashes(path="docs/CLAIMS_LEDGER.md"):
    hs = []
    for ln in Path(path).read_text(encoding="utf8").splitlines():
        cols = [c.strip() for c in ln.split("|")]
        if len(cols) > 6 and re.match(r"^[A-Z][A-Z0-9-]*$", cols[1] or ""):
            hs += HEX.findall(cols[5])
    return hs


def stamp_hashes(root="results"):
    hs = []
    for f in Path(root).rglob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        stack = [d]
        while stack:
            o = stack.pop()
            if isinstance(o, dict):
                if isinstance(o.get("stamp"), dict) and isinstance(o["stamp"].get("commit"), str):
                    hs += HEX.findall(o["stamp"]["commit"])
                stack += list(o.values())
            elif isinstance(o, list):
                stack += o
    return hs
