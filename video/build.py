"""Rebuild the SHAHID demo video from scratch into video/build/.

  video/.venv/Scripts/python video/build.py               summary cut: shahid_demo.mp4, _subtitled.mp4, .srt
  video/.venv/Scripts/python video/build.py --cut short   short cut:   shahid_demo_short.mp4, _subtitled.mp4, .srt

Run from the repository root with the video environment. Needs: ffmpeg on PATH (or the winget link), the project
environment .venv (console and checks), the video environment video/.venv (Manim CE, Kokoro, Playwright).
Cuts are defined in video/cuts.py; the summary cut works in build/, any other cut in build/<cut>/.
Steps can be run alone: python video/build.py [--cut NAME] voice cards scenes console assemble
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

VIDEO = Path(__file__).resolve().parent
REPO = VIDEO.parent
BUILD = VIDEO / "build"
FONTS = BUILD / "fonts"
PROJECT_PY = REPO / ".venv" / "Scripts" / "python.exe"
VIDEO_PY = Path(sys.executable)
sys.path.insert(0, str(VIDEO))

from cuts import CUTS  # noqa: E402

LEAD, GAP, TAIL = 0.3, 0.35, 0.5   # s of silence: before a beat, between sentences, after a beat
XFADE = 0.4                        # s crossfade between scenes
FPS = 30
CUT, OUT, ORDER = None, None, None  # set by use_cut()
PORT = 8599
FONT_ZIPS = {"Inter": ("https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip",
                       ["Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf"]),
             "JetBrainsMono": ("https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip",
                               ["JetBrainsMono-Regular.ttf"])}


def use_cut(name):
    """Select a cut of video/cuts.py: its narration, scenes and console script, and its working folder."""
    global CUT, OUT, ORDER
    CUT, OUT = CUTS[name], BUILD if name == "summary" else BUILD / name
    ORDER = list(CUT["narration"])  # scene order; S04Console is the live capture
    OUT.mkdir(parents=True, exist_ok=True)


use_cut("summary")


def ffmpeg():
    exe = shutil.which("ffmpeg") or str(Path(os.environ["LOCALAPPDATA"]) / "Microsoft/WinGet/Links/ffmpeg.exe")
    if not Path(exe).exists() and not shutil.which(exe):
        sys.exit("ffmpeg not found: winget install Gyan.FFmpeg")
    return exe


def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd)[:160])
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def probe_seconds(path):
    out = subprocess.run([ffmpeg(), "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


# ---- 1. fonts (SIL OFL 1.1) ------------------------------------------------------------------------------
def fonts():
    FONTS.mkdir(parents=True, exist_ok=True)
    for name, (url, files) in FONT_ZIPS.items():
        if all((FONTS / f).exists() for f in files):
            continue
        print(f"[fonts] {name}")
        z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url).read()))
        for f in files:
            src = next(n for n in z.namelist() if n.endswith("/" + f) and "/ttf/" in n)
            (FONTS / f).write_bytes(z.read(src))
            lic = next((n for n in z.namelist() if n.upper().endswith(("LICENSE.TXT", "OFL.TXT"))), None)
            if lic:
                (FONTS / f"{name}-LICENSE.txt").write_bytes(z.read(lic))


# ---- 2. narration and beat durations ----------------------------------------------------------------------
def sentences(text):
    return [s for s in re.split(r"(?<=[.?!])\s+", text.strip()) if s]


def voice():
    import numpy as np
    import soundfile as sf
    from tts import SR, speak
    (OUT / "audio").mkdir(parents=True, exist_ok=True)
    durations, cues = {}, {}
    for scene, beats in CUT["narration"].items():
        print(f"[voice] {scene}")
        track, t, durs, sc = [], 0.0, [], []
        for text in beats:
            start = t
            track.append(np.zeros(int(LEAD * SR), np.float32)); t += LEAD
            for i, s in enumerate(sentences(text)):
                a = speak(s, say=CUT["say"], speed=CUT["speed"])
                sc.append([round(t, 3), round(t + len(a) / SR, 3), s])
                track.append(a); t += len(a) / SR
                track.append(np.zeros(int((GAP if i < len(sentences(text)) - 1 else TAIL) * SR), np.float32))
                t += GAP if i < len(sentences(text)) - 1 else TAIL
            durs.append(round(t - start, 3))
        audio = np.concatenate(track)
        sf.write(OUT / "audio" / f"{scene}.wav", audio, SR)
        durations[scene], cues[scene] = durs, sc
    (OUT / "durations.json").write_text(json.dumps(durations, indent=1))
    (OUT / "cues.json").write_text(json.dumps(cues, indent=1))
    total = sum(map(sum, durations.values())) - XFADE * (len(durations) - 1)
    print(f"[voice] total {total:.1f} s")


# ---- 3. work-process cards from the real commands -----------------------------------------------------------
def cards():
    def last(cmd, keep):
        print(f"[cards] {' '.join(cmd)}")
        p = subprocess.run([str(PROJECT_PY), "-m", *cmd], cwd=REPO, capture_output=True, text=True)
        lines = [l.strip() for l in (p.stdout + p.stderr).splitlines() if l.strip()]
        out = [l for l in lines if re.search(keep, l)]
        return {"ok": p.returncode == 0, "lines": out}
    checks = []
    for cmd, keep, show in [(["pytest", "-q", "-p", "no:warnings"], r"\d+ passed", "python -m pytest -q"),
                            (["shahid.check_numbers"], r"^LEVEL [1-3]", "python -m shahid.check_numbers"),
                            (["shahid.check_tables"], r"^TABLES", "python -m shahid.check_tables")]:
        r = last(cmd, keep)
        lines = [re.sub(r"\s*in [\d.]+s.*$", "", l) for l in r["lines"]]  # drop timings: no host detail
        lines = [re.sub(r"\s*\(documents -> ledger\)|\s*\(ledger -> cited result files\)|\s*\(rounding rule in generated documents\)", "", l) for l in lines]
        checks.append({"cmd": show, "ok": r["ok"], "lines": [[l, r["ok"]] for l in lines]})
    log = subprocess.run(["git", "log", "--reverse", "--format=%as|%an|%s"], cwd=REPO, capture_output=True,
                         text=True, check=True).stdout.splitlines()
    reg = [l.split("|", 2) for l in log if re.search(r"registered|committed alone, before", l)]
    pick = [reg[0]] + [r for r in reg if r[2].startswith(("Protocol 05", "Protocol 07b"))][:2]

    def short(s, n=46):
        s = s.split(":")[0] if s.startswith("Protocol") else s.split("(")[0]
        return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"
    commits = [f"{d} · {who} · {short(s.strip()).strip()}" for d, who, s in pick]
    (BUILD / "cards.json").write_text(json.dumps({"checks": checks, "commits": commits}, indent=1), encoding="utf8")
    if not all(c["ok"] for c in checks):
        sys.exit("[cards] a check failed: the narration says every check passes; fix that line first")


# ---- 4. Manim scenes ----------------------------------------------------------------------------------------
def scenes(quality="h"):
    res = {"h": "1920,1080", "l": "854,480"}[quality]
    env = {**os.environ, "SHAHID_DURATIONS": str(OUT / "durations.json")}
    for scene, mod in CUT["files"].items():
        print(f"[scenes] {scene}")
        p = subprocess.run([str(c) for c in [VIDEO_PY, "-m", "manim", f"-q{quality}", "-r", res, "--fps", FPS, "--media_dir", OUT / "media",
                            "--disable_caching", "--progress_bar", "none", "-v", "WARNING", "-o", scene, f"{mod}.py", scene]],
                           cwd=VIDEO / "scenes", capture_output=True, text=True, env=env)
        print(p.stdout[-400:], p.stderr[-2000:] if p.returncode else "")
        if p.returncode or "OVERRUN" in p.stdout:
            sys.exit(f"[scenes] {scene} failed or overran its narration")


def scene_video(scene):
    if scene == "S04Console":
        return OUT / "console.mp4"
    found = sorted((OUT / "media" / "videos" / CUT["files"][scene]).rglob(f"{scene}.mp4"))
    return next((f for f in found if "1080p" in str(f)), found[0])  # a preview render may sit beside it


# ---- 5. console capture ----------------------------------------------------------------------------------------
CURSOR_JS = """
addEventListener('DOMContentLoaded', () => {
  const c = document.createElement('div');
  c.style.cssText = 'position:fixed;left:0;top:0;width:30px;height:30px;margin:-15px 0 0 -15px;border-radius:50%;' +
    'border:2px solid rgba(226,232,240,.9);background:rgba(59,130,246,.25);pointer-events:none;z-index:2147483647;' +
    'transition:transform .12s ease-out';
  document.body.appendChild(c);
  addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
  addEventListener('mousedown', () => c.style.transform = 'scale(.7)', true);
  addEventListener('mouseup', () => c.style.transform = 'scale(1)', true);
});
"""


def uncertain_row(now, onset):
    """Row of the group with this onset in the Uncertain tab at replay time `now`: uncertain groups already
    decided, sorted by onset (results/demo/showcase.json, the file the console replays)."""
    groups = json.loads((REPO / "results/demo/showcase.json").read_text(encoding="utf8"))["groups"]
    rows = sorted(g["onset"][11:16] for g in groups
                  if g["verdict"] == "UNCERTAIN" and g["record"]["decided_at"][11:16] <= now)
    return rows.index(onset)


def console():
    from playwright.sync_api import sync_playwright
    beats = json.loads((OUT / "durations.json").read_text())["S04Console"]
    srv = subprocess.Popen([PROJECT_PY, "-m", "streamlit", "run", "ui/app.py", "--server.headless", "true",
                            "--server.port", str(PORT), "--browser.gatherUsageStats", "false"], cwd=REPO,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    raw = OUT / "console_raw"
    shutil.rmtree(raw, ignore_errors=True)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://localhost:{PORT}", timeout=1)
                break
            except OSError:
                time.sleep(1)
        with sync_playwright() as p:
            b = p.chromium.launch()
            # warm-up page: reset the operator log so the chain starts at genesis
            w = b.new_page(viewport={"width": 1920, "height": 1080})
            w.goto(f"http://localhost:{PORT}/?scenario=showcase")
            w.get_by_role("button", name="Reset session").click()
            w.wait_for_timeout(2500)
            w.close()
            ctx = b.new_context(viewport={"width": 1920, "height": 1080}, record_video_dir=str(raw),
                                record_video_size={"width": 1920, "height": 1080})
            ctx.add_init_script(CURSOR_JS)
            pg = ctx.new_page()
            t_open = time.monotonic()
            pg.goto(f"http://localhost:{PORT}/?scenario=showcase")
            pg.get_by_text("Present", exact=True).wait_for(timeout=60000)
            pg.wait_for_timeout(2500)
            pg.get_by_text("Present", exact=True).click()
            pg.mouse.move(960, 600)
            pg.wait_for_timeout(2500)
            t0 = time.monotonic()
            marks = [t0]

            def glide(x, y, steps=18):
                pg.mouse.move(x, y, steps=steps)

            def click(loc, settle=1100):
                loc.scroll_into_view_if_needed()
                bb = loc.bounding_box()
                glide(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
                pg.wait_for_timeout(200)
                loc.click()
                pg.wait_for_timeout(settle)

            def until(k):
                left = sum(beats[:k + 1]) - (time.monotonic() - t0)
                if left < -0.3:
                    print(f"[console] beat {k} overran by {-left:.1f} s")
                pg.wait_for_timeout(max(0, left) * 1000)
                marks.append(time.monotonic())

            def hover(loc, wait):
                bb = loc.filter(visible=True).first.bounding_box()
                glide(bb["x"] + min(bb["width"] / 2, 160), bb["y"] + bb["height"] / 2, 22)
                pg.wait_for_timeout(wait)

            def row(k):  # select row k of the queue grid (a canvas: rows are 35 px apart)
                y = 270 + 35 * k
                glide(467, y); pg.wait_for_timeout(200); pg.mouse.click(467, y); pg.wait_for_timeout(1500)

            flag = {}

            def replay():
                """The replay runs on to 14:15 (13:00, 13:30, 14:15): every queue holds an item, and the midday
                group is decided at 14:00."""
                for _ in range(3):
                    click(pg.get_by_role("button", name="Next event"), 1000)
                pg.evaluate("document.activeElement && document.activeElement.blur()")  # no lingering tooltip
                glide(960, 560)

            def comms():
                """The concentrator failure and its evidence card (queue view: nothing scrolls under the chips)."""
                click(pg.get_by_role("button", name="inbox"))
                click(pg.get_by_role("tab", name=re.compile("Comms unconfirmed")))
                row(0)
                hover(pg.get_by_text(re.compile("Expected if only data lost", re.I)), 2400)
                hover(pg.get_by_text(re.compile("Probability of a communication failure", re.I)), 2200)
                hover(pg.get_by_text(re.compile("stopped reporting at")), 3200)
                hover(pg.get_by_text("automatic", exact=True), 500)

            def outage():
                """The outage waits for a person, who approves it."""
                click(pg.get_by_role("tab", name=re.compile("Outages awaiting approval")))
                row(0)
                hover(pg.get_by_role("button", name="Approve"), 700)
                click(pg.get_by_role("button", name="Approve"))

            def uncertain():
                """Too close to call: the midday group goes to a supervisor with its evidence."""
                click(pg.get_by_role("tab", name=re.compile("Uncertain")))
                now = re.search(r"2016-06-09 (\d\d:\d\d)", pg.inner_text("body")).group(1)
                row(uncertain_row(now, "12:30"))
                hover(pg.get_by_text(re.compile("Probability of a communication failure", re.I)), 1200)
                click(pg.get_by_role("button", name="Escalate to supervisor"))

            def audit():
                """The hash-chained log; the approval carries the fast-approval flag from here on."""
                click(pg.get_by_role("button", name="receipt_long"), 0)
                flag["at"] = time.monotonic()
                pg.wait_for_timeout(1100)
                click(pg.get_by_role("button", name="Verify chain"), 900)

            def tamper():
                """Change one digit of a logged value in the copy, then verify it."""
                click(pg.get_by_text("Tamper test"), 900)
                ta = pg.locator("textarea").first
                bb = ta.bounding_box(); glide(bb["x"] + 300, bb["y"] + 30)
                new = ta.evaluate("""t => { const i = t.value.indexOf('"seconds": ') + 11; t.focus();
                                             t.setSelectionRange(i, i + 1); return t.value[i] === '7' ? '8' : '7'; }""")
                pg.keyboard.type(new, delay=120)
                pg.wait_for_timeout(300)
                click(pg.get_by_role("button", name="Verify edited copy"), 1200)

            steps = {"replay": replay, "comms": comms, "outage": outage, "uncertain": uncertain, "audit": audit,
                     "tamper": tamper, "audit_and_tamper": lambda: (audit(), tamper())}
            for k, name in enumerate(CUT["console"]):  # one step per console beat
                steps[name]()
                until(k)
            video = pg.video.path()
            ctx.close()
            b.close()
    finally:
        srv.terminate()
    log = [json.loads(l) for l in (REPO / "ui/operator_log.jsonl").read_text(encoding="utf8").splitlines() if l.strip()]
    if not any(e["action"] == "APPROVED" and e["fast"] for e in log):
        sys.exit("[console] the approval was not flagged as fast: the narration and the caption say it is; retake")
    start = marks[0] - t_open
    run([ffmpeg(), "-y", "-ss", f"{start:.3f}", "-i", video, "-t", f"{sum(beats):.3f}", "-vf",
         f"fps={FPS},scale=1920:1080,format=yuv420p", "-an", "-c:v", "libx264", "-crf", "16", OUT / "console_body.mp4"])
    overlay_console(sum(beats), flag["at"] - marks[0])


def fast_seconds():
    """The console's fast-approval threshold (ui/oplog.py FAST_SECONDS), read from its source."""
    v = float(re.search(r"^FAST_SECONDS = ([\d.]+)", (REPO / "ui/oplog.py").read_text(encoding="utf8"), re.M).group(1))
    return f"{v:g}"


