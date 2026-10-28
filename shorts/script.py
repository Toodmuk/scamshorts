"""Researches one recent Thai scam with Claude + web search and returns
the script JSON that the renderer uses."""
import json
import os
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
  "reveal": "Thai slogan for the reveal moment, <= 14 chars, e.g. ของปลอม!",
  "rule": {"if": ["condition 1, <= 16 chars", "condition 2, <= 16 chars (optional)"], "then": "action, <= 12 chars, e.g. อย่าโอน!"},
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
- Visual beats: 3-6 scenes use "visual" INSTEAD of "message" - an animated infographic
  shown in place of the chat. Use only facts from the sources:
    {{"type": "money", "amount": <number in baht>, "label": "<what the amount is>"}}
        - money lost or demanded. Great as the FIRST scene to lead with the loss.
    {{"type": "map", "province": "<Thai province name, e.g. จันทบุรี>", "label": "<short>"}}
        - only when the source names the province (where it happened / arrest).
    {{"type": "stat", "value": "<short number + unit, e.g. 17 เดือน, 300 ราย>", "label": "<short>"}}
        - a duration, a victim count, or another single striking number.
    {{"type": "flow", "steps": ["<2-4 short boxes, <= 14 chars each>"], "caption": "<short>"}}
        - how the money or the trick moves, e.g. ["เหยื่อ", "บัญชีม้า", "มิจฉาชีพ"]. For a scheme that
          repeats, 3 steps and a caption with a number, e.g. "วนซ้ำ 17 เดือน".
    {{"type": "compare", "title": "<short>", "items": [{{"label": "<short>", "value": <number>, "unit": "<short>"}}, {{"label": "...", "value": <number>, "unit": "..."}}]}}
        - two numbers side by side (e.g. what was promised vs what was lost, this year vs last year).
    {{"type": "bars", "title": "<short>", "unit": "<short>", "items": [{{"label": "<short>", "value": <number>}}]}}
        - 2-5 numbers to compare as rising bars (e.g. cases per year, losses per scam type).
    {{"type": "percent", "value": <0-100>, "label": "<short>"}}
        - one percentage from the sources (e.g. share of victims who are over 60).
    {{"type": "proof", "items": ["<1-3 short names of the fake proof shown, <= 18 chars each>"]}}
        - the fake documents, slips, pages or messages used to convince the victim,
          e.g. ["สเตทเมนต์ธนาคาร", "เอกสารตำรวจ"] or ["สลิปโอนเงินปลอม"] or ["หน้าเว็บธนาคารปลอม"].
  Labels and steps are short Thai phrases. The narration of that scene must talk about it.
- tip: the one red-flag rule that would stop this scam.
- reveal: 1-3 words slammed on screen at the reveal (e.g. ของปลอม!, มิจฉาชีพ!, อย่ากด!).
- rule: the same red-flag rule split for the screen: "if" = 1-2 short conditions, "then" = the
  action, e.g. {{"if": ["ไม่เคยเจอตัว", "ขอยืมเงิน"], "then": "อย่าโอน!"}}.
- end_narration: restate the rule, say สงสัยโทร 1441, and ask viewers to send the clip
  to their parents or family.
- 8-11 scenes in total (chat scenes + 3-6 visual scenes), so something new appears every few seconds.
- Total narration (scenes + end) 700-1000 Thai characters, about 60-80 seconds. Tell the story
  like a short documentary: what happened, how the trick works step by step, the numbers, the
  arrest or warning, then the rule.
- No emoji anywhere.
- topic: short English slug for the scam type, used to avoid repeats.

When finished, call the submit_script tool with an object of this shape (do not write the
JSON as text in your reply):
{SCHEMA}"""

EDITOR = """Now act as a strict Thai editor and fact-checker for the draft you just wrote.
1. Check every claim against the sources you found. Remove or fix anything they don't
   support. Amounts and numbers must match the sources.
2. Read every narration line aloud in your head as a Thai viewer: fix anything stiff,
   formal, awkward or doubled. It must sound like natural spoken Thai.
