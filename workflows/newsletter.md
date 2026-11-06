# Workflow: LL2C Newsletter

## Objective
Turn a topic into a researched, branded (LL2C) HTML newsletter with infographics and send it via Gmail, using only free APIs.

## Inputs
- `topic`: the newsletter subject in plain text (PT-BR or EN). Content is always written in PT-BR.
- `recipients`: `NEWSLETTER_RECIPIENTS` in `.env` (e.g. your own address while testing), or `--to`.

## Free stack (verified 2026-11-06)
| Step | Service | Free limit |
|---|---|---|
| Research | Tavily | 1,000 credits/month (advanced search = 2 credits) |
| Writing | Groq (`openai/gpt-oss-120b`, fallback `openai/gpt-oss-20b`) | ~30 RPM / ~1K req/day per org |
| Infographics | Local Python (Pillow) | unlimited |
| Hero image | Cloudflare Workers AI FLUX-1-schnell | 10k neurons/day (~43 per image) |
| Send | Gmail API (OAuth) | free |

Nano Banana (Gemini image models) has **no free API tier** (AI Studio pricing page: "Free tier: Not available"), so it's replaced above. Recheck if Google changes this.

## Setup (one time)
1. `.env`: `TAVILY_API_KEY`, `GROQ_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `GMAIL_SENDER`, `NEWSLETTER_RECIPIENTS` (see `.env.example`).
2. Gmail API: Google Cloud Console → new project → enable **Gmail API** → OAuth consent screen (External, Testing, add yourself as a test user) → Credentials → OAuth client ID → **Desktop app** → download as `credentials.json` into the project root. The first send opens a browser and saves `token.json`.
3. `python tools/render_logo.py` (the runner does this automatically if `brand/logo.png` is missing).

## Tools
1. `tools/research_topic.py`: Tavily search → `research.json`
2. `tools/write_newsletter.py`: Groq JSON content → `content.json`
3. `tools/render_infographics.py`: `stats.png`, `chart.png`
4. `tools/generate_hero_image.py`: `hero.jpg` (optional, non-fatal)
5. `tools/build_html.py`: `newsletter.html` (cid images), `preview.html` (`--preview`)
6. `tools/send_gmail.py`: Gmail send; `--dry-run` only writes `message.eml`
7. `tools/run_newsletter.py`: runs all steps in order; `--from-step` resumes

## Steps
1. `python tools/run_newsletter.py --topic "<topic>"` (no `--send`). Everything lands in `.tmp/<slug>/`.
2. Open `.tmp/<slug>/preview.html` and review the facts against `research.json`. AI can still get things wrong.
3. Ask the user to confirm before sending, then run `python tools/run_newsletter.py --slug <slug> --from-step send --send`.

## Outputs
- Deliverable: the email in the recipients' Gmail inboxes.
- Intermediates (disposable): `.tmp/<slug>/` holds research.json, content.json, images, html and message.eml.

## Edge Cases & Failure Handling
- Tavily returns no results: broaden the topic.
- Groq returns invalid JSON or a bad schema: the tool retries once, then switches to the fallback model. On a 429 (rate limit), wait a minute; the daily token cap is shared per org.
- No numeric data for a chart: `chart` is null and `chart.png` is skipped.
- Cloudflare fails (quota or token): the newsletter is sent without a hero image.
- Gmail `invalid_grant`: delete `token.json` and re-authorize. In Testing mode, refresh tokens expire after 7 days.
- Font download fails: falls back to DejaVu Sans.

## Learnings
<!-- Append rate limits, quirks, and fixes discovered while running this workflow. -->
- Gmail strips SVG and web fonts: the logo is rendered to PNG, and the font stack falls back to Segoe UI/Arial.
- 2026-11-06: Groq retired `qwen-2.5-coder-32b` and no longer lists `llama-3.3-70b-versatile`. A retired model returns a 400 `model_decommissioned` error, not a 404, so `write_newsletter.py` now skips both cases. To see current models, run `Groq().models.list()`. Leave `GROQ_MODEL` empty to use gpt-oss-120b.
- The fontsource Plus Jakarta Sans TTF is latin-only, so symbols like `≈` and `→` came out as broken glyphs. The renderer now switches to DejaVu for that text, and the prompt asks for plain values.
- The first full run used about 2 Tavily credits, about 1 Groq request and 1 FLUX image. It took about 1 min end to end and made a 227 KB email.
- Groq sometimes mislabels a stat, e.g. "195 líderes que testam agentes" when the 195 were the people surveyed. Always review the preview before sending.
- The OAuth client JSON must be named `credentials.json` (with an "s") so `.gitignore` covers it. `credential.json` and `client_secret*.json` are now ignored too. A "Web application" client also works if `http://localhost:8080/` is listed in its Authorized redirect URIs (`send_gmail.py` uses port 8080 for web clients). A "Desktop app" client needs no redirect setup.
- The infographics are now full panels: a header with label and logo, numbered cards, progress rings for % values, a source line per stat, and gradient bars on a scaled axis. Groq now returns `source` on each `key_stats` item and on `chart`.
