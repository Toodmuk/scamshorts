"""Daily scam-awareness Short.

  python run.py                                  # full run: research -> voice -> video
  python run.py --script samples/sample_script.json   # skip research, use a script file
  python run.py --no-voice                       # silent preview, no ElevenLabs credits
"""
import argparse
import datetime
import json
import os
import shutil
import sys
from zoneinfo import ZoneInfo

import settings
from shorts import deliver, render, script, voice

HISTORY = os.path.join("data", "history.json")
WHERE = "GitHub repo -> Settings -> Secrets and variables -> Actions -> New repository secret"


def require_keys(names):
    """Stop early with a clear message if a secret is missing."""
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        sys.exit("\nMISSING SECRET(S): " + ", ".join(missing) +
                 f"\nAdd them at: {WHERE}\n(Names must match exactly. Keys never go in the code.)\n")
    for n in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        if not os.getenv(n):
            print(f"Note: {n} not set - the video won't be sent to Telegram.")


def load_history():
    if os.path.exists(HISTORY):
        with open(HISTORY, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(items):
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    with open(HISTORY, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)


def post_text(d):
    src = "\n".join(f"- {s.get('title', '')}: {s.get('url', '')}" for s in d["sources"]) \
        or "- (ไม่มี - ห้ามโพสต์จนกว่าจะตรวจข้อมูลแล้ว)"
    return (f"TITLE\n{d['title']}\n\n"
            f"DESCRIPTION\n{d['description']}\n\n{' '.join(d['hashtags'])}\n\n"
            f"SOURCES (fact-check before posting)\n{src}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", help="use this script JSON instead of researching")
    ap.add_argument("--no-voice", action="store_true", help="silent preview")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()

    today = datetime.datetime.now(ZoneInfo("Asia/Bangkok")).date().isoformat()
    outdir = os.path.join(a.out, today)
    os.makedirs(outdir, exist_ok=True)
    history = load_history()
    needed = [] if a.script else ["ANTHROPIC_API_KEY"]
    if not a.no_voice:
        needed.append("ELEVENLABS_API_KEY")
    require_keys(needed)

    if a.script:
        with open(a.script, encoding="utf-8") as f:
            data = script.validate(json.load(f))
        print(f"Using script file {a.script}")
    else:
        target = None
        if not a.no_voice:   # pace the voice credits so they last until the plan renews
            per_video, left, videos, src = voice.budget()
            print(f"Voice budget: {left:,} credits left ({src}), {videos} videos to go -> {per_video:,} per video")
            if per_video < 450:
                deliver.notify(f"⏸ เว้นวันนี้: เครดิตเสียง ElevenLabs เหลือ {left:,} สำหรับอีก {videos} คลิป\n"
                               "ระบบเว้นบางวันเพื่อให้พอใช้ถึงรอบต่ออายุแพ็กเกจ")
                return
            target = min(1000, per_video)
        print("Researching today's scam...")
        data = script.generate([h["topic"] for h in history[-60:]], today, target)
    data["date"] = today
    with open(os.path.join(outdir, "script.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"Topic: {data['topic']} | Hook: {data['hook']}")

    use_voice = not a.no_voice
    lines = [s["narration"] for s in data["scenes"]] + [data["end_narration"]]
    audios, durs = voice.make_all(lines, outdir, use_voice)

    video = render.build(data, audios, durs, outdir)
    text = post_text(data)
    with open(os.path.join(outdir, "post.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    shutil.rmtree(os.path.join(outdir, "tmp"), ignore_errors=True)
    print(f"Done: {video} ({sum(durs):.1f}s)")

    if not a.script:
        history.append({"date": today, "topic": data["topic"], "title": data["title"]})
        save_history(history)
    try:
        deliver.telegram(video, text, settings.POST_MODE, settings.POST_TIME)
    except Exception as e:  # video is still saved in GitHub; don't fail the run
        print(f"WARNING: could not send to Telegram: {e}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        deliver.notify(f"❌ วันนี้สร้างคลิปไม่สำเร็จ: {str(e)[:300]}\nดูรายละเอียดใน GitHub > Actions")
        raise