3. Make the hook and first line hit harder - lead with the loss or the twist.
4. Check every visual: amounts, numbers and the province must match the sources exactly.
5. Check the particle rule and every other rule again.
Then call submit_script again with the corrected final object (same shape)."""


def _extract_json(text):
    """JSON written as text (backup path). Repairs common slips such as an unescaped
    quote inside Thai text or a missing comma."""
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0:
        raise ValueError("no JSON object in model output")
    chunk = text[start:end + 1] if end > start else text[start:]
    try:
        return json.loads(chunk)
    except json.JSONDecodeError:
        import json_repair
        d = json_repair.loads(chunk)
        if not isinstance(d, dict) or not d.get("scenes"):
            raise ValueError("model output could not be repaired into a script")
        return d


SUBMIT = {
    "name": "submit_script",
    "description": "Submit the finished Short script. Call this once at the end with the complete object.",
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {"type": "string"}, "hook": {"type": "string"}, "source_label": {"type": "string"},
            "app": {"type": "string", "enum": ["sms", "line"]}, "sender": {"type": "string"},
            "reveal": {"type": "string"}, "rule": {"type": "object"},
            "scenes": {"type": "array", "items": {"type": "object"}},
            "tip": {"type": "string"}, "end_narration": {"type": "string"}, "title": {"type": "string"},
            "description": {"type": "string"}, "hashtags": {"type": "array", "items": {"type": "string"}},
            "sources": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["topic", "hook", "scenes", "tip", "end_narration", "title", "sources"],
    },
}


def _script_of(resp):
    """(script dict, tool_use id or None) from a response - the tool call if there is one,
    otherwise JSON found in the text."""
    for b in resp.content:
        if getattr(b, "type", "") == "tool_use" and getattr(b, "name", "") == "submit_script":
            if isinstance(b.input, dict) and b.input.get("scenes"):
                return b.input, b.id
    return _extract_json(_text_of(resp)), None


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
    for k in ("hook", "sender", "tip", "end_narration", "title", "description", "source_label", "reveal"):
        d[k] = str(d.get(k) or "")
    d["reveal"] = d["reveal"].strip()[:16] or "มิจฉาชีพ!"
    rule = d.get("rule") if isinstance(d.get("rule"), dict) else {}
    conds = [str(x).strip()[:20] for x in (rule.get("if") or []) if str(x).strip()][:2]
    then = str(rule.get("then") or "").strip()[:14]
    if not conds or not then:                  # derive a screen rule from the tip
        parts = d["tip"].replace("=", " ").split()
        half = max(1, (len(parts) + 1) // 2)
        conds = [x for x in (" ".join(parts[:half]), " ".join(parts[half:])) if x][:2] or ["ระวัง"]
        then = then or "อย่าหลงเชื่อ!"
    d["rule"] = {"if": conds, "then": then}
    scenes = [s for s in d["scenes"] if isinstance(s, dict) and s.get("narration")]
    if not 2 <= len(scenes) <= 13:
        raise ValueError(f"expected 2-13 scenes, got {len(scenes)}")
    n_vis = 0
    for s in scenes:
        vis = beats.validate(s.get("visual")) if n_vis < 7 else None
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


def generate(covered_topics, today, target_chars=None):
    import anthropic

    client = anthropic.Anthropic()
    tools = [{"type": SEARCH_TOOL, "name": "web_search", "max_uses": 4}]
    learn = ""
    try:   # last weekly report's lessons (style, hooks, topics) - never overrides the fact rules
        with open(os.path.join("data", "insights.txt"), encoding="utf-8") as f:
            learn = f.read().strip()[:1500]
    except OSError:
        pass
    messages = [{
        "role": "user",
        "content": (f"Today is {today}. Already covered (do not repeat): "
                    f"{json.dumps(covered_topics, ensure_ascii=False)}\n"
                    + (f"Lessons from last week's performance (apply to style, hooks and topic choice only; "
                       f"all the rules above still apply):\n{learn}\n" if learn else "")
                    + (f"Length for this video: total narration {max(350, target_chars - 250)}-{target_chars} Thai "
                       f"characters (this overrides the length rule; use fewer scenes if needed).\n" if target_chars else "")
                    + "Research and write today's Short, then call submit_script."),
    }]

    tools.append(SUBMIT)

    def call():
        resp = client.messages.create(model=MODEL, max_tokens=8000, system=SYSTEM,
                                      tools=tools, messages=messages)
        # Long searches can pause mid-turn; continue until finished.
        while resp.stop_reason == "pause_turn":
            _add_assistant(messages, resp.content)
            resp = client.messages.create(model=MODEL, max_tokens=8000, system=SYSTEM,
                                          tools=tools, messages=messages)
        return resp

    def reply_to(resp, tool_id, text):
        """Next user turn: answer the tool call (if any), then say what to do."""
        _add_assistant(messages, resp.content)
        content = [{"type": "tool_result", "tool_use_id": tool_id, "content": "Received."}] if tool_id else []
        content.append({"type": "text", "text": text})
        messages.append({"role": "user", "content": content})

    resp, draft, tool_id, last_err = call(), None, None, None
    for attempt in range(3):
        try:
            raw, tool_id = _script_of(resp)
            draft = validate(raw)
            break
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
            print(f"Script attempt {attempt + 1} not usable ({e}) - asking again.")
            ids = [b.id for b in resp.content if getattr(b, "type", "") == "tool_use"]
            reply_to(resp, ids[0] if ids else None,
                     f"That was not usable ({e}). Call submit_script now with the complete, finished script.")
            resp = call()
    if draft is None:
        raise RuntimeError(f"Claude did not return a usable script after 3 tries: {last_err}")

    draft["editor_ok"] = False
    if not EDITOR_PASS:
        return draft
    try:  # second pass: fact-check + natural Thai. Keeps the draft if this fails.
        reply_to(resp, tool_id, EDITOR)
        final = validate(_script_of(call())[0])
        final["editor_ok"] = True
        print("Editor pass applied.")
        return final
    except Exception as e:
        print(f"Editor pass skipped ({e}) - using the draft.")
        return draft
