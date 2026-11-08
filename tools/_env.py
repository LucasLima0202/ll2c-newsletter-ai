"""Shared helpers for tools: load .env and resolve project paths."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / ".tmp"
TMP.mkdir(exist_ok=True)

load_dotenv(ROOT / ".env")

# Windows consoles default to cp1252; keep accents and dashes readable
import sys  # noqa: E402
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


BRAND = ROOT / "brand"  # logos (versioned); fonts are downloaded here at runtime
BRAND.mkdir(exist_ok=True)

# LL2C brand palette
COLORS = {
    "navy": "#031B2F",       # Azul Principal
    "navy2": "#0B3954",      # Azul Secundario
    "light": "#BFD7EA",      # Azul Claro
    "white": "#FFFFFF",
    "black": "#1A1A1A",
    "alert": "#FF6663",
    "highlight": "#E0FF4F",  # Destaque
    "cyan": "#70E4EF",       # Agua Eletrica
}


def slugify(text: str) -> str:
    import re
    import unicodedata
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "newsletter"


def run_dir(slug: str) -> Path:
    d = TMP / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def require_env(name: str) -> str:
    """Return an env var or exit with a clear message if it's missing."""
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required env var {name!r}. Add it to .env")
    return value
