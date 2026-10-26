"""Thai-aware text helpers. Thai has no spaces between words, so we
segment with PyThaiNLP before wrapping lines."""
import re

from pythainlp.corpus.common import thai_words
from pythainlp.tokenize import word_tokenize
from pythainlp.util import Trie

# Scam-vocabulary the default dictionary splits badly (e.g. แอป -> แอ|ป).
_EXTRA = {
    "แอป", "แอปธนาคาร", "ลิงก์", "ไลน์", "คลิป", "มิจฉาชีพ", "โอนเงิน",
    "แก๊งคอลเซ็นเตอร์", "คอลเซ็นเตอร์", "ออนไลน์", "เฟซบุ๊ก", "ติ๊กต็อก",
    "พัสดุ", "ตกค้าง", "ยืนยันตัวตน", "รหัสผ่าน", "โอทีพี", "คิวอาร์โค้ด",
    "สแกน", "บัญชีม้า", "อายัด", "แอดไลน์", "ค่าไฟ", "เงินคืน",
}
_TRIE = Trie(set(thai_words()) | _EXTRA)
_UNITS = {"บาท", "ล้าน", "ล้านบาท", "หมื่น", "พัน", "คน", "ราย", "ครั้ง", "วัน", "นาที", "ชั่วโมง", "%"}

_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200d]")
_COMBINING = re.compile(r"[\u0E31\u0E34-\u0E3A\u0E47-\u0E4E]")


def clean(s):
    """Strip emoji (the fonts can't draw them) and extra whitespace."""
    return _EMOJI.sub("", s or "").strip()


def _clusters(s):
    """Split into grapheme-ish clusters so tone marks stay on their consonant."""
    out = []
    for ch in s:
        if out and _COMBINING.match(ch):
            out[-1] += ch
        else:
            out.append(ch)
    return out


def wrap(text, font, max_w, draw):
    """Wrap text to lines no wider than max_w pixels."""
    lines = []
    for para in clean(text).split("\n"):
        line = ""
        for tok in word_tokenize(para, custom_dict=_TRIE, engine="newmm", keep_whitespace=True):
            cand = line + tok
            if draw.textlength(cand, font=font) <= max_w:
                line = cand
                continue
            if line.strip():
                lines.append(line.strip())
                line = tok.lstrip()
            else:
                line = tok
            # A single token wider than the line (e.g. a long URL): hard split.
            while draw.textlength(line, font=font) > max_w:
                acc = ""
                for c in _clusters(line):
                    if acc and draw.textlength(acc + c, font=font) > max_w:
                        break
                    acc += c
                lines.append(acc)
                line = line[len(acc):]
        if line.strip():
            lines.append(line.strip())
    return lines


def _wrap_phrases(text, font, max_w, draw, strict=False):
    """Wrap on spaces first (Thai uses spaces between phrases), falling back
    to word-level wrapping only for a phrase that is too wide on its own."""
    lines = []
    for para in clean(text).split("\n"):
        line = ""
        phrases = []
        for ph in para.split():   # keep numbers with their words: "ลด 70%", "1,500 บาท"
            if phrases and (ph[0].isdigit() or ph in _UNITS or phrases[-1][-1].isdigit() and ph in _UNITS):
                phrases[-1] += " " + ph
            else:
                phrases.append(ph)
        for ph in phrases:
            cand = f"{line} {ph}".strip()
            if draw.textlength(cand, font=font) <= max_w:
                line = cand
                continue
            if line:
                lines.append(line)
            if draw.textlength(ph, font=font) <= max_w:
                line = ph
            elif strict:
                return [""] * 999  # signal: a phrase doesn't fit at this size
            else:
                parts = wrap(ph, font, max_w, draw)
                lines.extend(parts[:-1])
                line = parts[-1]
        if line:
            lines.append(line)
    return lines


def _balance(fn, text, font, max_w, draw):
    """Same line count, but the narrowest width that achieves it, so the
    last line isn't a one-word orphan."""
    n = len(fn(text, font, max_w, draw))
    lo, hi = max_w * 0.4, max_w
    for _ in range(10):
        mid = (lo + hi) / 2
        if len(fn(text, font, mid, draw)) <= n:
            hi = mid
        else:
            lo = mid
    return fn(text, font, hi, draw)


def wrap_phrases(text, font, max_w, draw, strict=False):
    fn = lambda t, f, w, d: _wrap_phrases(t, f, w, d, strict)
    return _balance(fn, text, font, max_w, draw)


def wrap_words(text, font, max_w, draw):
    return _balance(wrap, text, font, max_w, draw)
