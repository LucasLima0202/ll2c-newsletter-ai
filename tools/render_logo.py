"""Render brand/logo-favicon.svg to brand/logo.png (Gmail does not display SVG).

The SVG is two straight-line polygons, so we draw them with Pillow (no cairo needed).
Usage: python tools/render_logo.py [--height 96]
"""
import argparse

from PIL import Image, ImageDraw

from _env import BRAND

VIEWBOX = (139, 156)
POLYGONS = [
    [(119.658, 38.2383), (119.237, 146.463), (99.0728, 146.388), (99.4261, 55.5952),
     (52.1294, 55.4186), (52.1972, 37.9863)],
    [(19.9404, 119.683), (19.9404, 11.457), (40.1047, 11.457), (40.1047, 102.251),
     (87.4018, 102.251), (87.4018, 119.683)],
]


def render(height: int = 96, color: str = "#FFFFFF") -> Image.Image:
    ss = 4  # supersample for smooth edges
    scale = height * ss / VIEWBOX[1]
    w, h = round(VIEWBOX[0] * scale), round(VIEWBOX[1] * scale)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for poly in POLYGONS:
        draw.polygon([(x * scale, y * scale) for x, y in poly], fill=color)
    return img.resize((w // ss, h // ss), Image.LANCZOS)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--height", type=int, default=96)
    a = p.parse_args()
    out = BRAND / "logo.png"
    render(a.height).save(out)
    print(f"logo -> {out}")


if __name__ == "__main__":
    main()
