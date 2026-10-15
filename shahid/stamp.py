"""Stamp every result file with commit, config hash and date. Origin: ORIGINAL."""
import datetime, hashlib, json, subprocess, sys, platform


def git_commit():
    try:
        h = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
        # generated results/ files do not count: a runner writing several result files would otherwise
        # stamp every file after the first as dirty; code, configs and docs still do
        dirty = subprocess.call(["git", "diff", "--quiet", "HEAD", "--", ".", ":(exclude)results"]) != 0
        return h + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def config_hash(cfg):
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest()[:12]


def stamp(cfg, command):
    return {"commit": git_commit(), "config_hash": config_hash(cfg), "config": cfg,
            "command": command, "date": datetime.datetime.now().isoformat(timespec="seconds"),
            "python": sys.version.split()[0], "platform": platform.platform()}


def write_json(path, payload):
    with open(path, "w") as f:
        json.dump(payload, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
