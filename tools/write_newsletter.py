"""Write newsletter content (English) with Groq from .tmp/<slug>/research.json.

Usage: python tools/write_newsletter.py --slug <slug>
Output: .tmp/<slug>/content.json
"""
import argparse
import json
import os

from groq import BadRequestError, Groq, NotFoundError

from _env import require_env, existing_run

# GROQ_MODEL (optional) is tried first; unknown models are skipped. Check ids: client.models.list()
MODELS = list(dict.fromkeys(m for m in [os.getenv("GROQ_MODEL"), "openai/gpt-oss-120b", "openai/gpt-oss-20b"] if m))

SYSTEM = """You are the newsletter writer for LL2C (Technology • Automation • AI).
Write in English, professional, clear and direct tone, for business owners and tech professionals.
RULES:
- Use ONLY facts present in the research provided. Do not invent numbers, names or dates.
- Every statistic in key_stats and in the chart must come literally from the research.
- key_stats.value: short, only numbers, %, $, x, letters and spaces (e.g. "40%", "9 to 4"). No symbols like ≈ → ~.
- key_stats.label must describe the number precisely (e.g. who was surveyed vs. who takes the action).
- body_html may only use <p>, <strong>, <em>, <ul>, <li>, <a href>. No styles.
- Reply ONLY with a valid JSON object in this format:
{
  "subject": "email subject (max 70 characters)",
  "preheader": "preview text (max 110 characters)",
  "title": "issue title",
  "intro": "opening paragraph (2-3 sentences, plain text)",
  "sections": [{"heading": "...", "body_html": "<p>...</p>"}],
  "key_stats": [{"value": "73%", "label": "short description (max 60 characters)", "source": "short source name (e.g. SF Federal Reserve, 2024)"}],
  "chart": {"title": "...", "unit": "%", "labels": ["..."], "values": [12.5], "source": "short source name"} or null,
  "hero_prompt": "English prompt for an abstract illustration about the topic, no text, no letters",
  "cta": {"text": "button text", "url": "a URL from the sources"},
  "sources": [{"title": "...", "url": "..."}]
}
- 3 to 4 sections, 3 to 4 key_stats (use fewer if the research has fewer numbers).
- chart: only include it if the research has 3+ comparable numeric values; otherwise null.
"""


REQUIRED = ["subject", "preheader", "title", "intro", "sections", "key_stats", "hero_prompt", "cta", "sources"]


def validate(c: dict) -> None:
    missing = [k for k in REQUIRED if k not in c]
    if missing:
        raise ValueError(f"missing keys: {missing}")
    if not c["sections"] or not all("heading" in s and "body_html" in s for s in c["sections"]):
        raise ValueError("sections malformed")
    for s in c["key_stats"]:
        if "value" not in s or "label" not in s:
            raise ValueError("key_stats malformed")
    ch = c.get("chart")
    if ch:
        if len(ch.get("labels", [])) != len(ch.get("values", [])) or len(ch["labels"]) < 2:
            c["chart"] = None
        else:
            ch["values"] = [float(v) for v in ch["values"]]


# LLMs like typographic variants (non-breaking hyphen, narrow spaces) that the brand font lacks
_CHAR_FIX = str.maketrans({"‐": "-", "‑": "-", "‒": "-", " ": " ",
                           " ": " ", " ": " ", "​": ""})


def normalize(text: str) -> str:
    return text.translate(_CHAR_FIX)


def build_user_prompt(research: dict) -> str:
    parts = [f"TOPIC: {research['topic']}"]
    if research.get("answer"):
        parts.append(f"SUMMARY: {research['answer']}")
    for i, r in enumerate(research["results"], 1):
        parts.append(f"[{i}] {r['title']}\nURL: {r['url']}\n{(r['content'] or '')[:1500]}")
    return "\n\n".join(parts)


def write(research: dict) -> dict:
    client = Groq(api_key=require_env("GROQ_API_KEY"))
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": build_user_prompt(research)}]
    last_err = None
    for model in MODELS:
        for attempt in range(2):
            try:
                resp = client.chat.completions.create(
                    model=model, messages=messages, temperature=0.5,
                    response_format={"type": "json_object"}, max_completion_tokens=4096,
                )
                content = json.loads(normalize(resp.choices[0].message.content))
                validate(content)
                content["_model"] = model
                return content
            except (NotFoundError, BadRequestError) as e:
                if isinstance(e, BadRequestError) and "decommissioned" not in str(e) and "not found" not in str(e).lower():
                    last_err = e
                    print(f"[{model} attempt {attempt + 1}] {e}")
                    continue
                print(f"[{model}] not available on Groq (decommissioned/unknown) — skipping")
                break
            except Exception as e:  # invalid JSON, schema error, or API error
                last_err = e
                print(f"[{model} attempt {attempt + 1}] {type(e).__name__}: {e}")
    raise SystemExit(f"Groq failed on all models: {last_err}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--slug", required=True)
    a = p.parse_args()
    d = existing_run(a.slug)
    research = json.loads((d / "research.json").read_text(encoding="utf-8"))
    content = write(research)
    out = d / "content.json"
    out.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"content ({content['_model']}) -> {out}")


if __name__ == "__main__":
    main()
