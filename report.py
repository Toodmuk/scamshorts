"""Weekly performance report -> Telegram (Mondays ~09:17 Bangkok, or Actions -> Weekly report -> Run).

1. Pulls profile stats (followers, views, likes...) and per-video stats for the last 7 days
   from Upload-Post's analytics API - no extra keys needed.
2. Claude reads the numbers next to each video's hook and topic and writes a short Thai analysis.
3. Sends the report to Telegram.
4. Saves "lessons" to data/insights.txt - the script writer reads them next week (style, hooks,
   topic choice only; the fact rules never change).
"""
import datetime
import json
import os
import sys
from zoneinfo import ZoneInfo

import requests

import settings
from shorts import deliver, publish

BKK = ZoneInfo("Asia/Bangkok")
POSTED = os.path.join("data", "posted.json")
STATS = os.path.join("data", "stats.json")
INSIGHTS = os.path.join("data", "insights.txt")
PLATFORMS = publish.PLATFORMS
NAMES = {"youtube": "YouTube", "facebook": "Facebook", "instagram": "Instagram", "tiktok": "TikTok"}


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _get(path, params=None):
    r = requests.get(f"{publish.API}{path}", params=params or {}, timeout=90,
                     headers={"Authorization": f"Apikey {publish.KEY}"})
    r.raise_for_status()
    return r.json()


def _num(x):
    return x if isinstance(x, (int, float)) else 0


def profile_stats():
    params = {"platforms": ",".join(PLATFORMS)}
    if publish.PAGE_ID:
        params["page_id"] = publish.PAGE_ID
    j = _get(f"/analytics/{publish.PROFILE}", params)
    out = {}
    for p in PLATFORMS:
        d = j.get(p)
        if isinstance(d, dict):
            vals = {k: d[k] for k in ("followers", "views", "reach", "impressions", "likes", "comments",
                                      "shares", "saves", "watch_time_minutes", "average_view_duration_seconds")
                    if isinstance(d.get(k), (int, float))}
            if "followers" in vals:          # skip platforms that answered with a message instead of numbers
                out[p] = vals
    return out


def video_stats(entry):
    """Per-platform numbers for one posted video. Facebook reports reach instead of views."""
    rid = entry.get("request_id")
    if not rid:
        return {}
    j = _get(f"/uploadposts/post-analytics/{rid}")
    out = {}
    for p, d in (j.get("platforms") or {}).items():
        m = (d or {}).get("post_metrics") or {}
        out[p] = {"views": _num(m.get("views")) or _num(m.get("reach")), "likes": _num(m.get("likes")) or _num(m.get("reactions")),
                  "comments": _num(m.get("comments")), "shares": _num(m.get("shares"))}
    return out


