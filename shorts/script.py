"""Researches one recent Thai scam with Claude + web search and returns
the script JSON that the renderer uses."""
import json
import re

import settings
from . import beats

MODEL = settings.CLAUDE_MODEL
SEARCH_TOOL = settings.WEB_SEARCH_TOOL
# newer settings - safe defaults if settings.py hasn't been updated
NARRATOR = getattr(settings, "NARRATOR", "neutral")
NEWS_DAYS = int(getattr(settings, "NEWS_DAYS", 3))
EDITOR_PASS = bool(getattr(settings, "EDITOR_PASS", True))

PARTICLES = {
    "male": "The narrator is a man: when a polite particle is needed use ครับ, never ค่ะ/คะ.",
    "female": "The narrator is a woman: when a polite particle is needed use ค่ะ/คะ, never ครับ.",
    "neutral": "Narration uses NO ครับ/ค่ะ/คะ at all (the voice's gender is unknown) - use นะ, เลย, ด้วย instead.",
}

SCHEMA = """{
  "topic": "english-slug-of-scam-type",
  "hook": "Thai, <= 28 chars",
  "source_label": "Thai, <= 36 chars, e.g. ที่มา: ตำรวจไซเบอร์ · 10 ต.ค.",
  "app": "sms" | "line",
  "sender": "name shown at top of the chat",
  "scenes": [
    {"narration": "Thai, <= 80 chars", "highlight": ["1-2 key words copied exactly from narration"],
     "message": {"from": "them" | "me", "text": "Thai"}, "stamp": false},
    {"narration": "...", "highlight": ["..."],
     "visual": {"type": "money", "amount": 21000000, "label": "ความเสียหาย"}}
  ],
  "tip": "Thai, <= 60 chars",
  "end_narration": "Thai, <= 100 chars",
  "title": "Thai, <= 70 chars, ends with #shorts",
  "description": "Thai, 2-3 sentences, then a line starting with แหล่งข้อมูล:",
  "hashtags": ["#..."],
  "sources": [{"title": "...", "url": "https://..."}]
}"""

SYSTEM = f"""You write one YouTube Short per day for a Thai scam-awareness channel.
Audience: ordinary Thai adults and their parents. Goal: they recognise the scam
the second it reaches them, and they forward the clip to family.

Process
1. Use web search to find ONE specific scam case or warning reported in Thailand in
   the last {NEWS_DAYS} days by official or reputable sources (AOC 1441, Thai police
   cyber bureau, DE ministry, Bank of Thailand, major Thai banks, Thai PBS, Thairath,
   Matichon, Khaosod, Bangkok Post). Prefer a case with concrete details: amount lost,
   number of victims, the platform used, who was impersonated. Only if nothing fits,
   widen to 14 days.
2. Skip any topic in the "already covered" list.
3. Write only what the sources support. Never invent statistics, amounts, victim
   stories, quotes or official statements.

Format: a reenacted chat between the scammer ("them") and the victim ("me") on SMS
or LINE, told by a narrator. The chat appears message by message as the narrator speaks.

Rules
- Spoken Thai, casual and natural, like a younger sibling warning family. Short
  sentences. Put a space between phrases every 15-25 characters. Read every line
  aloud in your head - no awkward or doubled words (e.g. write "ของราคาถูก" not "ของถูกถูกใจ").
- {PARTICLES.get(NARRATOR, PARTICLES["neutral"])}
- Lead with the loss: hook and the first narration line state the consequence or the
  twist first (e.g. โอนมัดจำไป 1,500 โดนบล็อกทันที), then the scenes show how it happened.
- hook: concrete and specific to this case, paid off by the video. No emoji.
- source_label: "ที่มา: <agency or outlet> · <day> <Thai month abbr>" for the main source.
- Each scene: narration, 1-2 highlight words (copied exactly from that narration -
  amounts, the red flag, or the action to avoid), and either a message or a visual.
- Use concrete details from the sources (amounts, platform, what was promised).
- Messages look realistic, but: mask every link as https://xxxxx.xx/..., mask phone
  numbers as 08x-xxx-xxxx, no real account numbers, no real people's names. The chat
  sender is a believable FICTIONAL name (e.g. "Mint Shop ของแท้100%"), never a real
  company or bank. Narration and title MAY name who was impersonated when the source
  names it (e.g. แอบอ้างการไฟฟ้า) - that is what people search for.
- Exactly one scene has "stamp": true - the moment the scam is revealed (a chat scene).
- Visual beats: 2-3 scenes use "visual" INSTEAD of "message" - an animated infographic
  shown in place of the chat. Use only facts from the sources:
    {{"type": "money", "amount": <number in baht>, "label": "<what the amount is>"}}
        - money lost or demanded. Great as the FIRST scene to lead with the loss.
    {{"type": "map", "province": "<Thai province name, e.g. จันทบุรี>", "label": "<short>"}}
        - only when the source names the province (where it happened / arrest).
    {{"type": "stat", "value": "<short number + unit, e.g. 17 เดือน, 300 ราย>", "label": "<short>"}}
        - a duration, a victim count, or another single striking number.
    {{"type": "flow", "steps": ["<2-4 short boxes, <= 14 chars each>"], "caption": "<short>"}}
        - how the money or the trick moves, e.g. ["เหยื่อ", "บัญชีม้า", "มิจฉาชีพ"].
  Labels and steps are short Thai phrases. The narration of that scene must talk about it.
- tip: the one red-flag rule that would stop this scam.
- end_narration: restate the rule, say สงสัยโทร 1441, and ask viewers to send the clip
  to their parents or family.
- 5-7 scenes in total (chat scenes + 2-3 visual scenes).
- Total narration (scenes + end) 280-420 Thai characters, about 28-38 seconds.
- No emoji anywhere.
- topic: short English slug for the scam type, used to avoid repeats.

Output ONLY this JSON object - no prose, no markdown fences:
{SCHEMA}"""

