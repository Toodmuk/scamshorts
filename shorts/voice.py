"""Turns each narration line into an mp3 with ElevenLabs.
Without an API key it returns silent timings, so you can preview visuals."""
import base64
import json
import os
import subprocess

import requests

import settings
from .text import clean

API_KEY = os.getenv("ELEVENLABS_API_KEY")   # secret - set in GitHub, not here
VOICE_ID = settings.ELEVENLABS_VOICE_ID
MODEL = settings.ELEVENLABS_MODEL
_TIMESTAMPS_OK = True
PAUSE = 0.15  # breathing room after each line (seconds) - short keeps the pace up


def enabled():
    return bool(API_KEY and VOICE_ID)


def _synth(text, path):
    """Speak one line. Asks for word timings too (for synced highlights);
    falls back to plain audio if that endpoint isn't available."""
    headers = {"xi-api-key": API_KEY, "Content-Type": "application/json"}
    body = {"text": text, "model_id": MODEL}
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    global _TIMESTAMPS_OK
    try:
        if not _TIMESTAMPS_OK:
            raise ValueError("timestamps unavailable")
        r = requests.post(url + "/with-timestamps", params={"output_format": "mp3_44100_128"},
                          headers=headers, json=body, timeout=120)
        if r.status_code == 200:
            j = r.json()
            audio = base64.b64decode(j["audio_base64"])
            if audio:
                with open(path, "wb") as f:
                    f.write(audio)
                return j.get("alignment") or j.get("normalized_alignment")
        _TIMESTAMPS_OK = False      # don't keep asking for every line
    except (requests.RequestException, ValueError, KeyError):
        pass
    r = requests.post(url, params={"output_format": "mp3_44100_128"},
                      headers=headers, json=body, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text[:300]}")
    with open(path, "wb") as f:
        f.write(r.content)
    return None


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
            align = _synth(text, path)
            if align:
                with open(os.path.join(tmp, f"align_{i:02d}.json"), "w", encoding="utf-8") as f:
                    json.dump(align, f, ensure_ascii=False)
            audios.append(path)
            durs.append(_length(path) + PAUSE)
        else:
            audios.append(None)
            durs.append(_estimate(text))
    durs[-1] += 0.8  # hold the end card a moment longer
    return audios, durs
