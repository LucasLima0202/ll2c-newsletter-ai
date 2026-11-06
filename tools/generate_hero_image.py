"""Generate a hero illustration with Cloudflare Workers AI (FLUX-1-schnell, free tier).

Free tier: 10,000 neurons/day (~43 neurons per 4-step image).
Usage: python tools/generate_hero_image.py --slug <slug>
Output: .tmp/<slug>/hero.jpg (1200x630). Exits non-zero on failure — the pipeline continues without a hero.
"""
import argparse
import base64
import io
import json

import requests
from PIL import Image

from _env import require_env, run_dir

MODEL = "@cf/black-forest-labs/flux-1-schnell"
STYLE = (", minimalist futuristic tech illustration, deep dark navy blue background (#031B2F), "
         "glowing electric cyan (#70E4EF) and subtle lime (#E0FF4F) accents, clean geometric shapes, "
         "soft gradients, editorial, high detail, no text, no letters, no words, no logos")


def generate(prompt: str) -> Image.Image:
    account = require_env("CLOUDFLARE_ACCOUNT_ID")
    token = require_env("CLOUDFLARE_API_TOKEN")
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{MODEL}"
    r = requests.post(url, headers={"Authorization": f"Bearer {token}"},
                      json={"prompt": prompt + STYLE, "steps": 4}, timeout=120)
    if r.status_code != 200:
        raise SystemExit(f"Cloudflare error {r.status_code}: {r.text[:500]}")
    b64 = r.json()["result"]["image"]
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")


def crop_banner(img: Image.Image, w=1200, h=630) -> Image.Image:
    scale = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--slug", required=True)
    a = p.parse_args()
    d = run_dir(a.slug)
    c = json.loads((d / "content.json").read_text(encoding="utf-8"))
    img = crop_banner(generate(c["hero_prompt"]))
    out = d / "hero.jpg"
    img.save(out, quality=88)
    print(f"hero -> {out}")


if __name__ == "__main__":
    main()
