"""Send .tmp/<slug>/newsletter.html via the Gmail API with inline (CID) images.

Setup: credentials.json (Desktop OAuth client) in project root. First run opens a browser
to authorize and saves token.json.
Usage:
  python tools/send_gmail.py --slug <slug> --dry-run       # build message.eml, don't send
  python tools/send_gmail.py --slug <slug> [--to a@b.com]  # send
"""
import argparse
import base64
import json
import os
import re
from email.message import EmailMessage
from email.utils import formataddr

from _env import ROOT, existing_run

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
IMAGES = {"logo": ("logo.png", "png"), "hero": ("hero.jpg", "jpeg"),
          "stats": ("stats.png", "png"), "chart": ("chart.png", "png")}


def plain_text(c: dict) -> str:
    strip = lambda h: re.sub(r"<[^>]+>", "", h or "")
    parts = [c["title"], "", c["intro"], ""]
    for s in c.get("key_stats", []):
        parts.append(f"• {s['value']} — {s['label']}")
    for s in c["sections"]:
        parts += ["", s["heading"].upper(), strip(s["body_html"])]
    if c.get("sources"):
        parts += ["", "SOURCES"] + [f"- {s.get('title', '')}: {s['url']}" for s in c["sources"]]
    return "\n".join(parts)


def build_message(slug: str, to: str, sender: str) -> EmailMessage:
    d = existing_run(slug)
    c = json.loads((d / "content.json").read_text(encoding="utf-8"))
    html = (d / "newsletter.html").read_text(encoding="utf-8")
    msg = EmailMessage()
    msg["Subject"] = c["subject"]
    msg["From"] = formataddr(("LL2C Newsletter", sender))
    msg["To"] = to
    msg.set_content(plain_text(c))
    msg.add_alternative(html, subtype="html")
    html_part = msg.get_payload()[1]
    for cid, (fn, subtype) in IMAGES.items():
        if f"cid:{cid}" in html and (d / fn).exists():
            html_part.add_related((d / fn).read_bytes(), maintype="image", subtype=subtype,
                                  cid=f"<{cid}>", filename=fn, disposition="inline")
    return msg


def gmail_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    token, creds_file = ROOT / "token.json", ROOT / "credentials.json"
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_file.exists():
                raise SystemExit("credentials.json missing — see workflows/newsletter.md setup")
            # Desktop clients accept any localhost port. "Web application" clients need this exact
            # URI in Authorized redirect URIs: http://localhost:8080/
            is_web = "web" in json.loads(creds_file.read_text(encoding="utf-8"))
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
            creds = flow.run_local_server(port=8080 if is_web else 0, open_browser=True)
        token.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--slug", required=True)
    p.add_argument("--to", default=os.getenv("NEWSLETTER_RECIPIENTS"))
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if not a.to:
        raise SystemExit("No recipient: pass --to or set NEWSLETTER_RECIPIENTS in .env")
    sender = os.getenv("GMAIL_SENDER") or "me"
    msg = build_message(a.slug, a.to, sender)
    eml = existing_run(a.slug) / "message.eml"
    eml.write_bytes(bytes(msg))
    print(f"message built ({eml.stat().st_size // 1024} KB) -> {eml}")
    if a.dry_run:
        print(f"DRY RUN — not sent. Would send to: {a.to}")
        return
    raw = base64.urlsafe_b64encode(bytes(msg)).decode()
    sent = gmail_service().users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"sent to {a.to} — Gmail id {sent['id']}")


if __name__ == "__main__":
    main()
