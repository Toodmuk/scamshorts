"""Posts today's Short on schedule (or right away on workflow_dispatch).

Runs every hour (07:23-22:23 Bangkok). Each run:
  - already posted / skipped today -> does nothing (silent)
  - POST_MODE auto                 -> posts at AUTO_POST_HOUR (or immediately
                                     when POST_ANY_DAY is set from Run workflow)
  - reply "skip" in Telegram       -> skip that day only (emergency brake)
  - POST_MODE approve              -> posts only after Telegram "ok"

  python post.py artifact            # folder containing short.mp4 + script.json
  python post.py artifact --dry-run  # show what would be posted, post nothing
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
LAST_HOUR = 21          # the 21:xx run is the last check of the day


def load_posted():
    if os.path.exists(POSTED):
        with open(POSTED, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_posted(posted):
    os.makedirs(os.path.dirname(POSTED), exist_ok=True)
    with open(POSTED, "w", encoding="utf-8") as f:
        json.dump(posted, f, ensure_ascii=False, indent=1)


def safety_notes(d):
    """Non-blocking notes logged on auto post (never holds the day)."""
    out = []
    if not [s for s in d.get("sources") or [] if str((s or {}).get("url", "")).startswith("http")]:
        out.append("ไม่มีแหล่งข้อมูลอ้างอิง")
    if d.get("editor_ok") is False:
        out.append("ขั้นตรวจข้อเท็จจริงไม่ได้ทำงาน")
    if d.get("renderer") == "classic" and (getattr(settings, "RENDERER", "") or "").lower() == "constructivist":
        out.append("ใช้ระบบตัดต่อสำรอง")
    return out


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

    import schedule
    if not schedule.is_post_day(now.date()) and not os.getenv("POST_ANY_DAY"):
        print("Not a posting day.")
        return 0
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
    notes = safety_notes(data)
    # Manual "Run workflow" sets POST_ANY_DAY — post now, don't wait for AUTO_POST_HOUR.
    hour_ok = bool(os.getenv("POST_ANY_DAY")) or now.hour >= int(getattr(settings, "AUTO_POST_HOUR", 18))
    auto_ready = mode == "auto" and decision != "skip" and hour_ok
    go = decision == "ok" or auto_ready
    print(f"mode={mode} decision={decision} notes={notes} -> {'POST' if go else 'WAIT'}")

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
        if last_run and mode == "approve":
            deliver.notify("วันนี้ไม่ได้โพสต์ - ไม่ได้รับคำตอบ ok")
            posted[today] = {"status": "no reply", "title": data["title"]}
            save_posted(posted)
        return 0                                    # otherwise wait for the next hourly run
    if notes:
        print("Auto-post notes (non-blocking): " + "; ".join(notes))
    if not publish.enabled():
        deliver.notify("ยังไม่ได้ตั้งค่า UPLOAD_POST_API_KEY / UPLOAD_POST_USER - โพสต์ไม่ได้")
        return 1

    try:
        results = publish.post(video, data)
    except Exception as e:  # not posted - the next hourly run will try again
        deliver.notify(f"โพสต์ไม่สำเร็จ จะลองใหม่รอบถัดไป: {e}")
        return 1

    u = publish.LAST_USAGE or {}
    usage = f"\nUpload-Post เดือนนี้ใช้ไป {u['count']}/{u['limit']} ครั้ง" if u.get("limit") else ""
    deliver.notify("โพสต์แล้ว\n" + "\n".join(f"{p}: {r}" for p, r in results.items()) + usage)
    posted[today] = {"status": "posted", "title": data["title"], "hook": data.get("hook", ""),
                     "topic": data.get("topic", ""), "request_id": publish.LAST_REQUEST_ID, "results": results}
    posted.pop(f"held:{today}", None)
    save_posted(posted)
    return 1 if any(str(r).startswith("ERROR") for r in results.values()) else 0   # SKIPPED is not an error


if __name__ == "__main__":
    sys.exit(main())