def overlay_console(duration, flag_at):
    """SIMULATED and CONSTRUCTED DEMONSTRATION DAY chips on the empty part of the top bar, the section
    lower-third for its first 2.8 s, and the fast-approval caption from `flag_at` (s) to the end, drawn with
    Pillow in the scene palette."""
    from PIL import Image, ImageDraw, ImageFont
    semi = ImageFont.truetype(str(FONTS / "Inter-SemiBold.ttf"), 14)
    reg = ImageFont.truetype(str(FONTS / "Inter-Regular.ttf"), 26)

    def chips():
        im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        x = 800
        for s in ("SIMULATED", "CONSTRUCTED DEMONSTRATION DAY"):
            w = d.textlength(s, font=semi)
            d.rounded_rectangle([x, 95, x + w + 22, 119], 12, fill=(11, 18, 32, 255), outline=(245, 158, 11, 255), width=2)
            d.text((x + 11, 99), s, font=semi, fill=(245, 158, 11, 255))
            x += w + 34
        return im

    def lower():
        im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([24, 990, 360, 1050], 10, fill=(17, 26, 46, 240))
        d.rectangle([40, 1004, 46, 1036], fill=(59, 130, 246, 255))
        d.text((62, 1004), "Working console", font=reg, fill=(148, 163, 184, 255))
        return im
    def caption():
        """Over the empty lower part of the Audit view, above where the subtitles sit."""
        im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        s = f"Approvals under {fast_seconds()} s are flagged (over-trust check)"
        w = d.textlength(s, font=reg)
        x, y = 1145 - w / 2, 860
        d.rounded_rectangle([x - 24, y - 14, x + w + 24, y + 46], 12, fill=(17, 26, 46, 245), outline=(245, 158, 11, 255), width=2)
        d.text((x, y), s, font=reg, fill=(226, 232, 240, 255))
        return im
    chips().save(OUT / "ov_chips.png")
    lower().save(OUT / "ov_lower.png")
    caption().save(OUT / "ov_fast.png")
    a = f"{flag_at:.2f}"
    run([ffmpeg(), "-y", "-i", OUT / "console_body.mp4", "-i", OUT / "ov_chips.png", "-loop", "1", "-t", "3.2",
         "-i", OUT / "ov_lower.png", "-loop", "1", "-t", f"{duration:.3f}", "-i", OUT / "ov_fast.png", "-filter_complex",
         "[2:v]format=rgba,fade=t=in:st=0:d=0.4:alpha=1,fade=t=out:st=2.4:d=0.4:alpha=1[lt];"
         f"[3:v]format=rgba,fade=t=in:st={a}:d=0.3:alpha=1[fc];"
         "[0:v][1:v]overlay=0:0[a];[a][lt]overlay=0:0:eof_action=pass[b];"
         f"[b][fc]overlay=0:0:enable='gte(t,{a})',format=yuv420p[v]",
         "-map", "[v]", "-t", f"{duration:.3f}", "-c:v", "libx264", "-crf", "16", OUT / "console.mp4"])


