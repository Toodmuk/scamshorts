"""Constructivist renderer bridge.

Prepares a job for web/render.js (script, scene timings, word timings, Thai word breaks),
runs it in Node, then mixes the narration with the sound effects and muxes short.mp4.
Any failure raises, so render.build can fall back to the classic renderer.
"""
import glob
import json
import os
import random
import re
import shutil
import subprocess

from pythainlp.tokenize import word_tokenize

import settings
from . import render as R
from .text import _TRIE, clean

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
THAI = re.compile(r"[\u0E00-\u0E7F]")


def available():
    return bool(shutil.which("node")) and os.path.isdir(os.path.join(WEB, "node_modules", "canvas"))


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def _segs(script):
    """Thai has no spaces between words: send word breaks for every phrase."""
    out = {}
    for s in _strings(script):
        for ph in s.split():
            if THAI.search(ph) and len(ph) > 6 and ph not in out:
                out[ph] = word_tokenize(ph, custom_dict=_TRIE, engine="newmm", keep_whitespace=True)
    return out


def _aligns(tmp, n):
    res = []
    for i in range(n):
        try:
            with open(os.path.join(tmp, f"align_{i:02d}.json"), encoding="utf-8") as f:
                res.append(json.load(f))
        except (OSError, ValueError):
            res.append(None)
    return res


def build(data, audios, durations, outdir):
    tmp = os.path.join(outdir, "tmp")
    os.makedirs(tmp, exist_ok=True)
    durs = [max(1, round(d * 30)) / 30 for d in durations]
    aligns = _aligns(tmp, len(durs))

    lines = [clean(s["narration"]) for s in data["scenes"]] + [clean(data["end_narration"])]
    highs = [s.get("highlight", []) for s in data["scenes"]] + [["1441"]]
    words = [[[round(t, 3), w] for t, w in R.word_times(text, hl, al, 0.85 * d)]
             for text, hl, al, d in zip(lines, highs, aligns, durs)]

    script = dict(data)
    script["scenes"] = [dict(s, narration=clean(s["narration"])) for s in data["scenes"]]
    script["end_narration"] = lines[-1]
    job = {
        "script": script, "durs": durs, "words": words, "segs": _segs(script),
        "channel": getattr(settings, "CHANNEL_NAME", ""),
        "out_video": os.path.join(tmp, "video.mp4"), "out_audio": os.path.join(tmp, "sfx.wav"),
        "out_cover": os.path.join(outdir, "cover.png"),
    }
    job_path = os.path.join(tmp, "job.json")
    with open(job_path, "w", encoding="utf-8") as f:
        json.dump(job, f, ensure_ascii=False)

    r = subprocess.run(["node", os.path.join(WEB, "render.js"), job_path],
                       capture_output=True, text=True, timeout=1800)
    print(r.stdout.strip())
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "node renderer failed").strip()[-400:])

    # voice + effects (+ optional music), levelled for phone speakers when there is a voice
    narration = R._narration(audios, durs, tmp)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", narration, "-i", job["out_audio"]]
    chains = ["[1:a]aresample=44100,aformat=channel_layouts=stereo,volume=0.9[s]"]
    mix = "[0:a][s]"
    tracks = glob.glob(os.path.join(R.MUSIC_DIR, "*.mp3"))
    if tracks:
        cmd += ["-stream_loop", "-1", "-i", random.choice(tracks)]
        chains.append("[2:a]aresample=44100,aformat=channel_layouts=stereo,volume=0.08[m]")
        mix += "[m]"
    level = ",loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100" if any(audios) else ""
    chains.append(f"{mix}amix=inputs={mix.count('[')}:duration=first:normalize=0{level}[a]")
    audio = os.path.join(tmp, "audio.wav")
    R._run(cmd + ["-filter_complex", ";".join(chains), "-map", "[a]", "-c:a", "pcm_s16le", audio])

    final = os.path.join(outdir, "short.mp4")
    R._run(["ffmpeg", "-y", "-loglevel", "error", "-i", job["out_video"], "-i", audio,
            "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-shortest", "-movflags", "+faststart", final])
    return final
