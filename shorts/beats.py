"""Animated infographic 'beats' shown in place of the phone for one scene.

  money - a counter ticks up to the amount lost       {"type":"money","amount":21000000,"label":"ความเสียหาย"}
  map   - Thailand zooms in to the province           {"type":"map","province":"จันทบุรี","label":"ตำรวจจับกุมแล้ว"}
  stat  - one big number/fact pops in                 {"type":"stat","value":"17 เดือน","label":"หลอกต่อเนื่องนาน"}
  flow  - 2-4 boxes linked by arrows, a coin travels  {"type":"flow","steps":["เหยื่อ","บัญชีม้า","มิจฉาชีพ"],"caption":"..."}

Every beat draws onto a phone-sized black card so it matches the rest of the video.
"""
import json
import math
import os
import re

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_FILE = os.path.join(ROOT, "assets", "thailand_provinces.json")

YELLOW, BLACK, WHITE, RED = (255, 199, 0), (0, 0, 0), (255, 255, 255), (214, 36, 28)
GRAY = (150, 150, 150)

_provinces = None


def provinces():
    global _provinces
    if _provinces is None:
        with open(MAP_FILE, encoding="utf-8") as f:
            _provinces = json.load(f)["provinces"]
    return _provinces


ALIASES = {"กทม": "กรุงเทพมหานคร", "กรุงเทพ": "กรุงเทพมหานคร", "กรุงเทพฯ": "กรุงเทพมหานคร",
           "อยุธยา": "พระนครศรีอยุธยา", "โคราช": "นครราชสีมา", "สุราษฎร์": "สุราษฎร์ธานี"}


def normalize_province(name):
    """Thai province name as stored in the map file, or None if unknown."""
    n = re.sub(r"^(จังหวัด|จ\.)\s*", "", str(name or "").strip())
    n = ALIASES.get(n, n)
    return n if n in provinces() else None


def parse_amount(v):
    try:
        x = float(re.sub(r"[^\d.]", "", str(v)))
        return x if x > 0 else None
    except ValueError:
        return None


# ---- helpers ----
def _clamp(x):
    return max(0.0, min(1.0, x))


def fade(color, a):
    """Opaque color mixed toward the black card - looks like transparency, no holes."""
    a = _clamp(a)
    return tuple(int(c * a) for c in color) + (255,)


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out_back(x):
    c1 = 1.70158
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


