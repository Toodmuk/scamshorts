"""Telegram: sends the daily preview to your phone and reads your
'ok' / 'skip' reply. Skipped silently if Telegram isn't configured."""
import os

import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")   # secret - set in GitHub, not here
CHAT = os.getenv("TELEGRAM_CHAT_ID")      # secret - set in GitHub, not here
BASE = f"https://api.telegram.org/bot{TOKEN}"

OK_WORDS = {"ok", "okay", "yes", "post", "go", "โพสต์", "ได้", "โอเค"}
SKIP_WORDS = {"skip", "no", "stop", "ข้าม", "ไม่", "ไม่โพสต์"}


def enabled():
    return bool(TOKEN and CHAT)


def notify(text):
    if not enabled():
        print(text)
        return
    try:
        requests.post(f"{BASE}/sendMessage", timeout=60, data={
            "chat_id": CHAT, "text": text[:4000], "disable_web_page_preview": "true"})
    except requests.RequestException as e:
        print(f"WARNING: Telegram message failed: {e}")


def telegram(video_path, post_text, post_mode="approve", post_time="18:00"):
    if not enabled():
        print("Telegram not configured - skipping delivery.")
        return False
    if post_mode == "auto":
        caption = f"คลิปวันนี้ จะโพสต์อัตโนมัติ {post_time} น.\nตอบ skip ถ้าไม่อยากให้โพสต์"
    else:
        caption = f"คลิปวันนี้ ตรวจแหล่งข้อมูลด้านล่าง\nตอบ ok ก่อน {post_time} น. เพื่อโพสต์ / skip เพื่อข้าม"
    with open(video_path, "rb") as f:
        r = requests.post(f"{BASE}/sendVideo", timeout=300, files={"video": f}, data={
            "chat_id": CHAT, "caption": caption, "supports_streaming": "true"})
    r.raise_for_status()
    notify(post_text)
    print("Sent to Telegram.")
    return True


def approval(since_unix):
    """Your latest 'ok' or 'skip' sent after since_unix, else None."""
    if not enabled():
        return None
    r = requests.get(f"{BASE}/getUpdates", params={"limit": 100}, timeout=60)
    r.raise_for_status()
    decision = None
    for u in r.json().get("result", []):
        m = u.get("message") or {}
        if str((m.get("chat") or {}).get("id")) != str(CHAT) or m.get("date", 0) < since_unix:
            continue
        text = (m.get("text") or "").strip().lower()
        if text in OK_WORDS:
            decision = "ok"
        elif text in SKIP_WORDS:
            decision = "skip"
    return decision
