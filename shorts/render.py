"""Draws and animates the Short (no extra cost - Pillow + ffmpeg only):
typing dots -> message pops in with a notification sound, slow zoom on the
phone, the red stamp slams down with a shake and a thud, end card pops in."""
import array
import glob
import math
import os
import random
import subprocess
import wave

from PIL import Image, ImageDraw, ImageFont, features

from .text import clean, wrap_phrases, wrap_words

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "assets", "fonts")
MUSIC_DIR = os.path.join(ROOT, "assets", "music")

W, H, FPS = 1080, 1920, 30
HEAD = "ChakraPetch-Bold.ttf"
REG = "IBMPlexSansThai-Regular.ttf"
SEMI = "IBMPlexSansThai-SemiBold.ttf"
BOLD = "IBMPlexSansThai-Bold.ttf"

C = {
    "bg": (255, 199, 0),        # hazard yellow: reads "warning" instantly
    "ink": (0, 0, 0),
    "paper": (255, 255, 255),
    "stamp": (214, 36, 28),
    "sms_head": (246, 246, 246),
    "sms_them": (233, 233, 235),
    "sms_me": (10, 132, 255),
    "line_bg": (140, 166, 205),
    "line_head": (38, 46, 62),
    "line_me": (122, 214, 90),
}

PHONE = (100, 420, 980, 1500)
PW, PH = PHONE[2] - PHONE[0], PHONE[3] - PHONE[1]
PCX, PCY = (PHONE[0] + PHONE[2]) // 2, (PHONE[1] + PHONE[3]) // 2
SUB_TOP = 1548

# ---- animation timing (seconds) - tweak here ----
TYPING = 0.45      # "typing..." dots before a scammer's message
POP = 0.22         # message pop-in
STAMP_AT = 0.30    # stamp starts falling (from start of its scene)
STAMP_LEN = 0.16   # fall time
SHAKE_LEN = 0.35   # phone shake after impact
END_POP = 0.25     # end card pop-in
ZOOM = 0.025       # slow zoom on the phone across the whole video (2.5%)

_fonts = {}