# ---- 6. assembly, loudness, subtitles ---------------------------------------------------------------------------
def assemble():
    durs = json.loads((OUT / "durations.json").read_text())
    cues = json.loads((OUT / "cues.json").read_text())
    seg = OUT / "segments"
    seg.mkdir(exist_ok=True)
    lens = []
    for s in ORDER:
        D = sum(durs[s])
        lens.append(D)
        run([ffmpeg(), "-y", "-i", scene_video(s), "-i", OUT / "audio" / f"{s}.wav", "-filter_complex",
             f"[0:v]fps={FPS},scale=1920:1080,tpad=stop_mode=clone:stop_duration=3,trim=duration={D:.3f},setpts=PTS-STARTPTS,format=yuv420p[v];"
             f"[1:a]aresample=48000,apad,atrim=duration={D:.3f},asetpts=PTS-STARTPTS[a]",
             "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "16", "-c:a", "pcm_s16le", seg / f"{s}.mkv"])
    # crossfade chain
    inputs, fv, fa, off = [], [], [], 0.0
    for i, s in enumerate(ORDER):
        inputs += ["-i", seg / f"{s}.mkv"]
    v, a = "[0:v]", "[0:a]"
    for i in range(1, len(ORDER)):
        off += lens[i - 1] - XFADE
        fv.append(f"{v}[{i}:v]xfade=transition=fade:duration={XFADE}:offset={off:.3f}[v{i}]")
        fa.append(f"{a}[{i}:a]acrossfade=d={XFADE}[a{i}]")
        v, a = f"[v{i}]", f"[a{i}]"
    total = sum(lens) - XFADE * (len(ORDER) - 1)
    mix = OUT / "mix.mkv"
    run([ffmpeg(), "-y", *inputs, "-filter_complex", ";".join(fv + fa), "-map", v, "-map", a,
         "-c:v", "libx264", "-crf", "16", "-c:a", "pcm_s16le", mix])
    # two-pass loudness normalisation to -16 LUFS
    m = subprocess.run([ffmpeg(), "-i", str(mix), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    ln = (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    out = BUILD / f"{CUT['name']}.mp4"
    run([ffmpeg(), "-y", "-i", mix, "-af", f"{ln},aresample=48000", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", "-r", FPS, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    srt(cues, lens)
    burn()
    print(f"[assemble] {out} {probe_seconds(out):.2f} s (expected {total:.2f} s)")


def burn():
    """Subtitles burned in: Inter on a translucent box at the bottom (ASS sizes are on a 288-line canvas)."""
    n = CUT["name"]
    run([ffmpeg(), "-y", "-i", f"{n}.mp4", "-vf",
         f"subtitles={n}.srt:fontsdir=fonts:force_style='FontName=Inter,FontSize=11,PrimaryColour=&H00F0E8E2,"
         "BackColour=&H3820120B,OutlineColour=&H3820120B,BorderStyle=4,Outline=2,Shadow=0,MarginV=6'",
         "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-c:a", "copy", "-movflags", "+faststart",
         f"{n}_subtitled.mp4"], cwd=BUILD)


def wrap(s, n=56):
    """At most two lines of at most about n characters."""
    if len(s) <= n:
        return s
    words, l1 = s.split(), ""
    while words and len(l1 + " " + words[0]) <= max(n, len(s) / 2 + 6):
        l1 = (l1 + " " + words.pop(0)).strip()
    return l1 + "\n" + " ".join(words)


def srt(cues, lens):
    def ts(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    rows, start = [], 0.0
    for i, s in enumerate(ORDER):
        for a, b, text in cues[s]:
            # long sentences split at a comma or colon near the middle, timed by length
            parts = [text]
            if len(text) > 96:
                cut = min((m.end() for m in re.finditer(r"[,:;] ", text)), key=lambda k: abs(k - len(text) / 2), default=None)
                if cut:
                    parts = [text[:cut].strip(), text[cut:].strip()]
            t = a
            for p_ in parts:
                d = (b - a) * len(p_) / sum(map(len, parts))
                rows.append((start + t, start + t + d, wrap(p_)))
                t += d
        start += lens[i] - XFADE
    (BUILD / f"{CUT['name']}.srt").write_text(
        "\n".join(f"{k}\n{ts(a)} --> {ts(b)}\n{t}\n" for k, (a, b, t) in enumerate(rows, 1)), encoding="utf8")


def media():
    """Repository copies of the explainer cut in docs/media/: the subtitled video (720p, at most 10 MB), a silent
    loop of the centrepiece (R against M, then the verdict; 960 px, at most 4 MB) and a poster frame."""
    dst = REPO / "docs" / "media"
    dst.mkdir(parents=True, exist_ok=True)
    n = CUT["name"]
    for crf in range(18, 40, 2):  # the lowest CRF (best quality) that fits
        out = dst / f"{n}.mp4"
        run([ffmpeg(), "-y", "-i", BUILD / f"{n}_subtitled.mp4", "-vf", "scale=1280:720:flags=lanczos", "-c:v", "libx264",
             "-preset", "slow", "-crf", crf, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", out])
        if out.stat().st_size <= 10e6:
            break
    durs = json.loads((OUT / "durations.json").read_text())
    idea = sum(durs["S01Hook"]) - XFADE                    # where the idea scene starts in the cut
    b = durs["S03Idea"]
    a0, a1 = idea + b[0], idea + sum(b)                     # from the M and R bars to the verdict
    speed = (a1 - a0) / 10.0                                # about 10 s of loop
    src = BUILD / f"{n}.mp4"                                # without subtitles
    vf = f"setpts=PTS/{speed:.3f},fps=12,scale=960:-1:flags=lanczos"
    run([ffmpeg(), "-y", "-ss", f"{a0:.2f}", "-to", f"{a1:.2f}", "-i", src, "-filter_complex",
         f"[0:v]{vf},split[x][y];[x]palettegen=max_colors=96:stats_mode=diff[p];[y][p]paletteuse=dither=none", "-loop", "0",
         dst / f"{n}_preview.gif"])
    run([ffmpeg(), "-y", "-ss", f"{a0:.2f}", "-to", f"{a1:.2f}", "-i", src, "-vf", vf, "-c:v", "libwebp", "-lossless", "0",
         "-q:v", "70", "-loop", "0", "-an", dst / f"{n}_preview.webp"])
    gif, webp = dst / f"{n}_preview.gif", dst / f"{n}_preview.webp"
    (webp if webp.stat().st_size < gif.stat().st_size else gif).unlink()  # keep the smaller one
    run([ffmpeg(), "-y", "-ss", f"{a1 - 1.0:.2f}", "-i", src, "-frames:v", "1", dst / f"{n}_poster.png"])
    for f in sorted(dst.glob(f"{n}*")):
        print(f"[media] {f.name} {f.stat().st_size / 1e6:.2f} MB")


STEPS = {"fonts": fonts, "voice": voice, "cards": cards, "scenes": scenes, "console": console, "assemble": assemble,
         "preview": lambda: scenes("l"), "subtitles": burn, "media": media}  # preview: low-resolution scenes only, not part of the default run

if __name__ == "__main__":
    BUILD.mkdir(exist_ok=True)
    args = sys.argv[1:]
    if "--cut" in args:
        i = args.index("--cut")
        use_cut(args[i + 1])
        del args[i:i + 2]
    default = [s for s in STEPS if s not in ("preview", "subtitles", "media")]
    if CUT is not CUTS["summary"]:
        default.remove("cards")  # the work-process cards appear in the summary cut only
    if "S04Console" not in CUT["narration"]:
        default.remove("console")  # a cut without console footage
    if CUT.get("media"):
        default.append("media")  # repository copies in docs/media/
    for name in args or default:
        print(f"== {name}")
        STEPS[name]()