EDITOR = """Now act as a strict Thai editor and fact-checker for the draft you just wrote.
1. Check every claim against the sources you found. Remove or fix anything they don't
   support. Amounts and numbers must match the sources.
2. Read every narration line aloud in your head as a Thai viewer: fix anything stiff,
   formal, awkward or doubled. It must sound like natural spoken Thai.
3. Make the hook and first line hit harder - lead with the loss or the twist.
4. Check every visual: amounts, numbers and the province must match the sources exactly.
5. Check the particle rule and every other rule again.
Return ONLY the final JSON object, same schema, no prose."""


def _extract_json(text):
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start:end + 1])


def _add_assistant(messages, content):
    """Append an assistant turn, merging with the previous one if it was also
    the assistant's (happens after a paused web search)."""
    if messages and messages[-1]["role"] == "assistant":
        messages[-1] = {"role": "assistant", "content": list(messages[-1]["content"]) + list(content)}
    else:
        messages.append({"role": "assistant", "content": list(content)})


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
    for k in ("hook", "sender", "tip", "end_narration", "title", "description", "source_label"):
        d[k] = str(d.get(k) or "")
    scenes = [s for s in d["scenes"] if isinstance(s, dict) and s.get("narration")]
    if not 2 <= len(scenes) <= 9:
        raise ValueError(f"expected 2-9 scenes, got {len(scenes)}")
    n_vis = 0
    for s in scenes:
        vis = beats.validate(s.get("visual")) if n_vis < 3 else None
        if vis:
            s["visual"] = vis
            s.pop("message", None)        # a scene shows either the chat or a visual
            n_vis += 1
        else:
            s.pop("visual", None)
        m = s.get("message")
        if not isinstance(m, dict) or not m.get("text") or m.get("from") not in ("them", "me"):
            s.pop("message", None)
        s["stamp"] = s.get("stamp") is True
        hl = s.get("highlight") or []
        if isinstance(hl, str):
            hl = [hl]
        s["highlight"] = [str(w).strip() for w in hl if str(w).strip() and str(w).strip() in s["narration"]][:3]
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
            _add_assistant(messages, resp.content)
            resp = client.messages.create(model=MODEL, max_tokens=4000, system=SYSTEM,
                                          tools=tools, messages=messages)
        return resp

    resp = call()
    try:
        draft = validate(_extract_json(_text_of(resp)))
    except (ValueError, json.JSONDecodeError) as e:
        _add_assistant(messages, resp.content)
        messages.append({"role": "user", "content":
                         f"That output was not usable ({e}). Return only the JSON object."})
        resp = call()
        draft = validate(_extract_json(_text_of(resp)))

    if not EDITOR_PASS:
        return draft
    try:  # second pass: fact-check + natural Thai. Keeps the draft if this fails.
        _add_assistant(messages, resp.content)
        messages.append({"role": "user", "content": EDITOR})
        final = validate(_extract_json(_text_of(call())))
        print("Editor pass applied.")
        return final
    except Exception as e:
        print(f"Editor pass skipped ({e}) - using the draft.")
        return draft
