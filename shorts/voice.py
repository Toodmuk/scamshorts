"""Turns each narration line into an mp3 with ElevenLabs.
Without an API key it returns silent timings, so you can preview visuals."""
import base64
import datetime
import json
import os
import subprocess
from zoneinfo import ZoneInfo

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


USAGE = os.path.join("data", "voice_usage.json")
BKK = ZoneInfo("Asia/Bangkok")


def _record(chars):
    """Our own monthly count (backup for when the key can't read the plan)."""
    month = datetime.datetime.now(BKK).strftime("%Y-%m")
    try:
        with open(USAGE, encoding="utf-8") as f:
            u = json.load(f)
    except (OSError, ValueError):
        u = {}
    u[month] = u.get(month, 0) + chars
    os.makedirs("data", exist_ok=True)
    with open(USAGE, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(u.items())[-12:]), f, indent=1)


def budget():
    """How many voice characters today's video may use so the credits last until they renew.
    Returns (per_video, credits_left, videos_left, source)."""
    import schedule
    today = datetime.datetime.now(BKK).date()
    left, reset, source = None, None, "estimate"
    try:
        r = requests.get("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": API_KEY}, timeout=30)
        if r.status_code == 200:
            j = r.json()
            left = int(j["character_limit"]) - int(j["character_count"])
            if j.get("next_character_count_reset_unix"):
                reset = datetime.datetime.fromtimestamp(int(j["next_character_count_reset_unix"]), BKK).date()
            source = "elevenlabs"
    except (requests.RequestException, ValueError, KeyError):
        pass
    if left is None:        # key can't read the plan: use our own count for this calendar month
        try:
            with open(USAGE, encoding="utf-8") as f:
                used = json.load(f).get(today.strftime("%Y-%m"), 0)
        except (OSError, ValueError):
            used = 0
        left = int(getattr(settings, "VOICE_MONTHLY_CREDITS", 30000)) - used
    if reset is None:       # assume it renews on the 1st of next month
        reset = (today.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
    videos = max(1, schedule.count_post_days(today, reset))
    spare = left - int(getattr(settings, "VOICE_RESERVE", 2000))
    return max(0, spare // videos), left, videos, source


def _speed_up(audios, durs, tmp, factor):
    """Speed every line up by `factor` (<= 1.25) so the video fits the length cap."""
    for i, p in enumerate(audios):
        if not p:
            continue
        out = p.replace(".mp3", "_fast.mp3")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", p, "-filter:a", f"atempo={factor:.4f}", out], check=True)
        os.replace(out, p)
        durs[i] = _length(p) + PAUSE
        ap = os.path.join(tmp, f"align_{i:02d}.json")
        try:
            with open(ap, encoding="utf-8") as f:
                al = json.load(f)
            for k in ("character_start_times_seconds", "character_end_times_seconds"):
                if al.get(k):
                    al[k] = [t / factor for t in al[k]]
            with open(ap, "w", encoding="utf-8") as f:
                json.dump(al, f, ensure_ascii=False)
        except (OSError, ValueError):
            pass
    return durs


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
    if use_voice and enabled():
        _record(sum(len(clean(x)) for x in lines))
        cap = float(getattr(settings, "MAX_SECONDS", 88)) - 1.5
        if sum(durs) > cap:      # keep under Facebook's 90-second Reels limit
            factor = min(1.25, sum(durs) / cap)
            print(f"Narration {sum(durs):.1f}s is over the cap - speeding up x{factor:.2f}")
            durs = _speed_up(audios, durs, tmp, factor)
    durs[-1] += 0.8  # hold the end card a moment longer
    return audios, durs
