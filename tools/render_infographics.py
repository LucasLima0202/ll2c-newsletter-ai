"""Render brand-styled infographic panels from .tmp/<slug>/content.json.

Outputs (1200px wide, shown at 600px in email for retina sharpness):
  stats.png  — "BY THE NUMBERS" panel: numbered stat cards, progress rings for %, sources
  chart.png  — "ANALYSIS" panel: gradient bar chart with axis, gridlines and source
Drawn at 2x and downsampled for smooth edges. Style follows brand/Guia de Marca LL2C.
Usage: python tools/render_infographics.py --slug <slug>
"""
import argparse
import json
import math
import re

import requests
from PIL import Image, ImageDraw, ImageFont

from _env import BRAND, COLORS, run_dir

FONT_DIR = BRAND / "fonts"
FONT_WEIGHTS = {"bold": 800, "semibold": 700, "regular": 500}
FONT_URL = "https://cdn.jsdelivr.net/fontsource/fonts/plus-jakarta-sans@latest/latin-{w}-normal.ttf"
SAFE_EXTRA = set("–—‘’“”•€…")
W, SS, PAD = 1200, 2, 56  # logical width, supersample factor, outer padding

NAVY, NAVY2, LIGHT = COLORS["navy"], COLORS["navy2"], COLORS["light"]
WHITE, CYAN, LIME = COLORS["white"], COLORS["cyan"], COLORS["highlight"]


def rgb(h: str, a: int = 255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


# ---------- fonts ----------
_fonts = {}


def _font_file(weight: str):
    FONT_DIR.mkdir(exist_ok=True)
    path = FONT_DIR / f"PlusJakartaSans-{weight}.ttf"
    if not path.exists():
        try:
            r = requests.get(FONT_URL.format(w=FONT_WEIGHTS[weight]), timeout=30)
            r.raise_for_status()
            path.write_bytes(r.content)
        except Exception as e:
            print(f"font download failed ({e}); using DejaVu fallback")
            return None
    return path


def needs_fallback(text: str) -> bool:
    """Latin font subset lacks symbols like ≈ →; use DejaVu for such text."""
    return any(ord(ch) > 0x17F and ch not in SAFE_EXTRA for ch in text)


def font(weight: str, size: float, text: str = ""):
    px = int(size * SS)
    fb = needs_fallback(text)
    key = (weight, px, fb)
    if key not in _fonts:
        path = None if fb else _font_file(weight)
        if path is None:
            import matplotlib
            name = "DejaVuSans.ttf" if weight == "regular" else "DejaVuSans-Bold.ttf"
            path = f"{matplotlib.get_data_path()}/fonts/ttf/{name}"
        _fonts[key] = ImageFont.truetype(str(path), px)
    return _fonts[key]


_measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))


def text_w(txt: str, weight: str, size: float) -> float:
    return _measure.textlength(txt, font=font(weight, size, txt)) / SS