class Beat:
    """Base: a black rounded card the size of the phone."""

    def __init__(self, spec, size, F, fit, fonts):
        self.spec, (self.w, self.h) = spec, size
        self.F, self.fit, self.fonts = F, fit, fonts
        self.scratch = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    def card(self):
        im = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle((0, 0, self.w - 1, self.h - 1), radius=72, fill=BLACK)
        return im

    def text(self, d, s, font_key, sizes, max_w, y, fill, alpha=1.0, anchor="mm", max_lines=1):
        f, lines = self.fit(self.scratch, s, self.fonts[font_key], max_w, sizes, max_lines)
        a, b = f.getmetrics()
        step = int((a + b) * 0.95)
        for i, ln in enumerate(lines):
            d.text((self.w // 2, y + i * step), ln, font=f, anchor=anchor, fill=fade(fill, alpha))
        return len(lines) * step


class MoneyBeat(Beat):
    def __init__(self, *a):
        super().__init__(*a)
        self.amount = parse_amount(self.spec["amount"])
        self.label = self.spec.get("label") or "ความเสียหาย"

    def frame(self, t):
        im = self.card()
        d = ImageDraw.Draw(im)
        x = ease_out_cubic(_clamp(t / 1.3))
        val = self.amount * x
        num = f"{val:,.0f}"
        self.text(d, self.label, "semi", range(60, 40, -2), self.w - 120, 360, WHITE, _clamp(t / 0.25))
        pop = 1.0
        if t > 1.3:   # little punch when the counter lands
            pop = 1 + 0.08 * math.sin(_clamp((t - 1.3) / 0.25) * math.pi)
        f, lines = self.fit(self.scratch, f"{self.amount:,.0f}", self.fonts["head"],
                            self.w - 100, range(220, 80, -6), 1)
        size = max(40, int(f.size * pop))
        d.text((self.w // 2, 580), num, font=self.F(self.fonts["head"], size), anchor="mm", fill=YELLOW + (255,))
        self.text(d, "บาท", "head", range(110, 60, -4), self.w - 200, 750, RED, _clamp((t - 0.2) / 0.3))
        # red bar sweeping under the number
        bw = int((self.w - 220) * x)
        d.rounded_rectangle((110, 840, 110 + bw, 856), radius=8, fill=RED + (255,))
        return im


class StatBeat(Beat):
    def frame(self, t):
        im = self.card()
        d = ImageDraw.Draw(im)
        x = _clamp(t / 0.35)
        s = 0.4 + 0.6 * ease_out_back(x)
        f, lines = self.fit(self.scratch, self.spec["value"], self.fonts["head"],
                            self.w - 120, range(240, 80, -6), 1)
        d.text((self.w // 2, 470), lines[0], font=self.F(self.fonts["head"], max(30, int(f.size * s))),
               anchor="mm", fill=fade(YELLOW, x * 2))
        if self.spec.get("label"):
            self.text(d, self.spec["label"], "semi", range(64, 40, -2), self.w - 120, 690,
                      WHITE, _clamp((t - 0.3) / 0.3), max_lines=2)
        return im


class FlowBeat(Beat):
    def __init__(self, *a, dur=4.0):
        super().__init__(*a)
        self.steps = [str(s) for s in self.spec["steps"]][:4]
        n = len(self.steps)
        self.gap = min(0.75, max(0.35, (dur - 0.8) / max(n, 1)))
        top, bottom = 150, self.h - (230 if self.spec.get("caption") else 150)
        span = bottom - top
        self.ys = [int(top + span * (i + 0.5) / n) for i in range(n)]

    def frame(self, t):
        im = self.card()
        d = ImageDraw.Draw(im)
        bw, bh = self.w - 240, 132
        cx = self.w // 2
        n = len(self.steps)
        for i, (label, y) in enumerate(zip(self.steps, self.ys)):
            ti = t - i * self.gap
            if ti < 0:
                continue
            x = _clamp(ti / 0.3)
            s = 0.6 + 0.4 * ease_out_back(x)
            w2, h2 = int(bw * s / 2), int(bh * s / 2)
            last = i == n - 1
            fill = fade(RED if last else WHITE, x * 2)
            d.rounded_rectangle((cx - w2, y - h2, cx + w2, y + h2), radius=36, fill=fill)
            f, lines = self.fit(self.scratch, label, self.fonts["bold"], bw - 60, range(58, 34, -2), 1)
            d.text((cx, y), lines[0], font=f, anchor="mm",
                   fill=WHITE + (255,) if last else BLACK + (255,))
            if i > 0:   # arrow from the box above, then a coin travels down it
                y0, y1 = self.ys[i - 1] + bh // 2 + 10, y - bh // 2 - 14
                a = _clamp(ti / 0.25)
                ye = int(y0 + (y1 - y0) * a)
                d.line((cx, y0, cx, ye), fill=YELLOW + (255,), width=10)
                if a >= 1:
                    d.polygon([(cx - 26, y1 - 22), (cx + 26, y1 - 22), (cx, y1 + 6)], fill=YELLOW + (255,))
                c = _clamp((ti - 0.05) / (self.gap * 0.9))
                if 0 < c < 1:
                    yc = int(y0 + (y1 - y0) * ease_in_out(c))
                    d.ellipse((cx + 30, yc - 26, cx + 82, yc + 26), fill=YELLOW + (255,), outline=BLACK + (255,), width=4)
                    d.text((cx + 56, yc), "฿", font=self.F(self.fonts["bold"], 34), anchor="mm", fill=BLACK + (255,))
        cap = self.spec.get("caption")
        if cap:
            self.text(d, cap, "semi", range(56, 36, -2), self.w - 120, self.h - 120, YELLOW,
                      _clamp((t - n * self.gap) / 0.3))
        return im


class MapBeat(Beat):
    SS = 2          # supersampling for smooth edges
    ZOOM_T = 1.4

    def __init__(self, *a):
        super().__init__(*a)
        self.target = self.spec["province"]
        self.label = self.spec.get("label", "")
        self.k = math.cos(math.radians(13))
        self.polys = {n: [[(lon * self.k, -lat) for lon, lat in ring] for ring in rings]
                      for n, rings in provinces().items()}
        allpts = [p for rings in self.polys.values() for r in rings for p in r]
        self.full = self._bbox(allpts, pad=0.06)
        tpts = [p for r in self.polys[self.target] for p in r]
        self.center = (sum(p[0] for p in tpts) / len(tpts), sum(p[1] for p in tpts) / len(tpts))
        self.near = self._bbox(tpts, pad=1.6, min_size=2.6)
        self.map_box = (30, 210, self.w - 30, self.h - 60)

    @staticmethod
    def _bbox(pts, pad=0.1, min_size=0.0):
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        w = max(max(xs) - min(xs), min_size) * (1 + pad)
        h = max(max(ys) - min(ys), min_size) * (1 + pad)
        return cx, cy, w, h

    def frame(self, t):
        im = self.card()
        x0, y0, x1, y1 = self.map_box
        mw, mh = (x1 - x0) * self.SS, (y1 - y0) * self.SS
        z = ease_in_out(_clamp((t - 0.25) / self.ZOOM_T))
        cx = self.full[0] + (self.near[0] - self.full[0]) * z
        cy = self.full[1] + (self.near[1] - self.full[1]) * z
        w = self.full[2] + (self.near[2] - self.full[2]) * z
        h = self.full[3] + (self.near[3] - self.full[3]) * z
        w *= 1 - 0.04 * _clamp((t - 0.25 - self.ZOOM_T) / 3)       # keep drifting in slowly
        scale = min(mw / w, mh / (h * 1.0))
        ox, oy = mw / 2 - cx * scale, mh / 2 - cy * scale
        layer = Image.new("RGBA", (mw, mh), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        pulse = 0.5 + 0.5 * math.sin(t * 6)
        hot = z > 0.55
        for name, rings in self.polys.items():
            target = name == self.target
            fill = (YELLOW if hot else (90, 90, 90)) if target else (42, 42, 42)
            for r in rings:
                pts = [(px * scale + ox, py * scale + oy) for px, py in r]
                if len(pts) > 2:
                    d.polygon(pts, fill=fill + (255,), outline=(85, 85, 85, 255))
        if hot:   # pulsing red outline on the target
            for r in self.polys[self.target]:
                pts = [(px * scale + ox, py * scale + oy) for px, py in r]
                d.line(pts + [pts[0]], fill=RED + (255,), width=int((5 + 6 * pulse) * self.SS), joint="curve")
            px, py = self.center[0] * scale + ox, self.center[1] * scale + oy
            drop = ease_out_back(_clamp((z - 0.55) / 0.45))
            r = 26 * self.SS
            py -= (1 - drop) * 120 * self.SS
            d.ellipse((px - r, py - r, px + r, py + r), fill=RED + (255,), outline=WHITE + (255,), width=6 * self.SS)
        layer = layer.resize((x1 - x0, y1 - y0), Image.LANCZOS)
        im.alpha_composite(layer, dest=(x0, y0))
        d = ImageDraw.Draw(im)
        a = _clamp((z - 0.5) / 0.3)
        self.text(d, f"จ.{self.target}" if self.target != "กรุงเทพมหานคร" else self.target,
                  "head", range(110, 60, -4), self.w - 100, 110, YELLOW, max(0.35, a))
        if self.label:
            self.text(d, self.label, "semi", range(52, 34, -2), self.w - 120, 190, WHITE, a)
        return im


def make(spec, size, dur, F, fit, fonts):
    kind = spec.get("type")
    if kind == "money":
        return MoneyBeat(spec, size, F, fit, fonts)
    if kind == "map":
        return MapBeat(spec, size, F, fit, fonts)
    if kind == "stat":
        return StatBeat(spec, size, F, fit, fonts)
    if kind == "flow":
        return FlowBeat(spec, size, F, fit, fonts, dur=dur)
    raise ValueError(f"unknown beat type {kind}")


def validate(spec):
    """Cleaned beat spec, or None if it can't be drawn reliably."""
    if not isinstance(spec, dict):
        return None
    kind = spec.get("type")
    label = str(spec.get("label") or "").strip()[:40]
    if kind == "money":
        amt = parse_amount(spec.get("amount"))
        return {"type": "money", "amount": amt, "label": label} if amt else None
    if kind == "map":
        p = normalize_province(spec.get("province"))
        return {"type": "map", "province": p, "label": label} if p else None
    if kind == "stat":
        v = str(spec.get("value") or "").strip()
        return {"type": "stat", "value": v[:16], "label": label} if v else None
    if kind == "flow":
        steps = [str(s).strip()[:16] for s in (spec.get("steps") or []) if str(s).strip()]
        if 2 <= len(steps) <= 4:
            return {"type": "flow", "steps": steps, "caption": str(spec.get("caption") or "").strip()[:30]}
    return None
