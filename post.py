"""Posts today's Short once you approve it in Telegram.

Runs every hour (07:23-22:23 Bangkok). Each run:
  - already posted / skipped today -> does nothing (silent)
  - you replied "ok"              -> posts now, sends you the links
  - you replied "skip"            -> tells you once, then stays silent
  - no reply yet                  -> silent; the last run of the day (22:xx)
                                     tells you it wasn't posted

  python post.py artifact            # folder containing short.mp4 + script.json
  python post.py artifact --dry-run  # show what would be posted, post nothing

POST_MODE "approve" (default): posts only after "ok".
POST_MODE "auto": posts on the first run unless you replied "skip".
"""
import argparse
import datetime
import glob
import json
import os
import sys
from zoneinfo import ZoneInfo

import settings
from shorts import deliver, publish

POSTED = os.path.join("data", "posted.json")
BKK = ZoneInfo("Asia/Bangkok")
LAST_HOUR = 22          # the 22:xx run is the last chance of the day


def load_posted():
    if os.path.exists(POSTED):
        with open(POSTED, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_posted(posted):
    os.makedirs(os.path.dirname(POSTED), exist_ok=True)
    with open(POSTED, "w", encoding="utf-8") as f:
        json.dump(posted, f, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="?", default="artifact")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    now = datetime.datetime.now(BKK)
    if os.getenv("POST_NOW"):                      # for testing only
        now = datetime.datetime.fromisoformat(os.environ["POST_NOW"]).replace(tzinfo=BKK)
    today = now.date().isoformat()
    midnight = int(datetime.datetime.combine(now.date(), datetime.time(), BKK).timestamp())
    last_run = now.hour >= LAST_HOUR
    mode = getattr(settings, "POST_MODE", "approve")

    posted = load_posted()
    if today in posted:
        print(f"Already handled today: {list(posted[today])}")
        return 0

    # find today's video (the morning run can be hours late - that's fine)
    video, data = None, None
    for v in glob.glob(os.path.join(a.folder, "**", "short.mp4"), recursive=True):
        try:
            with open(os.path.join(os.path.dirname(v), "script.json"), encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if d.get("date") == today:
            video, data = v, d
            break
    if not video:
        print("No video for today yet.")
        if last_run:
            deliver.notify("วันนี้ไม่มีคลิปให้โพสต์ - การสร้างคลิปตอนเช้าอาจล้มเหลว เช็ก GitHub > Actions > Daily Short")
            posted[today] = {"status": "no video"}
            save_posted(posted)
        return 0

    decision = deliver.approval(midnight)
    go = decision == "ok" or (mode == "auto" and decision != "skip")
    print(f"mode={mode} decision={decision} -> {'POST' if go else 'WAIT'}")

    if a.dry_run:
        for k, v in publish.build_form(data):
            print(f"  {k}: {v[:80]!r}")
        return 0

    if decision == "skip":
        deliver.notify("วันนี้ไม่โพสต์ (คุณตอบ skip)")
        posted[today] = {"status": "skipped", "title": data["title"]}
        save_posted(posted)
        return 0
    if not go:
        if last_run:
            deliver.notify("วันนี้ไม่ได้โพสต์ - ไม่ได้รับคำตอบ ok")
            posted[today] = {"status": "no reply", "title": data["title"]}
            save_posted(posted)
        return 0                                    # otherwise wait for the next hourly run
    if not publish.enabled():
        deliver.notify("ยังไม่ได้ตั้งค่า UPLOAD_POST_API_KEY / UPLOAD_POST_USER - โพสต์ไม่ได้")
        return 1

    try:
        results = publish.post(video, data)
    except Exception as e:  # not posted - the next hourly run will try again
        deliver.notify(f"โพสต์ไม่สำเร็จ จะลองใหม่รอบถัดไป: {e}")
        return 1

    deliver.notify("โพสต์แล้ว\n" + "\n".join(f"{p}: {r}" for p, r in results.items()))
    posted[today] = {"status": "posted", "title": data["title"], "results": results}
    save_posted(posted)
    return 1 if any(str(r).startswith("ERROR") for r in results.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
