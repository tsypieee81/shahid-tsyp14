"""Repository hygiene for the submission: the dataset size the README states, no local absolute
paths or user names in tracked files, and internal Markdown links that resolve."""
import re
import subprocess
from pathlib import Path

import pytest


def tracked():
    try:
        out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    return [Path(p) for p in out.splitlines() if Path(p).is_file()]


def test_readme_states_the_tracked_dataset_size():
    size = sum(p.stat().st_size for p in tracked() if p.parts[0] == "dataset") / 1e6
    stated = re.search(r"(\d+\.\d) MB tracked", Path("README.md").read_text(encoding="utf8"))
    assert stated and abs(float(stated.group(1)) - size) < 0.1, (size, stated)


TEXT = {".py", ".md", ".yaml", ".yml", ".json", ".jsonl", ".txt", ".lock", ".ipynb", ".cfg", ".toml"}
LOCAL = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]|/home/[a-z]|/Users/[A-Za-z]|AppData[\\/]")


def test_no_local_absolute_paths_in_tracked_text_files():
    bad = [str(p) for p in tracked() if p.suffix in TEXT
           and LOCAL.search(p.read_text(encoding="utf8", errors="ignore"))]
    assert not bad, bad


LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def test_internal_markdown_links_resolve():
    bad = []
    for p in tracked():
        if p.suffix != ".md":
            continue
        for target in LINK.findall(p.read_text(encoding="utf8", errors="ignore")):
            if re.match(r"[a-z]+:", target):  # http(s), mailto
                continue
            if not (p.parent / target).exists():
                bad.append(f"{p} -> {target}")
    assert not bad, bad
