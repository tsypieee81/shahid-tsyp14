"""Narration with Kokoro-82M (Apache 2.0). Pronunciation fixes use Kokoro's inline phoneme syntax.
Run alone to write the two voice samples: python video/tts.py
"""
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 24000
VOICE = "af_heart"
FIX = {"SHAHID": "[SHAHID](/ʃəhˈid/)", "STEG": "[STEG](/stˈɛɡ/)"}
_pipes = {}


def speak(text, voice=VOICE, say=None, speed=1.0):
    """Audio (float32, 24 kHz) of `text`; `say` maps on-screen spellings to how the voice reads them."""
    lang = voice[0]  # "a" American, "b" British English
    if lang not in _pipes:
        from kokoro import KPipeline
        _pipes[lang] = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M")
    for k, v in {**(say or {}), **FIX}.items():
        text = text.replace(k, v)
    return np.concatenate([np.asarray(a, dtype=np.float32) for _, _, a in _pipes[lang](text, voice=voice, speed=speed)])


if __name__ == "__main__":
    sample = ("Here is the idea. All the energy these customers use passes through one transformer, "
              "and a meter on its low-voltage side keeps counting. That meter is our witness. "
              "SHAHID asks it one question.")
    out = Path(__file__).parent / "build" / "voices"
    out.mkdir(parents=True, exist_ok=True)
    for v in ("af_heart", "bm_george"):
        a = speak(sample, v)
        sf.write(out / f"{v}.wav", a, SR)
        print(v, round(len(a) / SR, 1), "s")
