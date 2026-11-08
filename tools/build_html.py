"""Build the branded HTML newsletter from .tmp/<slug>/content.json + images.

Usage:
  python tools/build_html.py --slug <slug>            -> newsletter.html (cid: image refs, for Gmail)
  python tools/build_html.py --slug <slug> --preview  -> preview.html (local image paths, open in browser)
"""
import argparse
import json
import shutil
from datetime import date
from html import escape
from html.parser import HTMLParser

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from _env import BRAND, ROOT, existing_run

FONT = "'Plus Jakarta Sans','Segoe UI',Arial,Helvetica,sans-serif"
# Allowed tags -> inline style (email clients ignore <style> for most things)
STYLES = {
    "p": f"margin:0 0 14px 0;font-family:{FONT};font-size:15px;line-height:24px;color:#BFD7EA;",
    "ul": f"margin:0 0 14px 0;padding-left:20px;font-family:{FONT};font-size:15px;line-height:24px;color:#BFD7EA;",
    "ol": f"margin:0 0 14px 0;padding-left:20px;font-family:{FONT};font-size:15px;line-height:24px;color:#BFD7EA;",
    "li": "margin:0 0 6px 0;",
    "strong": "color:#FFFFFF;", "b": "color:#FFFFFF;",
    "em": "", "i": "", "br": "",
    "a": "color:#70E4EF;text-decoration:underline;",
}
IMAGES = {"logo": "logo.png", "hero": "hero.jpg", "stats": "stats.png", "chart": "chart.png"}
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


class Sanitizer(HTMLParser):
    """Keep only allowlisted tags, drop attributes except a[href], add inline styles."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0  # depth inside <script>/<style>, whose text must be dropped
        self.dropped_a = 0  # <a> tags removed for unsafe href; drop their </a> too

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
            return
        if tag not in STYLES:
            return
        extra = ""
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if not href.startswith(("http://", "https://")):
                self.dropped_a += 1
                return
            extra = f' href="{escape(href)}"'
        style = f' style="{STYLES[tag]}"' if STYLES[tag] else ""
        self.out.append(f"<{tag}{extra}{style}>" if tag != "br" else "<br>")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag == "a" and self.dropped_a:
            self.dropped_a -= 1
        elif tag in STYLES and tag != "br":
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(escape(data))


def sanitize(html: str) -> str:
    s = Sanitizer()
    s.feed(html or "")
    s.close()
    result = "".join(s.out).strip()
    if result and not result.startswith(("<p", "<ul", "<ol")):
        result = f'<p style="{STYLES["p"]}">{result}</p>'
    return result


def build(slug: str, preview: bool = False):
    d = existing_run(slug)
    c = json.loads((d / "content.json").read_text(encoding="utf-8"))
    logo = BRAND / "logo.png"
    if not logo.exists():
        raise SystemExit("brand/logo.png missing — run tools/render_logo.py first")
    shutil.copy(logo, d / "logo.png")

    img = {k: (fn if preview else f"cid:{k}") for k, fn in IMAGES.items() if (d / fn).exists()}
    sections = [{"heading": s["heading"], "body_html": Markup(sanitize(s["body_html"]))} for s in c["sections"]]
    today = date.today()

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]))
    html = env.get_template("newsletter.html").render(
        c=c, sections=sections, img=img, date=f"{MONTHS[today.month - 1]} {today.year}")
    out = d / ("preview.html" if preview else "newsletter.html")
    out.write_text(html, encoding="utf-8")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--slug", required=True)
    p.add_argument("--preview", action="store_true")
    a = p.parse_args()
    print(f"html -> {build(a.slug, a.preview)}")


if __name__ == "__main__":
    main()
