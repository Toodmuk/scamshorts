"""Turns each narration line into an mp3 with ElevenLabs.
Without an API key it returns silent timings, so you can preview visuals."""
import os
import subprocess

import requests

import settings
from .text import clean

API_KEY = os.getenv("ELEVENLABS_API_KEY")   # secret - set in GitHub, not here
VOICE_ID = settings.ELEVENLABS_VOICE_ID
MODEL = settings.ELEVENLABS_MODEL
PAUSE = 0.35  # breathing room after each line (seconds)


def enabled():
    return bool(API_KEY and VOICE_ID)


def _synth(text, path):
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": API_KEY, "Content-Type": "application/json"},
        json={"text": text, "model_id": MODEL},
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text[:300]}")
    with open(path, "wb") as f:
        f.write(r.content)


def _length(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _estimate(text):
    # Thai narration runs roughly 11-13 characters per second.
    return max(2.0, len(text) / 12 + 0.6)


def make_all(lines, outdir, use_voice=True):
    """Returns (audio_paths, durations). Audio paths are None when silent."""
    tmp = os.path.join(outdir, "tmp")
    os.makedirs(tmp, exist_ok=True)
    audios, durs = [], []
    for i, line in enumerate(lines):
        text = clean(line)
        if use_voice and enabled():
            path = os.path.join(tmp, f"a{i:02d}.mp3")
            _synth(text, path)
            audios.append(path)
            durs.append(_length(path) + PAUSE)
        else:
            audios.append(None)
            durs.append(_estimate(text))
    durs[-1] += 0.8  # hold the end card a moment longer
    return audios, durs
