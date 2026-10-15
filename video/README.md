# Videos

Three cuts, each rebuilt from source by one command: 1920×1080, 30 fps, H.264 + AAC, −16 LUFS, with
subtitles. Everything shown is SIMULATED; [STORYBOARD.md](STORYBOARD.md) traces every number.

| Cut | Length | Command (from the repository root) |
|---|---|---|
| explainer: hook, the idea, one results card, close; no console | 88 s | `video/.venv/Scripts/python video/build.py --cut explainer` |
| short: the pitching demo, with the console | 2:54 | `video/.venv/Scripts/python video/build.py --cut short` |
| summary: the full demo | 4:51 | `video/.venv/Scripts/python video/build.py` |

[cuts.py](cuts.py) defines the cuts. Each writes `<name>.mp4`, `<name>_subtitled.mp4` and `<name>.srt`
to `video/build/` (not tracked). The explainer also writes [docs/media/](../docs/media/): the subtitled
video at 720p, a silent preview loop and a poster frame.

## Steps

Steps run in order, or alone: `build.py --cut short scenes assemble`.

1. fonts: downloads Inter and JetBrains Mono (SIL OFL 1.1) into `build/fonts/`.
2. voice: reads the narration and writes one WAV per scene, the beat lengths and the subtitle timings.
3. cards (summary only): runs `pytest`, `shahid.check_numbers` and `shahid.check_tables` and reads the
   protocol commits for the closing scene. A failing check stops the build.
4. scenes: renders [scenes/](scenes/), each beat as long as its narration. An animation that outruns its
   narration stops the build.
5. console (short and summary): records the `showcase` replay at 1920×1080, page only, with SIMULATED
   and CONSTRUCTED DEMONSTRATION DAY chips. It stops if the approval is not flagged as fast, since the
   caption says it is.
6. assemble: crossfades the scenes, normalises loudness in two passes, and writes and burns in the
   subtitles.
7. media (explainer only): writes the files in `docs/media/`.

Extra steps: `preview` renders the scenes at low resolution; `subtitles` re-burns the subtitles.

## Environments

- Project environment `.venv` (console and checks): `py -3.11 -m venv .venv`, then
  `pip install -r requirements.lock -r requirements-dev.txt streamlit==1.65.0`.
- Video environment `video/.venv`, apart from `requirements.lock`:
  `py -3.11 -m venv video/.venv`, then `video/.venv/Scripts/pip install manim kokoro soundfile playwright pillow`
  and `video/.venv/Scripts/python -m playwright install chromium`.
- ffmpeg on PATH: `winget install Gyan.FFmpeg`.

Versions of the committed builds:

| Package | Version |
|---|---|
| Python | 3.11.7 |
| Manim Community Edition | 0.22.0 (ManimPango 0.7.0, PyAV 18.1.0) |
| Kokoro text-to-speech | 0.9.4, model Kokoro-82M (misaki 0.9.4, spaCy 3.8.16 with en_core_web_sm 3.8.0, espeakng-loader 0.2.4) |
| PyTorch | 2.14.1 |
| Playwright | 1.64.0, Chromium |
| Pillow, soundfile, SciPy, NumPy | 12.3.0, 0.14.0, 1.17.1, 2.4.6 |
| ffmpeg | 9.0.2 (gyan.dev full build) |
| Streamlit (console) | 1.65.0 |

The build needs no TeX: every symbol is Unicode text.

## Files

| File | Role |
|---|---|
| [STORYBOARD.md](STORYBOARD.md) | scenes, visuals, narration, the source of every number, style sheet |
| [narration.py](narration.py) | the summary narration per beat |
| [cuts.py](cuts.py) | the cuts: narration of the short and explainer cuts, scenes, console steps, voice speed |
| [tts.py](tts.py) | the text-to-speech wrapper and pronunciation fixes |
| [scenes/](scenes/) | one scene per storyboard scene; `short.py` holds the condensed scenes, `style.py` the palette, timing and shared drawings |
| [build.py](build.py) | the build |
| [CREDITS.md](CREDITS.md) | tools, fonts, voice and data with their licences |