def F(name, size):
    key = (name, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(
            os.path.join(FONTS, name), size, layout_engine=ImageFont.Layout.RAQM)
    return _fonts[key]


def check_thai_support():
    if not features.check("raqm"):
        raise RuntimeError(
            "Pillow has no RAQM layout support, so Thai vowels and tone marks "
            "will render in the wrong place. Install libraqm0 and libfribidi0.")


def lh(font, extra=1.0):
    a, d = font.getmetrics()
    return int((a + d) * extra)


def fit(draw, text, font_name, max_w, sizes, max_lines):
    """Largest size that fits in max_lines, preferring breaks at phrase
    spaces over breaks between words."""
    sizes = list(sizes)
    strict = lambda t, f, w, d: wrap_phrases(t, f, w, d, strict=True)
    for wrapper in (strict, wrap_words):
        for s in sizes:
            f = F(font_name, s)
            lines = wrapper(text, f, max_w, draw)
            if len(lines) <= max_lines:
                return f, lines
    return f, lines[:max_lines]


def text_block(draw, lines, font, cx, top, fill, spacing=1.0, align="center", left=None):
    y = top
    step = lh(font, spacing)
    for ln in lines:
        if align == "center":
            draw.text((cx, y), ln, font=font, fill=fill, anchor="ma")
        else:
            draw.text((left, y), ln, font=font, fill=fill, anchor="la")
        y += step
    return y


# ---- easing ----
def _clamp(x):
    return max(0.0, min(1.0, x))


def ease_out_back(x):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_in_quad(x):
    return x * x


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def _with_alpha(im, a):
    """Copy of an RGBA image with its opacity scaled by a (0..1)."""
    if a >= 0.999:
        return im
    out = im.copy()
    out.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return out


# ---- static pieces ----
def draw_hook(draw, hook):
    f, lines = fit(draw, hook, HEAD, 940, range(104, 58, -4), 2)
    block_h = lh(f, 0.92) * len(lines)
    top = 110 + (290 - block_h) // 2
    text_block(draw, lines, f, W // 2, top, C["ink"], spacing=0.92)


def draw_subtitle(draw, text):
    f, lines = fit(draw, text, SEMI, 880, range(58, 42, -2), 3)
    step = lh(f, 0.96)
    box_h = step * len(lines) + 56
    draw.rounded_rectangle((50, SUB_TOP, W - 50, SUB_TOP + box_h), radius=34, fill=C["ink"])
    text_block(draw, lines, f, W // 2, SUB_TOP + 28, C["paper"], spacing=0.96)


def base_frame(hook, subtitle):
    img = Image.new("RGB", (W, H), C["bg"])
    d = ImageDraw.Draw(img)
    draw_hook(d, hook)
    draw_subtitle(d, subtitle)
    return img


def stamp_image(text="มิจฉาชีพ"):
    f = F(HEAD, 176)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    l, t, r, b = tmp.textbbox((0, 0), text, font=f, anchor="mm")
    pad_x, pad_y = 70, 46
    w, h = int(r - l) + 2 * pad_x, int(b - t) + 2 * pad_y
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = C["stamp"] + (238,)
    d.rounded_rectangle((8, 8, w - 8, h - 8), radius=36, outline=col, width=16)
    d.rounded_rectangle((34, 34, w - 34, h - 34), radius=22, outline=col, width=5)
    d.text((w // 2, h // 2), text, font=f, fill=col, anchor="mm")
    return im.rotate(9, expand=True, resample=Image.BICUBIC)


def end_panel(tip):
    """The black end card, as a phone-sized layer."""
    im = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((0, 0, PW - 1, PH - 1), radius=72, fill=C["ink"])
    cx = PW // 2
    y = 84
    y = text_block(draw, ["กฎข้อเดียวที่ต้องจำ"], F(BOLD, 46), cx, y, C["stamp"])
    f, lines = fit(draw, tip, BOLD, PW - 140, range(76, 50, -2), 4)
    y = text_block(draw, lines, f, cx, y + 30, C["paper"], spacing=0.95)
    y = max(y + 60, PH - 470)
    draw.line((90, y, PW - 90, y), fill=(70, 70, 70), width=3)
    y = text_block(draw, ["สงสัยว่าโดนหลอก"], F(SEMI, 48), cx, y + 44, C["paper"])
    y = text_block(draw, ["โทร 1441"], F(HEAD, 150), cx, y + 4, C["bg"], spacing=0.85)
    text_block(draw, ["ศูนย์ AOC ตลอด 24 ชั่วโมง"], F(REG, 40), cx, y + 6, (190, 190, 190))
    return im


# ---- the phone ----
class Phone:
    """Phone body, header and chat bubbles, in phone-local coordinates."""
    PADX, PADY, GAP = 28, 18, 20
    TYPING_W, TYPING_H = 150, 84

    def __init__(self, app, sender):
        self.app = app
        self.font = F(REG, 44)
        self.step = lh(self.font, 0.86)
        self.scratch = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        sx0, sy0, sx1, sy1 = 16, 16, PW - 16, PH - 16
        head_h = 132
        self.screen = (sx0, sy0, sx1, sy1)
        self.chat = (sx0 + 28, sy0 + head_h + 26, sx1 - 28, sy1 - 34)
        self.max_text_w = int((self.chat[2] - self.chat[0]) * 0.74) - 2 * self.PADX
        self.shell = self._shell(sender, head_h)
        self._cache = {}
        mask = Image.new("L", (sx1 - sx0, sy1 - sy0), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0) + mask.size, radius=58, fill=255)
        self.veil_mask = mask

    def _shell(self, sender, head_h):
        im = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        sx0, sy0, sx1, sy1 = self.screen
        d.rounded_rectangle((0, 0, PW - 1, PH - 1), radius=72, fill=C["ink"])
        screen_bg = C["paper"] if self.app == "sms" else C["line_bg"]
        d.rounded_rectangle((sx0, sy0, sx1, sy1), radius=58, fill=screen_bg)
        head_col = C["sms_head"] if self.app == "sms" else C["line_head"]
        name_col = C["ink"] if self.app == "sms" else C["paper"]
        d.rounded_rectangle((sx0, sy0, sx1, sy0 + head_h + 58), radius=58, fill=head_col)
        d.rectangle((sx0, sy0 + head_h - 10, sx1, sy0 + head_h), fill=head_col)
        d.rectangle((sx0, sy0 + head_h, sx1, sy0 + head_h + 58), fill=screen_bg)
        name_font, name_lines = fit(d, sender, SEMI, sx1 - sx0 - 120, range(42, 30, -2), 1)
        d.text(((sx0 + sx1) // 2, sy0 + head_h // 2 + 8), name_lines[0],
               font=name_font, fill=name_col, anchor="mm")
        d.text((sx0 + 44, sy0 + head_h // 2 + 8), "<", font=F(SEMI, 44),
               fill=C["sms_me"] if self.app == "sms" else C["paper"], anchor="mm")
        if self.app == "sms":
            d.line((sx0, sy0 + head_h, sx1, sy0 + head_h), fill=(220, 220, 220), width=2)
        return im

    def _colors(self, mine):
        if self.app == "sms":
            return (C["sms_me"], C["paper"]) if mine else (C["sms_them"], C["ink"])
        return (C["line_me"], C["ink"]) if mine else (C["paper"], C["ink"])

    def bubble(self, idx, m):
        """Rendered bubble image for message idx (cached)."""
        if idx not in self._cache:
            lines = wrap_phrases(m["text"], self.font, self.max_text_w, self.scratch)[:9]
            w = int(max(self.scratch.textlength(l, font=self.font) for l in lines)) + 2 * self.PADX
            h = self.step * len(lines) + 2 * self.PADY
            fill, tcol = self._colors(m.get("from") == "me")
            im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle((0, 0, w - 1, h - 1), radius=34, fill=fill)
            text_block(d, lines, self.font, 0, self.PADY, tcol, spacing=0.86,
                       align="left", left=self.PADX)
            self._cache[idx] = im
        return self._cache[idx]

    def typing(self, t):
        """Bouncing three-dot 'typing' bubble at time t."""
        w, h = self.TYPING_W, self.TYPING_H
        fill, _ = self._colors(False)
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=34, fill=fill)
        for k in range(3):
            phase = (t * 2.4 - k * 0.18) % 1.0
            lift = math.sin(phase * math.pi) if phase < 0.5 else 0.0
            cx, cy = 42 + k * 33, h // 2 - int(9 * lift)
            shade = 150 - int(60 * lift)
            d.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), fill=(shade, shade, shade))
        return im

    def place(self, items):
        """items: list of (key, image, mine). Returns {key: (x, y)}; keeps the
        newest items that fit, anchored to the bottom once the chat scrolls."""
        cx0, cy0, cx1, cy1 = self.chat
        avail = cy1 - cy0
        total, keep = 0, []
        for it in reversed(items):
            need = it[1].height + (self.GAP if keep else 0)
            if total + need > avail and keep:
                break
            total += need
            keep.insert(0, it)
        y = cy1 - total if len(keep) < len(items) else cy0
        pos = {}
        for key, im, mine in keep:
            pos[key] = (cx1 - im.width if mine else cx0, y)
            y += im.height + self.GAP
        return pos

    def layer(self, placed, skip=None):
        """Shell + every placed bubble except `skip`."""
        im = self.shell.copy()
        for key, (img, xy) in placed.items():
            if key != skip:
                im.alpha_composite(img, dest=xy)
        return im

    def veil(self, im, alpha):
        if alpha <= 0:
            return im
        sx0, sy0 = self.screen[:2]
        white = Image.new("RGBA", self.veil_mask.size, (255, 255, 255, 0))
        white.putalpha(self.veil_mask.point(lambda v: int(v * alpha / 255)))
        im.alpha_composite(white, dest=(sx0, sy0))
        return im


# ---- scenes ----
class ChatScene:
    def __init__(self, phone, msgs_before, new_msg, new_idx, stamp_mode, base, dur):
        self.p, self.base, self.dur = phone, base, dur
        self.new, self.new_idx = new_msg, new_idx
        self.stamp_mode = stamp_mode   # None | "slam" | "on"
        self.mine = bool(new_msg) and new_msg.get("from") == "me"
        self.pop_at = (0.12 if self.mine else TYPING) if new_msg else 0

        before = [(i, phone.bubble(i, m), m.get("from") == "me") for i, m in msgs_before]
        def placed(items):
            pos = phone.place(items)
            return {k: (img, pos[k]) for k, img, _ in items if k in pos}

        if new_msg:
            after = before + [(new_idx, phone.bubble(new_idx, new_msg), self.mine)]
            self.after = placed(after)
            self.l_pop = phone.layer(self.after, skip=new_idx)
            self.l_full = phone.layer(self.after)
            if not self.mine:
                typ = phone.typing(0)
                tplaced = placed(before + [("typing", typ, False)])
                self.typing_xy = tplaced["typing"][1]
                self.l_typing = phone.layer(tplaced, skip="typing")
        else:
            self.l_full = phone.layer(placed(before))
        if stamp_mode == "on":   # scam already revealed: keep the chat dimmed
            for name in ("l_full", "l_pop", "l_typing"):
                if hasattr(self, name):
                    setattr(self, name, phone.veil(getattr(self, name).copy(), 150))

    def phone_layer(self, t):
        p = self.p
        if self.new and not self.mine and t < TYPING:
            im = self.l_typing.copy()
            im.alpha_composite(p.typing(t), dest=self.typing_xy)
        elif self.new and t < self.pop_at + POP:
            im = self.l_pop.copy()
            x = _clamp((t - self.pop_at) / POP)
            if x > 0:
                b = p.bubble(self.new_idx, self.new)
                s = 0.55 + 0.45 * ease_out_back(x)
                bw, bh = max(1, int(b.width * s)), max(1, int(b.height * s))
                bs = _with_alpha(b.resize((bw, bh), Image.BICUBIC), _clamp(x / 0.5))
                fx, fy = self.after[self.new_idx][1]
                ax = fx + b.width - bw if self.mine else fx   # grow from the tail corner
                im.alpha_composite(bs, dest=(ax, fy + b.height - bh))
        else:
            im = self.l_full if self.stamp_mode != "slam" else self.l_full.copy()
        if self.stamp_mode == "slam":
            a = _clamp((t - STAMP_AT) / STAMP_LEN)
            im = p.veil(im if im is not self.l_full else im.copy(), int(150 * a))
        return im


class Renderer:
    def __init__(self, data, durs):
        check_thai_support()
        self.data = data
        self.phone = Phone(data["app"], data["sender"])
        self.stamp = stamp_image()
        self.durs = durs
        self.scenes, self.sfx = [], []
        msgs, stamped, t0 = [], False, 0.0
        for i, s in enumerate(data["scenes"]):
            base = base_frame(data["hook"], clean(s["narration"]))
            m = s.get("message")
            mode = "on" if stamped else ("slam" if s.get("stamp") else None)
            sc = ChatScene(self.phone, list(msgs), m, len(msgs), mode, base, durs[i])
            self.scenes.append(sc)
            if m:
                self.sfx.append((t0 + sc.pop_at, "pop" if sc.mine else "ding"))
                msgs.append((len(msgs), m))
            if mode == "slam":
                self.sfx.append((t0 + STAMP_AT + STAMP_LEN - 0.02, "thud"))
                stamped = True
            t0 += durs[i]
        self.chat_total = t0
        self.end_base = base_frame(data["hook"], clean(data["end_narration"]))
        self.end_panel = end_panel(data["tip"])
        self.sfx.append((t0, "pop"))

    def _phone_frame(self, sc, t, gt):
        layer = sc.phone_layer(t)
        s = 1 + ZOOM * (gt / max(self.chat_total, 0.01))
        lw, lhh = int(PW * s), int(PH * s)
        z = layer.resize((lw, lhh), Image.BILINEAR)
        dx = dy = 0
        stamp = None
        if sc.stamp_mode in ("slam", "on"):
            ts = t - STAMP_AT if sc.stamp_mode == "slam" else 99
            if ts >= 0:
                x = _clamp(ts / STAMP_LEN)
                sc_ = 1.9 - 0.9 * ease_in_quad(x)
                st = self.stamp
                if sc_ != 1.0:
                    st = st.resize((int(st.width * sc_), int(st.height * sc_)), Image.BICUBIC)
                stamp = _with_alpha(st, _clamp(x * 1.6))
            ti = ts - STAMP_LEN
            if 0 <= ti < SHAKE_LEN:
                k = math.exp(-8 * ti)
                dx = int(16 * k * math.sin(2 * math.pi * 17 * ti))
                dy = int(8 * k * math.cos(2 * math.pi * 13 * ti))
        frame = sc.base.copy()
        frame.paste(z, (PCX - lw // 2 + dx, PCY - lhh // 2 + dy), z)
        if stamp is not None:
            frame.paste(stamp, (PCX - stamp.width // 2 + dx, PCY + 60 - stamp.height // 2 + dy), stamp)
        return frame

    def _end_frame(self, t):
        x = _clamp(t / END_POP)
        frame = self.end_base.copy()
        s = 0.94 + 0.06 * ease_out_cubic(x)
        p = self.end_panel
        if s < 0.999:
            p = p.resize((int(PW * s), int(PH * s)), Image.BILINEAR)
        p = _with_alpha(p, _clamp(x * 1.5))
        frame.paste(p, (PCX - p.width // 2, PCY - p.height // 2), p)
        return frame

    def frames(self):
        gt = 0.0
        for sc, d in zip(self.scenes, self.durs):
            for f in range(round(d * FPS)):
                t = f / FPS
                yield self._phone_frame(sc, t, gt + t)
            gt += d
        for f in range(round(self.durs[-1] * FPS)):
            yield self._end_frame(f / FPS)

    def cover(self):
        sc = self.scenes[0]
        return self._phone_frame(sc, sc.dur - 1 / FPS, sc.dur)


# ---- sound effects (synthesised, no files needed) ----
SR = 44100


def _write_wav(path, samples):
    data = array.array("h", (int(max(-1.0, min(1.0, v)) * 32767) for v in samples))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def make_sfx(tmp):
    rnd = random.Random(7)
    paths = {k: os.path.join(tmp, f"sfx_{k}.wav") for k in ("ding", "pop", "thud")}
    n = int(SR * 0.6)
    _write_wav(paths["ding"], [
        (0.6 * math.sin(2 * math.pi * 1320 * (i / SR)) + 0.4 * math.sin(2 * math.pi * 1980 * (i / SR)))
        * math.exp(-7 * i / SR) * min(1.0, i / (SR * 0.004)) * 0.32 for i in range(n)])
    n, ph, pop = int(SR * 0.12), 0.0, []
    for i in range(n):
        t = i / SR
        ph += 2 * math.pi * (900 - 5500 * t) / SR
        pop.append(math.sin(ph) * math.exp(-30 * t) * min(1.0, t / 0.002) * 0.4)
    _write_wav(paths["pop"], pop)
    n = int(SR * 0.45)
    _write_wav(paths["thud"], [
        ((0.8 * math.sin(2 * math.pi * 62 * (i / SR)) + 0.4 * math.sin(2 * math.pi * 124 * (i / SR)))
         * math.exp(-9 * i / SR) * 0.85 + rnd.uniform(-1, 1) * math.exp(-120 * i / SR) * 0.3)
        * min(1.0, i / (SR * 0.002)) for i in range(n)])
    return paths


# ---- assembly ----
def _run(cmd):
    subprocess.run(cmd, check=True)


def _narration(audios, durs, tmp):
    parts = []
    for i, (a, d) in enumerate(zip(audios, durs)):
        out = os.path.join(tmp, f"n{i:02d}.wav")
        src = ["-i", a] if a else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        _run(["ffmpeg", "-y", "-loglevel", "error", *src,
              "-af", "aresample=44100,aformat=sample_fmts=s16:channel_layouts=stereo,apad",
              "-t", f"{d:.4f}", "-c:a", "pcm_s16le", out])
        parts.append(out)
    lst = os.path.join(tmp, "narr.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
    out = os.path.join(tmp, "narration.wav")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
          "-c", "copy", out])
    return out


def _mix(narration, sfx, tmp):
    paths = make_sfx(tmp)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", narration]
    chains, labels = [], []
    for k, (t, kind) in enumerate(sfx):
        cmd += ["-i", paths[kind]]
        chains.append(f"[{k + 1}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                      f"adelay=delays={max(0, int(t * 1000))}:all=1[s{k}]")
        labels.append(f"[s{k}]")
    tracks = glob.glob(os.path.join(MUSIC_DIR, "*.mp3"))
    n = len(labels) + 1
    if tracks:
        cmd += ["-stream_loop", "-1", "-i", random.choice(tracks)]
        chains.append(f"[{n}:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=0.10[m]")
        labels.append("[m]")
    chains.append(f"[0:a]{''.join(labels)}amix=inputs={len(labels) + 1}:duration=first:normalize=0[a]")
    out = os.path.join(tmp, "audio.wav")
    _run(cmd + ["-filter_complex", ";".join(chains), "-map", "[a]", "-c:a", "pcm_s16le", out])
    return out


def build(data, audios, durations, outdir):
    """Same interface as before: returns the path of short.mp4."""
    tmp = os.path.join(outdir, "tmp")
    os.makedirs(tmp, exist_ok=True)
    # snap every scene to whole frames so picture and sound stay in sync
    durs = [max(1, round(d * FPS)) / FPS for d in durations]
    r = Renderer(data, durs)
    r.cover().save(os.path.join(outdir, "cover.png"))

    video = os.path.join(tmp, "video.mp4")
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "20", "-pix_fmt", "yuv420p", video], stdin=subprocess.PIPE)
    try:
        for frame in r.frames():
            proc.stdin.write(frame.tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed while encoding the video")

    audio = _mix(_narration(audios, durs, tmp), r.sfx, tmp)
    final = os.path.join(outdir, "short.mp4")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", audio,
          "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
          "-shortest", "-movflags", "+faststart", final])
    return final
