"""Setup check - costs about $0.01 and ~30 voice characters.

Verifies every key and setting with tiny requests, then sends you a voice
sample and a silent sample video in Telegram. Run this before the first
real video:  GitHub -> Actions -> "Check setup" -> Run workflow.
"""
import os
import shutil
import subprocess
import sys
import tempfile

import requests

import settings

WHERE = "GitHub repo -> Settings -> Secrets and variables -> Actions"
results = []  # (ok, label, detail)


def report(ok, label, detail=""):
    results.append((ok, label, detail))
    print(("OK   " if ok else "FAIL ") + label + (f" - {detail}" if detail else ""))


def check_secrets():
    names = ["ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    missing = [n for n in names if not os.getenv(n)]
    report(not missing, "All 4 secrets present",
           f"missing: {', '.join(missing)} -> add at {WHERE}" if missing else "")


def check_environment():
    from PIL import features
    report(bool(shutil.which("ffmpeg")), "ffmpeg installed")
    report(features.check("raqm"), "Thai text shaping (raqm)",
           "" if features.check("raqm") else "install libraqm0 libfribidi0")


def check_claude():
    if not os.getenv("ANTHROPIC_API_KEY"):
        return report(False, "Claude", "no key")
    import anthropic
    try:
        r = anthropic.Anthropic().messages.create(
            model=settings.CLAUDE_MODEL, max_tokens=10,
            tools=[{"type": settings.WEB_SEARCH_TOOL, "name": "web_search", "max_uses": 1}],
            messages=[{"role": "user", "content": "Reply with the single word OK. Do not use any tools."}])
        report(True, f"Claude key + model {settings.CLAUDE_MODEL} + web search accepted")
    except anthropic.AuthenticationError:
        report(False, "Claude", "key rejected -> re-copy ANTHROPIC_API_KEY")
    except anthropic.NotFoundError:
        report(False, "Claude", f"model '{settings.CLAUDE_MODEL}' not found -> fix CLAUDE_MODEL in settings.py")
    except anthropic.PermissionDeniedError as e:
        report(False, "Claude", f"permission denied: {e}")
    except anthropic.BadRequestError as e:
        msg = str(e)
        if "credit" in msg.lower() or "balance" in msg.lower():
            report(False, "Claude", "no credit -> add credit in Console > Billing")
        elif "web search" in msg.lower() or "web_search" in msg.lower():
            report(False, "Claude", "web search is off -> enable it in Claude Console settings")
        else:
            report(False, "Claude", msg[:200])
    except Exception as e:
        report(False, "Claude", str(e)[:200])


def check_voice(tmp):
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        report(False, "ElevenLabs", "no key")
        return None
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{settings.ELEVENLABS_VOICE_ID}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        json={"text": "ทดสอบเสียง ช่องทันท่วงที", "model_id": settings.ELEVENLABS_MODEL},
        timeout=120)
    if r.status_code == 200:
        path = os.path.join(tmp, "voice_test.mp3")
        with open(path, "wb") as f:
            f.write(r.content)
        report(True, f"ElevenLabs key + voice + model {settings.ELEVENLABS_MODEL}")
        return path
    hint = {401: "key rejected or missing Text to Speech permission -> check the key",
            404: "voice not found -> add the voice to My Voices, re-check ELEVENLABS_VOICE_ID",
            402: "out of credits / plan issue"}.get(r.status_code, "")
    report(False, "ElevenLabs", f"HTTP {r.status_code} {hint} {r.text[:150]}")
    return None


def check_render(tmp):
    """Silent sample video - tests fonts, Thai layout and ffmpeg. Free."""
    try:
        out = os.path.join(tmp, "out")
        subprocess.run([sys.executable, "run.py", "--script", "samples/sample_script.json",
                        "--no-voice", "--out", out], check=True, capture_output=True, text=True,
                       env={k: v for k, v in os.environ.items() if not k.startswith("TELEGRAM")})
        for root, _, files in os.walk(out):
            if "short.mp4" in files:
                report(True, "Video maker (sample, silent)")
                return os.path.join(root, "short.mp4")
        report(False, "Video maker", "no video produced")
    except subprocess.CalledProcessError as e:
        report(False, "Video maker", (e.stderr or str(e))[-300:])
    return None


def check_telegram(voice_path, video_path):
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return report(False, "Telegram", "no token / chat id")
    base = f"https://api.telegram.org/bot{token}"
    r = requests.get(f"{base}/getMe", timeout=30)
    if not r.ok:
        return report(False, "Telegram", "bot token rejected -> re-copy TELEGRAM_BOT_TOKEN")
    r = requests.post(f"{base}/sendMessage", data={"chat_id": chat, "text": "กำลังตรวจระบบ..."}, timeout=30)
    if not r.ok:
        return report(False, "Telegram", "chat id wrong, or you haven't pressed Start in your bot")
    if voice_path:
        with open(voice_path, "rb") as f:
            requests.post(f"{base}/sendAudio", data={"chat_id": chat, "caption": "ตัวอย่างเสียง"},
                          files={"audio": f}, timeout=120)
    if video_path:
        with open(video_path, "rb") as f:
            requests.post(f"{base}/sendVideo", data={"chat_id": chat, "caption": "ตัวอย่างวิดีโอ (ไม่มีเสียง)"},
                          files={"video": f}, timeout=300)
    report(True, "Telegram bot + chat")


def main():
    tmp = tempfile.mkdtemp()
    check_secrets()
    check_environment()
    check_claude()
    voice_path = check_voice(tmp)
    video_path = check_render(tmp)
    check_telegram(voice_path, video_path)

    failed = [r for r in results if not r[0]]
    lines = [("✅ " if ok else "❌ ") + label + (f"\n    {d}" if d and not ok else "") for ok, label, d in results]
    summary = ("พร้อมใช้งาน - กด Run workflow ที่ Daily Short ได้เลย" if not failed
               else f"ยังมี {len(failed)} จุดต้องแก้ (ดูด้านบน)")
    text = "ผลตรวจระบบ\n" + "\n".join(lines) + "\n\n" + summary
    print("\n" + text)
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if token and chat:
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat, "text": text[:4000]}, timeout=30)
        except requests.RequestException:
            pass
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
