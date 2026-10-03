"""Posts today's Short if you approved it in Telegram.

  python post.py artifact            # folder containing short.mp4 + script.json
  python post.py artifact --dry-run  # show what would be posted, post nothing

POST_MODE=approve (default): posts only if you replied "ok".
POST_MODE=auto: posts unless you replied "skip".
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


def load_posted():
    if os.path.exists(POSTED):
        with open(POSTED, encoding="utf-8") as f:
            return json.load(f)
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="?", default="artifact")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    now = datetime.datetime.now(BKK)
    today = now.date().isoformat()
    midnight = int(datetime.datetime.combine(now.date(), datetime.time(), BKK).timestamp())
    mode = settings.POST_MODE

    vids = glob.glob(os.path.join(a.folder, "**", "short.mp4"), recursive=True)
    if not vids:
        deliver.notify("ไม่พบคลิปของวันนี้ - การสร้างคลิปตอนเช้าอาจล้มเหลว เช็ก GitHub Actions")
        return 0
    video = vids[0]
    with open(os.path.join(os.path.dirname(video), "script.json"), encoding="utf-8") as f:
        data = json.load(f)
    if data.get("date") != today:
        deliver.notify(f"คลิปล่าสุดเป็นของวันที่ {data.get('date')} ไม่ใช่วันนี้ - ไม่โพสต์")
        return 0

    posted = load_posted()
    if today in posted:
        print("Already posted today.")
        return 0

    decision = deliver.approval(midnight)
    go = decision == "ok" or (mode == "auto" and decision != "skip")
    print(f"mode={mode} decision={decision} -> {'POST' if go else 'HOLD'}")

    if a.dry_run:
        for k, v in publish.build_form(data):
            print(f"  {k}: {v[:80]!r}")
        return 0
    if not go:
        why = "คุณตอบ skip" if decision == "skip" else "ไม่ได้รับคำตอบ ok"
        deliver.notify(f"วันนี้ไม่โพสต์ ({why})")
        return 0
    if not publish.enabled():
        deliver.notify("ยังไม่ได้ตั้งค่า UPLOAD_POST_API_KEY / UPLOAD_POST_USER - โพสต์ไม่ได้")
        return 1

    try:
        results = publish.post(video, data)
    except Exception as e:  # report and fail the run so GitHub emails you
        deliver.notify(f"โพสต์ไม่สำเร็จ: {e}")
        return 1

    lines = [f"{p}: {r}" for p, r in results.items()]
    deliver.notify("โพสต์แล้ว\n" + "\n".join(lines))
    posted[today] = {"title": data["title"], "results": results}
    os.makedirs(os.path.dirname(POSTED), exist_ok=True)
    with open(POSTED, "w", encoding="utf-8") as f:
        json.dump(posted, f, ensure_ascii=False, indent=1)
    return 1 if any(str(r).startswith("ERROR") for r in results.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
