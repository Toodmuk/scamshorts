"""Which days get a video. One place to change it: POST_DAYS in settings.py.

  python schedule.py      exit 0 if today (Bangkok) is a posting day, else 1  (used by the workflows)
"""
import datetime
import sys
from zoneinfo import ZoneInfo

import settings

BKK = ZoneInfo("Asia/Bangkok")
NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def post_days():
    raw = (getattr(settings, "POST_DAYS", "") or "mon,tue,wed,thu,fri,sat,sun").lower()
    days = {NAMES.index(d.strip()[:3]) for d in raw.split(",") if d.strip()[:3] in NAMES}
    return days or set(range(7))


def is_post_day(day=None):
    day = day or datetime.datetime.now(BKK).date()
    return day.weekday() in post_days()


def count_post_days(start, end):
    """Posting days from start (inclusive) to end (exclusive)."""
    n, d = 0, start
    while d < end:
        n += is_post_day(d)
        d += datetime.timedelta(days=1)
    return n


if __name__ == "__main__":
    sys.exit(0 if is_post_day() else 1)
