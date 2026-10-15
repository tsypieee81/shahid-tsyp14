# Credits and licences

No music, no stock footage, no images from outside this repository. Every visual is drawn by the build
(Manim scenes, Pillow overlays) or recorded from this repository's own console.

## Tools

| Tool | Use | Licence |
|---|---|---|
| Manim Community Edition | animation | MIT |
| ManimPango, Pango, Cairo | text and vector rendering | GPL-3.0 (ManimPango), LGPL-2.1 (Pango, Cairo); used as tools, not shipped |
| PyAV | Manim's video writer | BSD-3-Clause |
| Kokoro (library) | text-to-speech | Apache-2.0 |
| misaki | Kokoro's grapheme-to-phoneme front end | Apache-2.0 |
| espeak-ng (via espeakng-loader) | phonemes for words misaki does not know | GPL-3.0; used as a tool, not shipped |
| spaCy, en_core_web_sm | misaki's English tokenizer and model | MIT |
| PyTorch | runs the voice model | BSD-3-Clause |
| Playwright, Chromium | console capture | Apache-2.0, BSD-3-Clause |
| Pillow | overlay chips | MIT-CMU (HPND) |
| SciPy, NumPy | Student-t curves in the scenes | BSD-3-Clause |
| ffmpeg | encoding, crossfades, loudness, subtitles | GPL-3.0 build (gyan.dev); used as a tool |
| Streamlit | the console being recorded | Apache-2.0 |

## Voice

Kokoro-82M model weights and the `af_heart` voice (hexgrad/Kokoro-82M on Hugging Face): Apache-2.0.
The narrator is synthetic; the video does not name the voice.

## Fonts

| Font | Use | Licence |
|---|---|---|
| Inter 4.1 (Rasmus Andersson) | all text and subtitles | SIL Open Font License 1.1 |
| JetBrains Mono 2.304 | terminal cards | SIL Open Font License 1.1 |

The console capture also shows the fonts the console itself loads (Streamlit's defaults and Material
Symbols, Apache-2.0).

## Data

Every number comes from this repository's ledger, stamped result files or the paper's press references;
see STORYBOARD.md. The simulated results derive from the SimBench database (ODbL 1.0), as stated in
`dataset/LICENSE.md`.
