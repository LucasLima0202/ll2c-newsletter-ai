"""Run the full newsletter pipeline for a topic.

Usage:
  python tools/run_newsletter.py --topic "Agentes de IA em pequenas empresas"          # stops at preview
  python tools/run_newsletter.py --topic "..." --send                                 # also sends via Gmail
  python tools/run_newsletter.py --slug <existing-slug> --from-step render --send     # resume
Steps: research -> write -> render -> hero -> html -> send
"""
import argparse
import subprocess
import sys
from pathlib import Path

from _env import BRAND, TMP, slugify

TOOLS = Path(__file__).resolve().parent
STEPS = ["research", "write", "render", "hero", "html", "send"]


def run(script: str, *args, required: bool = True) -> bool:
    cmd = [sys.executable, str(TOOLS / script), *args]
    print(f"\n>>> {script} {' '.join(args)}")
    ok = subprocess.run(cmd).returncode == 0
    if not ok and required:
        raise SystemExit(f"{script} failed — fix and resume with --from-step")
    return ok


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--topic")
    p.add_argument("--slug")
    p.add_argument("--from-step", choices=STEPS, default="research")
    p.add_argument("--send", action="store_true")
    p.add_argument("--to")
    a = p.parse_args()
    if not (a.topic or a.slug):
        raise SystemExit("pass --topic or --slug")
    slug = a.slug or slugify(a.topic)
    todo = STEPS[STEPS.index(a.from_step):]

    if not (BRAND / "logo.png").exists():
        run("render_logo.py")
    if "research" in todo:
        if not a.topic:
            raise SystemExit("--topic required for the research step")
        run("research_topic.py", "--topic", a.topic, "--slug", slug)
    if "write" in todo:
        run("write_newsletter.py", "--slug", slug)
    if "render" in todo:
        run("render_infographics.py", "--slug", slug)
    if "hero" in todo:
        if not run("generate_hero_image.py", "--slug", slug, required=False):
            print("!! hero image failed — continuing without it")
    if "html" in todo:
        run("build_html.py", "--slug", slug, "--preview")
        run("build_html.py", "--slug", slug)
        print(f"\nPreview: {TMP / slug / 'preview.html'}")
    if "send" in todo:
        extra = ["--to", a.to] if a.to else []
        run("send_gmail.py", "--slug", slug, *extra, *([] if a.send else ["--dry-run"]))


if __name__ == "__main__":
    main()