def wrap(txt: str, weight: str, size: float, max_w: float, max_lines: int = 3) -> list:
    words, lines, cur = str(txt).split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if text_w(trial, weight, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;") + "…"
    return lines


def fmt_num(v: float) -> str:
    return f"{v:g}"


# ---------- canvas ----------
class Canvas:
    def __init__(self, h: int):
        self.h = h
        self.img = Image.new("RGBA", (W * SS, h * SS), rgb(NAVY))

    @staticmethod
    def s(v: float) -> int:
        return int(round(v * SS))

    def _layer(self, fn):
        ov = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        fn(ImageDraw.Draw(ov))
        self.img.alpha_composite(ov)

    def background(self, motif_top: float = 0.16):
        """motif_top: fraction of height where the brand line motif starts (keeps it clear of data)."""
        w, h = self.img.size
        grad = Image.linear_gradient("L").resize((w, h))
        self.img = Image.composite(Image.new("RGBA", (w, h), rgb("#06263F")),
                                   Image.new("RGBA", (w, h), rgb(NAVY)), grad)
        # brand "graphic elements": angular circuit lines, bottom-right
        mid = motif_top + (1 - motif_top) * 0.48
        base = [(w * 0.52, h + 20), (w * 0.70, h * mid), (w * 0.85, h * mid), (w + 20, h * motif_top)]
        shift = [(x + self.s(30), y + self.s(10)) for x, y in base]

        def draw(d):
            d.line(base, fill=rgb(NAVY2, 150), width=self.s(22), joint="curve")
            d.line(shift, fill=rgb(CYAN, 80), width=self.s(2), joint="curve")
        self._layer(draw)

    def text(self, x, y, txt, weight, size, fill, tracking=0.0, anchor="la"):
        f = font(weight, size, txt)

        def draw(d):
            if not tracking:
                d.text((self.s(x), self.s(y)), txt, font=f, fill=fill, anchor=anchor)
                return
            cx = self.s(x)
            for ch in txt:
                d.text((cx, self.s(y)), ch, font=f, fill=fill)
                cx += d.textlength(ch, font=f) + self.s(tracking)
        self._layer(draw)

    def rrect(self, box, r, fill=None, outline=None, width=1.0):
        b = [self.s(v) for v in box]
        self._layer(lambda d: d.rounded_rectangle(b, radius=self.s(r), fill=fill,
                                                  outline=outline, width=self.s(width)))

    def line(self, pts, fill, width=1.0, dash=None):
        p = [(self.s(x), self.s(y)) for x, y in pts]

        def draw(d):
            if not dash:
                d.line(p, fill=fill, width=self.s(width))
                return
            (x0, y0), (x1, y1) = p
            length = math.hypot(x1 - x0, y1 - y0)
            on, off = self.s(dash[0]), self.s(dash[1])
            t = 0.0
            while t < length:
                t2 = min(t + on, length)
                d.line([(x0 + (x1 - x0) * t / length, y0 + (y1 - y0) * t / length),
                        (x0 + (x1 - x0) * t2 / length, y0 + (y1 - y0) * t2 / length)],
                       fill=fill, width=self.s(width))
                t += on + off
        self._layer(draw)

    def gradient_rrect(self, box, r, c1, c2):
        x0, y0, x1, y1 = [self.s(v) for v in box]
        w, h = max(1, x1 - x0), max(1, y1 - y0)
        mask_grad = Image.linear_gradient("L").rotate(90).resize((w, h))  # dark left -> light right
        bar = Image.composite(Image.new("RGBA", (w, h), rgb(c2)), Image.new("RGBA", (w, h), rgb(c1)), mask_grad)
        shape = Image.new("L", (w, h), 0)
        ImageDraw.Draw(shape).rounded_rectangle([0, 0, w - 1, h - 1], radius=min(self.s(r), h // 2), fill=255)
        self.img.paste(bar, (x0, y0), shape)

    def ring(self, cx, cy, r, pct, width=9.0):
        b = [self.s(cx - r), self.s(cy - r), self.s(cx + r), self.s(cy + r)]

        def draw(d):
            d.ellipse(b, outline=rgb(WHITE, 28), width=self.s(width))
            d.arc(b, -90, -90 + 360 * min(pct, 100) / 100, fill=rgb(CYAN), width=self.s(width))
        self._layer(draw)
        self.text(cx, cy, f"{fmt_num(round(pct))}%", "bold", 15, rgb(WHITE), anchor="mm")

    def logo(self, right_x, top_y, height=34):
        p = BRAND / "logo.png"
        if not p.exists():
            return
        lg = Image.open(p).convert("RGBA")
        h = self.s(height)
        lg = lg.resize((round(lg.width * h / lg.height), h), Image.LANCZOS)
        self.img.alpha_composite(lg, dest=(self.s(right_x) - lg.width, self.s(top_y)))

    def save(self, out):
        self.img.convert("RGB").resize((W, self.h), Image.LANCZOS).save(out, optimize=True)


# ---------- shared header ----------
EYEBROW, TITLE, TITLE_LH = 17, 36, 46


def header_height(title_lines: int) -> int:
    return 34 + (title_lines * TITLE_LH + 10 if title_lines else 0) + 22 + 32


def draw_header(c: Canvas, eyebrow: str, title_lines=None) -> float:
    y = PAD
    c.rrect((PAD, y + 4, PAD + 10, y + 14), 2, fill=rgb(LIME))
    c.text(PAD + 22, y, eyebrow, "semibold", EYEBROW, rgb(CYAN), tracking=3.5)
    c.logo(W - PAD, y - 6, height=30)
    y += 34
    for line in title_lines or []:
        c.text(PAD, y, line, "bold", TITLE, rgb(WHITE))
        y += TITLE_LH
    if title_lines:
        y += 10
    y += 22
    c.line([(PAD, y), (W - PAD, y)], fill=rgb(CYAN, 45), width=1.5)
    return y + 32


# ---------- stats panel ----------
def percent_of(value: str):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*%", value)
    if not m:
        return None
    v = float(m.group(1).replace(",", "."))
    return v if 0 < v <= 100 else None


def render_stats(stats: list, out):
    n = len(stats)
    cols = 1 if n == 1 else 2 if n in (2, 4) else 3
    rows = math.ceil(n / cols)
    gap, card_h = 24, 300
    card_w = (W - 2 * PAD - (cols - 1) * gap) / cols
    H = PAD + header_height(0) + rows * card_h + (rows - 1) * gap + PAD
    c = Canvas(H)
    c.background()
    top = draw_header(c, "BY THE NUMBERS")
    val_size = 74 if cols <= 2 else 60

    for i, s in enumerate(stats):
        r, col = divmod(i, cols)
        x, y = PAD + col * (card_w + gap), top + r * (card_h + gap)
        c.rrect((x, y, x + card_w, y + card_h), 22, fill=rgb(NAVY2, 225), outline=rgb(CYAN, 55), width=1.5)
        c.rrect((x + 1, y + 26, x + 5, y + 62), 2, fill=rgb(LIME))  # left accent tab
        c.text(x + 30, y + 30, f"{i + 1:02d}", "semibold", 17, rgb(LIME), tracking=2)

        value, label = str(s["value"]), str(s["label"])
        pct = percent_of(value)
        ring_space = 0
        if pct is not None:
            ring_r = 34
            c.ring(x + card_w - 30 - ring_r, y + 30 + ring_r, ring_r, pct)
            ring_space = 2 * ring_r + 24
        size = val_size
        while text_w(value, "bold", size) > card_w - 60 - ring_space and size > 32:
            size -= 2
        c.text(x + 30, y + 64, value, "bold", size, rgb(WHITE))

        ly = y + 64 + size * 1.12 + 10
        for line in wrap(label, "regular", 22, card_w - 60, max_lines=3):
            c.text(x + 30, ly, line, "regular", 22, rgb(LIGHT))
            ly += 31
        src = s.get("source")
        if src:
            c.line([(x + 30, y + card_h - 52), (x + card_w - 30, y + card_h - 52)], fill=rgb(WHITE, 22), width=1)
            src_txt = wrap(f"Source: {src}", "regular", 16, card_w - 60, max_lines=1)[0]
            c.text(x + 30, y + card_h - 38, src_txt, "regular", 16, rgb(LIGHT, 150))
    c.save(out)


# ---------- chart panel ----------
def nice_ticks(vmax: float, target: int = 4) -> list:
    raw = vmax / target if vmax > 0 else 1
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    top = math.ceil(vmax / step) * step
    return [round(i * step, 10) for i in range(int(round(top / step)) + 1)]


def render_chart(chart: dict, out):
    labels, values = chart["labels"], [float(v) for v in chart["values"]]
    unit = chart.get("unit") or ""
    sep = " " if unit[:1].isalpha() else ""
    fmt = lambda v: f"{fmt_num(v)}{sep}{unit}"
    title_lines = wrap(chart.get("title", ""), "bold", TITLE, W - 2 * PAD - 80, max_lines=2)
    source = chart.get("source")

    row_h, label_h, bar_h = 104, 36, 40
    axis_h, foot_h = 44, (46 if source else 0)
    H = PAD + header_height(len(title_lines)) + len(labels) * row_h + axis_h + foot_h + PAD - 20
    c = Canvas(H)
    plot_end = PAD + header_height(len(title_lines)) + len(labels) * row_h + axis_h
    c.background(motif_top=min(0.9, (plot_end - 8) / H))
    y0 = draw_header(c, "ANALYSIS", title_lines)

    value_w = max(text_w(fmt(v), "bold", 26) for v in values)
    x0, x1 = PAD, W - PAD - value_w - 22
    ticks = nice_ticks(max(values))
    vmax = ticks[-1] or 1
    plot_bottom = y0 + len(labels) * row_h - 20
    for t in ticks:  # gridlines + axis labels
        gx = x0 + (x1 - x0) * t / vmax
        c.line([(gx, y0 + label_h - 6), (gx, plot_bottom)], fill=rgb(LIGHT, 40), width=1, dash=(5, 6))
        c.text(gx, plot_bottom + 12, fmt_num(t), "regular", 16, rgb(LIGHT, 150), anchor="ma")

    top_i = values.index(max(values))
    for i, (lab, v) in enumerate(zip(labels, values)):
        ry = y0 + i * row_h
        lab_txt = wrap(lab, "semibold", 21, x1 - x0, max_lines=1)[0]
        c.text(x0, ry, lab_txt, "semibold", 21, rgb(WHITE if i == top_i else LIGHT))
        by = ry + label_h
        c.rrect((x0, by, x1, by + bar_h), 10, fill=rgb(WHITE, 14))
        bw = max(bar_h * 0.5, (x1 - x0) * v / vmax)
        c1, c2 = (CYAN, LIME) if i == top_i else ("#1F7A93", CYAN)
        c.gradient_rrect((x0, by, x0 + bw, by + bar_h), 10, c1, c2)
        c.text(x1 + 22, by + bar_h / 2, fmt(v), "bold", 26, rgb(LIME if i == top_i else WHITE), anchor="lm")

    if source:
        c.text(PAD, H - PAD - 6, f"Source: {source}", "regular", 16, rgb(LIGHT, 150), anchor="ls")
    c.save(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--slug", required=True)
    a = p.parse_args()
    d = run_dir(a.slug)
    c = json.loads((d / "content.json").read_text(encoding="utf-8"))
    if c.get("key_stats"):
        render_stats(c["key_stats"][:4], d / "stats.png")
        print(f"stats -> {d / 'stats.png'}")
    (d / "chart.png").unlink(missing_ok=True)
    if c.get("chart"):
        render_chart(c["chart"], d / "chart.png")
        print(f"chart -> {d / 'chart.png'}")
    else:
        print("no chart data — skipped chart.png")


if __name__ == "__main__":
    main()
