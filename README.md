<div align="center">

# LL2C Newsletter AI

**Give it a topic and get a researched, AI-written, illustrated newsletter in your inbox, in your brand's style.**
**Uses only APIs with a free plan.**

`Tavily` researches · `Groq` writes · `Python` draws the infographics · `Cloudflare FLUX` makes the cover image · `Gmail API` sends

</div>

---

## How it works

```
 topic ──► 1. Research ──► 2. Writing ──► 3. Infographics ──► 4. Cover ──► 5. HTML ──► 6. Send
           (Tavily)        (Groq, PT-BR)  (Pillow, brand)     (FLUX)      (template)   (Gmail)
```

Each step is a separate script in `tools/` and saves its output to `.tmp/<slug>/`. If a step fails, you can resume from it.

| Step | Service | Free limit |
|---|---|---|
| Research | [Tavily](https://app.tavily.com) | 1,000 credits/month (about 2 per newsletter) |
| Writing | [Groq](https://console.groq.com) (`openai/gpt-oss-120b`) | about 1,000 requests/day |
| Infographics | Local Python (Pillow) | unlimited |
| Cover image | [Cloudflare Workers AI](https://dash.cloudflare.com) (FLUX-1-schnell) | 10,000 neurons/day (about 200 images) |
| Sending | [Gmail API](https://console.cloud.google.com) | free |

> **Why not Nano Banana?** Gemini's image models (Nano Banana) **have no free API tier**. Cloudflare FLUX makes the cover image and Python draws the infographics. Image models often get text and numbers wrong; code doesn't.

> The newsletter content is written in **Brazilian Portuguese (PT-BR)**. To change the language, edit the prompt in `tools/write_newsletter.py`.

---

## Requirements

- Python **3.10+**
- A Google (Gmail) account
- Free accounts on Tavily, Groq and Cloudflare. None of them asks for a credit card.

---

## Installation

```bash
git clone https://github.com/LucasLima0202/ll2c-newsletter-ai.git
cd ll2c-newsletter-ai

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

---

## API key setup

Create a file named **`.env`** in the project root. It's already in `.gitignore`, so it never goes to GitHub. Contents:

```env
# Research
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxx

# Writing
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
# Optional: forces a specific model (leave empty to use the default)
GROQ_MODEL=

# Cover image
CLOUDFLARE_ACCOUNT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CLOUDFLARE_API_TOKEN=xxxxxxxxxxxxxxxx

# Sending
GMAIL_SENDER=your-email@gmail.com
NEWSLETTER_RECIPIENTS=recipient@gmail.com
```

> To send to several people, separate the addresses with commas: `a@x.com,b@y.com`

### 1. Tavily (research)
1. Sign up at **[app.tavily.com](https://app.tavily.com)**.
2. Copy the **API Key** from the dashboard. It starts with `tvly-`.
3. Paste it into `TAVILY_API_KEY`.

### 2. Groq (writing)
1. Sign up at **[console.groq.com](https://console.groq.com)**.
2. Go to **API Keys**, click **Create API Key** and copy the key. It starts with `gsk_`.
3. Paste it into `GROQ_API_KEY`.

### 3. Cloudflare Workers AI (cover image)
1. Sign up at **[dash.cloudflare.com](https://dash.cloudflare.com)**.
2. **Account ID:** shown on the dashboard home page in the right sidebar, or in the URL (`dash.cloudflare.com/<ACCOUNT_ID>`). Paste it into `CLOUDFLARE_ACCOUNT_ID`.
3. **Token:** click the profile icon, then **My Profile → API Tokens → Create Token**, and use the **"Workers AI"** template. Paste it into `CLOUDFLARE_API_TOKEN`.

> This step is optional. If Cloudflare fails, the newsletter is sent without a cover image.

### 4. Gmail API (sending)
This is the longest part, but you only do it once:

1. Go to **[console.cloud.google.com](https://console.cloud.google.com)** and create a **new project**.
2. Under **APIs & Services → Library**, search for **Gmail API** and click **Enable**.
3. Under **APIs & Services → OAuth consent screen**:
   - User type: **External**
   - Fill in the app name and your email
   - Under **Test users**, **add your own Gmail address** (login fails without it)
4. Under **APIs & Services → Credentials**, click **Create credentials → OAuth client ID**:
   - Type: **Desktop app**. This is the simplest option.
   - If you use **Web application** instead, add `http://localhost:8080/` under **Authorized redirect URIs**.
5. Download the JSON and save it in the project root as **`credentials.json`**, with exactly that name.

On the first send, a browser window opens so you can authorize the app. If you see *"Google hasn't verified this app"*, click **Continue**. That's normal for apps in testing mode. After that, the login is saved in `token.json`, which is also in `.gitignore`.

### Quick setup check

```bash
python tools/research_topic.py --topic "test"
```

If you see `8 results -> ...`, Tavily is working. If a key is missing, the script names it: `Missing required env var 'X'`.

---

## Usage

### Generate a newsletter (without sending)

```bash
python tools/run_newsletter.py --topic "AI agents in small businesses"
```

This runs every step and **stops before sending**. Open the preview in your browser:

```
.tmp/ai-agents-in-small-businesses/preview.html
```

> **Check the facts before sending.** The AI only uses data from the research, but it can still get a label or an interpretation wrong. To fix something, edit `.tmp/<slug>/content.json` and rerun from the `render` step.

### Send

```bash
python tools/run_newsletter.py --slug ai-agents-in-small-businesses --from-step send --send
```

To send to a different recipient just this once:

```bash
python tools/run_newsletter.py --slug <slug> --from-step send --send --to someone@email.com
```

### Resume from a step

The steps are `research → write → render → hero → html → send`.

```bash
# Edited content.json? Regenerate the images and HTML:
python tools/run_newsletter.py --slug <slug> --from-step render

# Just want a new cover image:
python tools/run_newsletter.py --slug <slug> --from-step hero
```

### Run individual steps

| Script | What it does |
|---|---|
| `tools/research_topic.py --topic "..."` | Searches with Tavily and saves `research.json` |
| `tools/write_newsletter.py --slug X` | Writes the content with Groq and saves `content.json` |
| `tools/render_infographics.py --slug X` | Draws `stats.png` and `chart.png` |
| `tools/generate_hero_image.py --slug X` | Generates `hero.jpg` with FLUX |
| `tools/build_html.py --slug X [--preview]` | Builds `newsletter.html` (or `preview.html`) |
| `tools/send_gmail.py --slug X [--dry-run]` | Sends, or with `--dry-run` only builds the `.eml` |
| `tools/render_logo.py` | Converts the SVG logo to PNG (Gmail doesn't display SVG) |

---

## Project structure

```
├── brand/                 # Logo and brand guide (LL2C colors and typography)
├── templates/
│   └── newsletter.html    # Email template (tables and inline CSS, Gmail-safe)
├── tools/                 # Python scripts, one per step
├── workflows/
│   └── newsletter.md      # Detailed operating guide, with lessons learned
├── .tmp/                  # Output of each run (disposable, not in git)
├── .env                   # Your keys (you create it, not in git)
├── credentials.json       # Google OAuth client (you download it, not in git)
└── token.json             # Gmail login (created automatically, not in git)
```

### Brand identity

The colors come from the brand guide in `brand/` and are defined in `tools/_env.py`:

| Color | Hex | Used for |
|---|---|---|
| Main Blue | `#031B2F` | background |
| Secondary Blue | `#0B3954` | cards |
| Light Blue | `#BFD7EA` | secondary text |
| Electric Aqua | `#70E4EF` | highlights and links |
| Highlight | `#E0FF4F` | CTA button and the chart's largest value |

The **Plus Jakarta Sans** font is downloaded automatically on the first run. It's used in the infographics, but in the email body Gmail replaces it with a system font (Segoe UI or Arial).

---

## Troubleshooting

| Error | Fix |
|---|---|
| `Missing required env var 'X'` | Key `X` is missing from `.env` |
| `model_decommissioned` (Groq) | The model in `GROQ_MODEL` was retired. Leave the field empty. |
| `429` / rate limit (Groq) | Wait 1 minute. The daily limit applies to the whole account. |
| `redirect_uri_mismatch` (Google) | Use a **Desktop app** client, or add `http://localhost:8080/` to the redirect URIs |
| `access_denied` (Google) | Add your Gmail address under **Test users** on the consent screen |
| `invalid_grant` (Gmail) | The login expired (it lasts 7 days in testing mode). Delete `token.json` and send again. |
| Missing cover image | Cloudflare failed or the daily quota ran out. Everything else still works. |
| Email went to spam | Mark it as "Not spam" once |

---

## Security

- **Never commit** `.env`, `credentials.json` or `token.json`. They're all in `.gitignore`.
- If a key leaks, **create a new one** in that service's dashboard and delete the old one.
- The Gmail token only has the `gmail.send` permission: it can send email but can't read your inbox.

---

<div align="center">

**LL2C** · Technology • Automation • AI

</div>
