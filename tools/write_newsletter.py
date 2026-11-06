"""Write newsletter content (PT-BR) with Groq from .tmp/<slug>/research.json.

Usage: python tools/write_newsletter.py --slug <slug>
Output: .tmp/<slug>/content.json
"""
import argparse
import json
import os

from groq import BadRequestError, Groq, NotFoundError

from _env import require_env, run_dir

# GROQ_MODEL (optional) is tried first; unknown models are skipped. Check ids: client.models.list()
MODELS = list(dict.fromkeys(m for m in [os.getenv("GROQ_MODEL"), "openai/gpt-oss-120b", "openai/gpt-oss-20b"] if m))

SYSTEM = """Você é o redator da newsletter da LL2C (Tecnologia • Automação • IA).
Escreva em português do Brasil, tom profissional, claro e direto, para donos de negócio e profissionais de tecnologia.
REGRAS:
- Use SOMENTE fatos presentes na pesquisa fornecida. Não invente números, nomes ou datas.
- Cada estatística em key_stats e no gráfico deve vir literalmente da pesquisa.
- key_stats.value: curto, só números, %, R$, x, letras e espaços (ex.: "40%", "9 para 4"). Sem símbolos como ≈ → ~.
- key_stats.label deve descrever o número com precisão (ex.: quem foi entrevistado vs. quem faz a ação).
- body_html pode usar apenas <p>, <strong>, <em>, <ul>, <li>, <a href>. Sem estilos.
- Responda APENAS com um objeto JSON válido neste formato:
{
  "subject": "assunto do e-mail (máx 70 caracteres)",
  "preheader": "texto de pré-visualização (máx 110 caracteres)",
  "title": "título da edição",
  "intro": "parágrafo de abertura (2-3 frases, texto puro)",
  "sections": [{"heading": "...", "body_html": "<p>...</p>"}],
  "key_stats": [{"value": "73%", "label": "descrição curta (máx 60 caracteres)", "source": "nome curto da fonte (ex.: Federal Reserve SF, 2024)"}],
  "chart": {"title": "...", "unit": "%", "labels": ["..."], "values": [12.5], "source": "nome curto da fonte"} ou null,
  "hero_prompt": "English prompt for an abstract illustration about the topic, no text, no letters",
  "cta": {"text": "texto do botão", "url": "uma URL das fontes"},
  "sources": [{"title": "...", "url": "..."}]
}
- 3 a 4 seções, 3 a 4 key_stats (se a pesquisa tiver menos números, use menos).
- chart: só inclua se houver 3+ valores numéricos comparáveis na pesquisa; senão null.
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


def build_user_prompt(research: dict) -> str:
    parts = [f"TEMA: {research['topic']}"]
    if research.get("answer"):
        parts.append(f"RESUMO: {research['answer']}")
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
                content = json.loads(resp.choices[0].message.content)
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
    d = run_dir(a.slug)
    research = json.loads((d / "research.json").read_text(encoding="utf-8"))
    content = write(research)
    out = d / "content.json"
    out.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"content ({content['_model']}) -> {out}")


if __name__ == "__main__":
    main()