def analyze(rows, prof, deltas):
    """Claude's short Thai analysis + English lessons for the script writer."""
    import anthropic
    data = {"videos": rows, "profile": prof, "follower_change": deltas}
    prompt = (
        "You are the growth analyst for a Thai scam-awareness Shorts channel (YouTube, Facebook, Instagram).\n"
        "Here is last week's data as JSON. Views on Facebook are reach.\n"
        f"{json.dumps(data, ensure_ascii=False)}\n\n"
        "Write in Thai, plain text, under 900 characters:\n"
        "1) สรุปสัปดาห์นี้ (2 บรรทัด)\n2) คลิปที่ดีที่สุด และน่าจะเพราะอะไร\n3) คลิปที่อ่อนที่สุด และน่าจะเพราะอะไร\n"
        "4) 3 อย่างที่ควรลองสัปดาห์หน้า (hook, หัวข้อ, รูปแบบ)\n"
        "Base every claim on the numbers; say so if there is too little data to tell.\n"
        "Then on a new line write LESSONS: followed by 3-5 short English bullet points for the script\n"
        "writer about hooks, topic choice and pacing only (never about facts or sources).")
    r = anthropic.Anthropic().messages.create(model=settings.CLAUDE_MODEL, max_tokens=1200,
                                              messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()
    if "LESSONS:" in text:
        thai, lessons = text.split("LESSONS:", 1)
        return thai.strip(), lessons.strip()
    return text, ""


def main():
    now = datetime.datetime.now(BKK)
    start, end = (now - datetime.timedelta(days=7)).date(), (now - datetime.timedelta(days=1)).date()
    posted = _load(POSTED, {})
    week = {d: e for d, e in posted.items() if ":" not in d and start.isoformat() <= d <= end.isoformat()}
    n_posted = sum(1 for e in week.values() if e.get("status") == "posted")
    n_skipped = sum(1 for e in week.values() if e.get("status") == "skipped")
    n_held = sum(1 for d in posted if d.startswith("held:") and start.isoformat() <= d[5:] <= end.isoformat())

    if not (publish.KEY and publish.PROFILE):
        deliver.notify("📊 รายงานประจำสัปดาห์: ยังไม่ได้ตั้งค่า Upload-Post จึงดึงสถิติไม่ได้")
        return 1

    problems = []
    try:
        prof = profile_stats()
    except Exception as e:
        prof, problems = {}, [f"สถิติช่อง: {str(e)[:120]}"]

    rows = []
    for d, e in sorted(week.items()):
        if e.get("status") != "posted":
            continue
        try:
            vs = video_stats(e)
        except Exception as ex:
            vs, problems = {}, problems + [f"สถิติคลิป {d}: {str(ex)[:80]}"]
        rows.append({"date": d, "hook": e.get("hook") or e.get("title", ""), "topic": e.get("topic", ""),
                     "views": sum(v["views"] for v in vs.values()), "likes": sum(v["likes"] for v in vs.values()),
                     "comments": sum(v["comments"] for v in vs.values()), "shares": sum(v["shares"] for v in vs.values()),
                     "per_platform": vs})

    history = _load(STATS, [])
    last = history[-1]["profile"] if history else {}
    deltas = {p: _num(prof.get(p, {}).get("followers")) - _num(last.get(p, {}).get("followers"))
              for p in prof if last.get(p)}
    missing = [NAMES.get(p, p) for p in PLATFORMS if p not in prof]
    if missing and prof:
        hint = " (ใส่ secret FACEBOOK_PAGE_ID เพื่อดูผู้ติดตาม Facebook)" if "facebook" in PLATFORMS and "facebook" not in prof and not publish.PAGE_ID else ""
        problems.append("ไม่มีตัวเลขผู้ติดตามของ " + ", ".join(missing) + hint)

    # ---- the message
    lines = [f"📊 รายงานประจำสัปดาห์ {start.day}/{start.month} – {end.day}/{end.month}"]
    if prof:
        fl = [f"{NAMES.get(p, p)} {_num(v.get('followers')):,}" + (f" ({deltas[p]:+,})" if p in deltas else "")
              for p, v in prof.items()]
        lines.append("👥 ผู้ติดตาม: " + " · ".join(fl))
    lines.append(f"🎬 โพสต์ {n_posted} คลิป" + (f" · ข้าม {n_skipped}" if n_skipped else "") + (f" · พักไว้ {n_held}" if n_held else ""))
    if rows:
        lines.append(f"👀 ยอดเห็นคลิปสัปดาห์นี้รวม {sum(r['views'] for r in rows):,} · ไลก์ {sum(r['likes'] for r in rows):,}"
                     f" · คอมเมนต์ {sum(r['comments'] for r in rows):,} · แชร์ {sum(r['shares'] for r in rows):,}")
        ranked = sorted(rows, key=lambda r: r["views"], reverse=True)
        lines.append("\n🏆 ดีที่สุด")
        for i, r in enumerate(ranked[:3], 1):
            lines.append(f"{i}. {r['hook'][:60]} — {r['views']:,} views, {r['shares']:,} แชร์")
        if len(ranked) > 3:
            lines.append(f"\n🔻 อ่อนที่สุด: {ranked[-1]['hook'][:60]} — {ranked[-1]['views']:,} views")
    lessons = ""
    if rows or prof:
        try:
            thai, lessons = analyze(rows, prof, deltas)
            if thai:
                lines.append("\n🧠 วิเคราะห์\n" + thai)
        except Exception as e:
            problems.append(f"วิเคราะห์: {str(e)[:100]}")
    if problems:
        lines.append("\n⚠️ ดึงข้อมูลบางส่วนไม่ได้: " + " | ".join(problems))
    text = "\n".join(lines)
    print(text)
    deliver.notify(text)

    history.append({"date": now.date().isoformat(), "profile": prof, "videos": rows})
    os.makedirs("data", exist_ok=True)
    with open(STATS, "w", encoding="utf-8") as f:
        json.dump(history[-26:], f, ensure_ascii=False, indent=1)        # keep ~6 months
    if lessons:
        with open(INSIGHTS, "w", encoding="utf-8") as f:
            f.write(f"From the report of {now.date().isoformat()}:\n{lessons}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
