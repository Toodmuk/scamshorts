"""Researches one recent Thai scam with Claude + web search and returns
the script JSON that the renderer uses."""
import json
import re

import settings

MODEL = settings.CLAUDE_MODEL
SEARCH_TOOL = settings.WEB_SEARCH_TOOL

SCHEMA = """{
  "topic": "english-slug-of-scam-type",
  "hook": "Thai, <= 28 chars",
  "app": "sms" | "line",
  "sender": "name shown at top of the chat",
  "scenes": [
    {"narration": "Thai, <= 90 chars", "message": {"from": "them" | "me", "text": "Thai"}, "stamp": false}
  ],
  "tip": "Thai, <= 60 chars",
  "end_narration": "Thai, <= 110 chars",
  "title": "Thai, <= 70 chars, ends with #shorts",
  "description": "Thai, 2-3 sentences, then a line starting with แหล่งข้อมูล:",
  "hashtags": ["#..."],
  "sources": [{"title": "...", "url": "https://..."}]
}"""

SYSTEM = f"""You write one YouTube Short per day for a Thai scam-awareness channel.
Audience: ordinary Thai adults and their parents. Goal: they recognise the scam
the second it reaches them, and they forward the clip to family.

Process
1. Use web search to find ONE scam pattern reported in Thailand in the last 14 days
   by official or reputable sources (e.g. AOC 1441, Thai police cyber bureau, the DE
   ministry, Bank of Thailand, major Thai banks' warnings, Thai PBS, Thairath,
   Matichon, Bangkok Post). If nothing new, pick a still-active pattern that has a
   recent source.
2. Skip any topic in the "already covered" list.
3. Write only what the sources support. Never invent statistics, amounts, victim
   stories, quotes or official statements.

Format: a reenacted chat between the scammer ("them") and the victim ("me") on SMS
or LINE, told by a narrator. The chat appears message by message as the narrator speaks.

Rules
- Spoken Thai, casual and clear, like warning a friend. Short sentences. Put a space
  between phrases every 15-25 characters, the way Thai is normally written.
- hook: names the exact situation the viewer will face (e.g. ได้ SMS แบบนี้ อย่ากด!).
  It must be paid off by the video. No emoji.
- 4-7 scenes. Each scene has a narration and an optional message.
- Messages look realistic, but: mask every link as https://xxxxx.xx/..., mask phone
  numbers as 08x-xxx-xxxx, no real account numbers, no real people's names, and name
  impersonated organisations only generically (ธนาคาร, การไฟฟ้า, ขนส่ง, ตำรวจ) - never
  a real bank or company name.
- Exactly one scene has "stamp": true - the moment the scam is revealed.
- tip: the one red-flag rule that would stop this scam.
- end_narration: restate the rule, say สงสัยโทร 1441, and ask viewers to send the clip
  to their parents or family.
- Total narration (scenes + end) 300-500 Thai characters, about 30-45 seconds.
- No emoji anywhere.
- topic: short English slug for the scam type, used to avoid repeats.

Output ONLY this JSON object - no prose, no markdown fences:
{SCHEMA}"""


def _extract_json(text):
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start:end + 1])


def _text_of(resp):
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def validate(d):
    """Fill defaults and fail loudly on anything the renderer can't use."""
    need = ["hook", "sender", "scenes", "tip", "end_narration", "title"]
    missing = [k for k in need if not d.get(k)]
    if missing:
        raise ValueError(f"script missing fields: {missing}")
    d["app"] = d.get("app") if d.get("app") in ("sms", "line") else "sms"
    d.setdefault("topic", "untitled")
    d.setdefault("description", "")
    tags = d.get("hashtags") or ["#รู้ทันมิจฉาชีพ", "#shorts"]
    if isinstance(tags, str):
        tags = tags.split()
    d["hashtags"] = ["#" + str(t).lstrip("#").strip() for t in tags if str(t).strip("# ")]
    srcs = d.get("sources") or []
    if isinstance(srcs, (str, dict)):
        srcs = [srcs]
    d["sources"] = [s if isinstance(s, dict) else {"title": "", "url": str(s)} for s in srcs]
    for k in ("hook", "sender", "tip", "end_narration", "title", "description"):
        d[k] = str(d.get(k) or "")
    scenes = [s for s in d["scenes"] if isinstance(s, dict) and s.get("narration")]
    if not 2 <= len(scenes) <= 9:
        raise ValueError(f"expected 2-9 scenes, got {len(scenes)}")
    for s in scenes:
        m = s.get("message")
        if not isinstance(m, dict) or not m.get("text") or m.get("from") not in ("them", "me"):
            s.pop("message", None)
        s["stamp"] = s.get("stamp") is True
    if not any(s.get("stamp") for s in scenes):
        scenes[-1]["stamp"] = True
    d["scenes"] = scenes
    return d


def generate(covered_topics, today):
    import anthropic

    client = anthropic.Anthropic()
    tools = [{"type": SEARCH_TOOL, "name": "web_search", "max_uses": 4}]
    messages = [{
        "role": "user",
        "content": (f"Today is {today}. Already covered (do not repeat): "
                    f"{json.dumps(covered_topics, ensure_ascii=False)}\n"
                    "Research and write today's Short. Return only the JSON."),
    }]

    def call():
        resp = client.messages.create(model=MODEL, max_tokens=4000, system=SYSTEM,
                                      tools=tools, messages=messages)
        # Long searches can pause mid-turn; continue until finished.
        while resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            resp = client.messages.create(model=MODEL, max_tokens=4000, system=SYSTEM,
                                          tools=tools, messages=messages)
        return resp

    resp = call()
    try:
        return validate(_extract_json(_text_of(resp)))
    except (ValueError, json.JSONDecodeError) as e:
        messages.append({"role": "assistant", "content": resp.content})
        messages.append({"role": "user", "content":
                         f"That output was not usable ({e}). Return only the JSON object."})
        return validate(_extract_json(_text_of(call())))
