"""Draws each scene as a 1080x1920 frame and stitches them into a Short."""
import glob
import os
import random
import subprocess

from PIL import Image, ImageDraw, ImageFont, features

from .text import clean, wrap_phrases, wrap_words

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "assets", "fonts")
MUSIC_DIR = os.path.join(ROOT, "assets", "music")

W, H = 1080, 1920
HEAD = "ChakraPetch-Bold.ttf"
REG = "IBMPlexSansThai-Regular.ttf"
SEMI = "IBMPlexSansThai-SemiBold.ttf"
BOLD = "IBMPlexSansThai-Bold.ttf"

C = {
    "bg": (255, 199, 0),        # hazard yellow: reads "warning" instantly
    "ink": (0, 0, 0),
    "paper": (255, 255, 255),
    "muted": (128, 128, 128),
    "stamp": (214, 36, 28),
    "sms_head": (246, 246, 246),
    "sms_them": (233, 233, 235),
    "sms_me": (10, 132, 255),
    "line_bg": (140, 166, 205),
    "line_head": (38, 46, 62),
    "line_me": (122, 214, 90),
}

PHONE = (100, 420, 980, 1500)
SUB_TOP = 1548
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


# ---------- pieces ----------

def draw_hook(draw, hook):
    f, lines = fit(draw, hook, HEAD, 940, range(104, 58, -4), 2)
    block_h = lh(f, 0.92) * len(lines)
    top = 110 + (290 - block_h) // 2
    text_block(draw, lines, f, W // 2, top, C["ink"], spacing=0.92)


def draw_phone(img, draw, app, sender, messages):
    x0, y0, x1, y1 = PHONE
    draw.rounded_rectangle(PHONE, radius=72, fill=C["ink"])
    sx0, sy0, sx1, sy1 = x0 + 16, y0 + 16, x1 - 16, y1 - 16
    screen_bg = C["paper"] if app == "sms" else C["line_bg"]
    draw.rounded_rectangle((sx0, sy0, sx1, sy1), radius=58, fill=screen_bg)

    # header
    head_h = 132
    head_col = C["sms_head"] if app == "sms" else C["line_head"]
    name_col = C["ink"] if app == "sms" else C["paper"]
    draw.rounded_rectangle((sx0, sy0, sx1, sy0 + head_h + 58), radius=58, fill=head_col)
    draw.rectangle((sx0, sy0 + head_h - 10, sx1, sy0 + head_h), fill=head_col)
    draw.rectangle((sx0, sy0 + head_h, sx1, sy0 + head_h + 58), fill=screen_bg)
    name_font, name_lines = fit(draw, sender, SEMI, sx1 - sx0 - 120, range(42, 30, -2), 1)
    draw.text(((sx0 + sx1) // 2, sy0 + head_h // 2 + 8), name_lines[0],
              font=name_font, fill=name_col, anchor="mm")
    draw.text((sx0 + 44, sy0 + head_h // 2 + 8), "<", font=F(SEMI, 44),
              fill=C["sms_me"] if app == "sms" else C["paper"], anchor="mm")
    if app == "sms":
        draw.line((sx0, sy0 + head_h, sx1, sy0 + head_h), fill=(220, 220, 220), width=2)

    # bubbles
    cx0, cy0, cx1, cy1 = sx0 + 28, sy0 + head_h + 26, sx1 - 28, sy1 - 34
    font = F(REG, 44)
    step = lh(font, 0.86)
    padx, pady, gap = 28, 18, 20
    max_text_w = int((cx1 - cx0) * 0.74) - 2 * padx

    laid = []
    for m in messages:
        lines = wrap_phrases(m["text"], font, max_text_w, draw)[:9]
        w = max(draw.textlength(l, font=font) for l in lines) + 2 * padx
        h = step * len(lines) + 2 * pady
        laid.append((m, lines, int(w), int(h)))

    # keep the newest messages that fit, like a scrolled chat
    avail = cy1 - cy0
    total, keep = 0, []
    for item in reversed(laid):
        need = item[3] + (gap if keep else 0)
        if total + need > avail and keep:
            break
        total += need
        keep.insert(0, item)
    scrolled = len(keep) < len(laid)
    y = cy1 - total if scrolled else cy0

    for m, lines, w, h in keep:
        mine = m.get("from") == "me"
        if app == "sms":
            fill = C["sms_me"] if mine else C["sms_them"]
            tcol = C["paper"] if mine else C["ink"]
        else:
            fill = C["line_me"] if mine else C["paper"]
            tcol = C["ink"]
        bx0 = cx1 - w if mine else cx0
        draw.rounded_rectangle((bx0, y, bx0 + w, y + h), radius=34, fill=fill)
        text_block(draw, lines, font, 0, y + pady, tcol, spacing=0.86,
                   align="left", left=bx0 + padx)
        y += h + gap


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


def draw_subtitle(draw, text):
    f, lines = fit(draw, text, SEMI, 880, range(58, 42, -2), 3)
    step = lh(f, 0.96)
    box_h = step * len(lines) + 56
    draw.rounded_rectangle((50, SUB_TOP, W - 50, SUB_TOP + box_h), radius=34, fill=C["ink"])
    text_block(draw, lines, f, W // 2, SUB_TOP + 28, C["paper"], spacing=0.96)


def draw_end_card(draw, tip):
    x0, y0, x1, y1 = PHONE
    draw.rounded_rectangle(PHONE, radius=72, fill=C["ink"])
    y = y0 + 84
    y = text_block(draw, ["กฎข้อเดียวที่ต้องจำ"], F(BOLD, 46), W // 2, y, C["stamp"])
    f, lines = fit(draw, tip, BOLD, x1 - x0 - 140, range(76, 50, -2), 4)
    y = text_block(draw, lines, f, W // 2, y + 30, C["paper"], spacing=0.95)
    y = max(y + 60, y1 - 470)
    draw.line((x0 + 90, y, x1 - 90, y), fill=(70, 70, 70), width=3)
    y = text_block(draw, ["สงสัยว่าโดนหลอก"], F(SEMI, 48), W // 2, y + 44, C["paper"])
    y = text_block(draw, ["โทร 1441"], F(HEAD, 150), W // 2, y + 4, C["bg"], spacing=0.85)
    text_block(draw, ["ศูนย์ AOC ตลอด 24 ชั่วโมง"], F(REG, 40), W // 2, y + 6, (190, 190, 190))


# ---------- frames ----------

def scene_frame(data, upto, subtitle, stamp):
    img = Image.new("RGB", (W, H), C["bg"])
    d = ImageDraw.Draw(img)
    draw_hook(d, data["hook"])
    msgs = [s["message"] for s in data["scenes"][:upto + 1] if s.get("message")]
    draw_phone(img, d, data["app"], data["sender"], msgs)
    if stamp:
        x0, y0, x1, y1 = PHONE
        veil = Image.new("RGBA", (x1 - x0 - 32, y1 - y0 - 32), (255, 255, 255, 150))
        mask = Image.new("L", veil.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0) + veil.size, radius=58, fill=150)
        img.paste(veil, (x0 + 16, y0 + 16), mask)
        st = stamp_image()
        px = (PHONE[0] + PHONE[2]) // 2 - st.width // 2
        py = (PHONE[1] + PHONE[3]) // 2 - st.height // 2 + 60
        img.paste(st, (px, py), st)
    draw_subtitle(d, subtitle)
    return img


def end_frame(data):
    img = Image.new("RGB", (W, H), C["bg"])
    d = ImageDraw.Draw(img)
    draw_hook(d, data["hook"])
    draw_end_card(d, data["tip"])
    draw_subtitle(d, data["end_narration"])
    return img


def all_frames(data):
    frames, stamped = [], False
    for i, s in enumerate(data["scenes"]):
        stamped = stamped or bool(s.get("stamp"))
        frames.append(scene_frame(data, i, clean(s["narration"]), stamped))
    frames.append(end_frame(data))
    return frames


# ---------- video ----------

def _run(cmd):
    subprocess.run(cmd, check=True)


def _segment(png, audio, dur, out):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", png]
    cmd += ["-i", audio] if audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    cmd += ["-filter_complex", "[1:a]aresample=44100,aformat=channel_layouts=stereo,apad[a]",
            "-map", "0:v", "-map", "[a]", "-t", f"{dur:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
            "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "160k", out]
    _run(cmd)


def build(data, audios, durations, outdir):
    check_thai_support()
    tmp = os.path.join(outdir, "tmp")
    os.makedirs(tmp, exist_ok=True)
    frames = all_frames(data)
    frames[0].save(os.path.join(outdir, "cover.png"))

    segs = []
    for i, (fr, au, du) in enumerate(zip(frames, audios, durations)):
        png = os.path.join(tmp, f"f{i:02d}.png")
        fr.save(png)
        seg = os.path.join(tmp, f"s{i:02d}.mp4")
        _segment(png, au, du, seg)
        segs.append(seg)

    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.abspath(s)}'\n" for s in segs)
    joined = os.path.join(tmp, "joined.mp4")
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
          "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", joined])

    final = os.path.join(outdir, "short.mp4")
    tracks = glob.glob(os.path.join(MUSIC_DIR, "*.mp3"))
    if tracks:
        _run(["ffmpeg", "-y", "-loglevel", "error", "-i", joined,
              "-stream_loop", "-1", "-i", random.choice(tracks),
              "-filter_complex",
              "[1:a]volume=0.10[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
              "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
              "-movflags", "+faststart", final])
    else:
        os.replace(joined, final)
    return final
