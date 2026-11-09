<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/Logo-complete.svg">
    <img src="assets/Logo-complete-dark.svg" alt="LL2C" width="180">
  </picture>
</p>

<p align="center">
  <img src="assets/cover.png" alt="LL2C Newsletter AI preview" width="40%">
</p>

<h1 align="center">LL2C Newsletter AI</h1>

<p align="center">Turns a topic into a researched, AI-written, illustrated newsletter and sends it through Gmail. Free-tier APIs only.</p>

<p align="center">
  <img src="https://img.shields.io/badge/CLI-tool-3B82F6?style=flat" alt="CLI tool">
  <img src="https://img.shields.io/badge/language-Python-3776AB?style=flat" alt="language Python">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat" alt="license MIT">
</p>

## About

A pipeline of Python scripts that researches a topic, writes the newsletter with an LLM, draws infographics, generates a cover image and sends the result as an HTML email. Each step saves its output to `.tmp/<slug>/`, so a failed run can resume from the step that broke. The newsletter is written in English; to change the language, edit the `SYSTEM` prompt in `tools/write_newsletter.py`.

## Features

- Web research with Tavily (`research.json`)
- Newsletter writing with Groq (`openai/gpt-oss-120b`, falls back to `openai/gpt-oss-20b`)
- Infographics (`stats.png`, `chart.png`) drawn locally with Pillow in the brand colors
- Cover image with Cloudflare Workers AI (`flux-1-schnell`); optional, the email is sent without it if the step fails
- Gmail-safe HTML email built from a Jinja2 template, with a browser preview
- Sending through the Gmail API with the `gmail.send` scope only
- Resume from any step: `research → write → render → hero → html → send`

| Step | Service | Free limit |
|---|---|---|
| Research | [Tavily](https://app.tavily.com) | 1,000 credits/month (about 2 per newsletter) |
| Writing | [Groq](https://console.groq.com) | about 1,000 requests/day |
| Infographics | Local Python (Pillow) | unlimited |
| Cover image | [Cloudflare Workers AI](https://dash.cloudflare.com) | 10,000 neurons/day (about 200 images) |
| Sending | [Gmail API](https://console.cloud.google.com) | free |

## Tech Stack

- Python
- `tavily-python`, `groq`, `requests`
- `pillow`, `matplotlib`, `jinja2`
- `google-api-python-client`, `google-auth-oauthlib`
- `python-dotenv`

## Getting Started

### Prerequisites

- Python 3.10+
- A Google (Gmail) account
- Free accounts on Tavily, Groq and Cloudflare (no credit card required)

### Installation

```bash
git clone https://github.com/LucasLima0202/ll2c-newsletter-ai.git
cd ll2c-newsletter-ai
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root (it is gitignored).

| Variable | Description |
|----------|-------------|
| `TAVILY_API_KEY` | Tavily API key (`tvly-...`), from the [Tavily dashboard](https://app.tavily.com) |
| `GROQ_API_KEY` | Groq API key (`gsk_...`), from **API Keys** in the [Groq console](https://console.groq.com) |
| `GROQ_MODEL` | Optional. Overrides the default model; leave empty to use the default |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account ID (dashboard sidebar or `dash.cloudflare.com/<ACCOUNT_ID>`) |
| `CLOUDFLARE_API_TOKEN` | Token from **My Profile → API Tokens → Create Token**, "Workers AI" template |
| `GMAIL_SENDER` | Sender address. Defaults to the authorized account |
| `NEWSLETTER_RECIPIENTS` | Recipients, comma-separated (`a@x.com,b@y.com`) |

### Gmail API setup

1. In [Google Cloud Console](https://console.cloud.google.com), create a project and enable **Gmail API**.
2. **OAuth consent screen**: user type **External**, and add your own Gmail address under **Test users**.
3. **Credentials → Create credentials → OAuth client ID**, type **Desktop app**. For a **Web application** client, add `http://localhost:8080/` to the authorized redirect URIs.
4. Download the JSON and save it in the project root as `credentials.json`.

On the first send, a browser window opens to authorize the app ("Google hasn't verified this app" → **Continue**). The login is saved to `token.json`.

Never commit `.env`, `credentials.json` or `token.json`. They are all in `.gitignore`. If a key leaks, revoke it and create a new one.

### Check the setup

```bash
python tools/research_topic.py --topic "test"
```

A missing key is reported as `Missing required env var 'X'`.

## Usage

Generate a newsletter without sending it. The preview is written to `.tmp/<slug>/preview.html`:

```bash
python tools/run_newsletter.py --topic "AI agents in small businesses"
```

Check the facts in the preview before sending. To fix content, edit `.tmp/<slug>/content.json` and rerun from `render`.

Send:

```bash
python tools/run_newsletter.py --slug <slug> --from-step send --send
python tools/run_newsletter.py --slug <slug> --from-step send --send --to someone@email.com
```

Resume from a step:

```bash
python tools/run_newsletter.py --slug <slug> --from-step render   # after editing content.json
python tools/run_newsletter.py --slug <slug> --from-step hero     # new cover image only
```

Individual steps:

| Script | Output |
|---|---|
| `tools/research_topic.py --topic "..."` | `research.json` |
| `tools/write_newsletter.py --slug X` | `content.json` |
| `tools/render_infographics.py --slug X` | `stats.png`, `chart.png` |
| `tools/generate_hero_image.py --slug X` | `hero.jpg` |
| `tools/build_html.py --slug X [--preview]` | `newsletter.html` / `preview.html` |
| `tools/send_gmail.py --slug X [--dry-run]` | sends, or builds the `.eml` only |
| `tools/render_logo.py` | PNG logo for the email header (Gmail does not display SVG) |

### Troubleshooting

| Error | Fix |
|---|---|
| `Missing required env var 'X'` | Add `X` to `.env` |
| `model_decommissioned` (Groq) | The model in `GROQ_MODEL` was retired. Leave it empty |
| `429` / rate limit (Groq) | Wait 1 minute. The daily limit is per account |
| `redirect_uri_mismatch` (Google) | Use a Desktop app client, or add `http://localhost:8080/` |
| `access_denied` (Google) | Add your address under **Test users** |
| `invalid_grant` (Gmail) | The token expired (7 days in testing mode). Delete `token.json` and send again |
| No cover image | Cloudflare failed or the daily quota ran out |

## Project Structure

```
├── assets/                # README logos
├── templates/
│   └── newsletter.html    # Email template (tables + inline CSS, Gmail-safe)
├── tools/                 # One Python script per step; brand colors in tools/_env.py
├── workflows/
│   └── newsletter.md      # Operating guide and lessons learned
├── .tmp/                  # Output of each run (disposable, gitignored)
└── requirements.txt
```

Brand colors are defined in `tools/_env.py`: `#031B2F` background, `#0B3954` cards, `#BFD7EA` secondary text, `#70E4EF` highlights/links, `#E0FF4F` CTA and the chart's top value.

## License

Distributed under the MIT License. See [LICENSE](LICENSE).

## Author

**LL2C**: [@LucasLima0202](https://github.com/LucasLima0202)
