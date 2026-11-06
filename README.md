<div align="center">

# LL2C Newsletter AI

**Dê um tema e receba no e-mail uma newsletter pesquisada, escrita e ilustrada por IA, com a sua marca.**
**Usa apenas APIs com plano gratuito.**

`Tavily` pesquisa · `Groq` escreve · `Python` desenha os infográficos · `Cloudflare FLUX` gera a imagem de capa · `Gmail API` envia

</div>

---

## Como funciona

```
 tema ──► 1. Pesquisa ──► 2. Redação ──► 3. Infográficos ──► 4. Capa ──► 5. HTML ──► 6. Envio
          (Tavily)        (Groq, PT-BR)  (Pillow, marca)     (FLUX)     (template)   (Gmail)
```

Cada etapa é um script independente em `tools/` e salva o resultado em `.tmp/<slug>/`. Se algo falhar, você retoma da etapa que parou.

| Etapa | Serviço | Limite grátis |
|---|---|---|
| Pesquisa | [Tavily](https://app.tavily.com) | 1.000 créditos/mês (cerca de 2 por newsletter) |
| Redação | [Groq](https://console.groq.com) (`openai/gpt-oss-120b`) | cerca de 1.000 requisições/dia |
| Infográficos | Python local (Pillow) | ilimitado |
| Imagem de capa | [Cloudflare Workers AI](https://dash.cloudflare.com) (FLUX-1-schnell) | 10.000 neurons/dia (cerca de 200 imagens) |
| Envio | [Gmail API](https://console.cloud.google.com) | grátis |

> **Por que não Nano Banana?** Os modelos de imagem do Gemini (Nano Banana) **não têm plano gratuito na API**. O FLUX da Cloudflare faz a capa, e o Python desenha os infográficos. Modelos de imagem costumam errar texto e números; o código não erra.

---

## Requisitos

- Python **3.10+**
- Uma conta Google (Gmail)
- Contas gratuitas em Tavily, Groq e Cloudflare. Nenhuma pede cartão.

---

## Instalação

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

## Configuração das chaves

Crie um arquivo chamado **`.env`** na raiz do projeto. Ele já está no `.gitignore` e nunca vai para o GitHub. Conteúdo:

```env
# Pesquisa
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxx

# Redação
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
# Opcional: força um modelo específico (deixe vazio para usar o padrão)
GROQ_MODEL=

# Imagem de capa
CLOUDFLARE_ACCOUNT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CLOUDFLARE_API_TOKEN=xxxxxxxxxxxxxxxx

# Envio
GMAIL_SENDER=seu-email@gmail.com
NEWSLETTER_RECIPIENTS=destinatario@gmail.com
```

> Para enviar para várias pessoas, separe os e-mails por vírgula: `a@x.com,b@y.com`

### 1. Tavily (pesquisa)
1. Crie uma conta em **[app.tavily.com](https://app.tavily.com)**.
2. No dashboard, copie a **API Key**, que começa com `tvly-`.
3. Cole em `TAVILY_API_KEY`.

### 2. Groq (redação)
1. Crie uma conta em **[console.groq.com](https://console.groq.com)**.
2. Vá em **API Keys**, clique em **Create API Key** e copie a chave, que começa com `gsk_`.
3. Cole em `GROQ_API_KEY`.

### 3. Cloudflare Workers AI (imagem de capa)
1. Crie uma conta em **[dash.cloudflare.com](https://dash.cloudflare.com)**.
2. **Account ID:** fica na página inicial do dashboard, na barra lateral direita, ou na URL (`dash.cloudflare.com/<ACCOUNT_ID>`). Cole em `CLOUDFLARE_ACCOUNT_ID`.
3. **Token:** clique no ícone de perfil, depois em **My Profile → API Tokens → Create Token**, e use o template **"Workers AI"**. Cole em `CLOUDFLARE_API_TOKEN`.

> Essa etapa é opcional. Se a Cloudflare falhar, a newsletter sai sem a imagem de capa.

### 4. Gmail API (envio)
Essa é a parte mais longa, mas você só faz uma vez:

1. Acesse **[console.cloud.google.com](https://console.cloud.google.com)** e crie um **projeto novo**.
2. Em **APIs e serviços → Biblioteca**, procure **Gmail API** e clique em **Ativar**.
3. Em **APIs e serviços → Tela de consentimento OAuth**:
   - Tipo de usuário: **Externo**
   - Preencha o nome do app e o seu e-mail
   - Em **Usuários de teste**, **adicione o seu próprio Gmail** (sem isso o login falha)
4. Em **APIs e serviços → Credenciais**, clique em **Criar credenciais → ID do cliente OAuth**:
   - Tipo: **App para computador** (*Desktop app*). É o mais simples.
   - Se usar **Aplicativo da Web**, adicione `http://localhost:8080/` em **URIs de redirecionamento autorizados**.
5. Baixe o JSON e salve na raiz do projeto como **`credentials.json`**, exatamente com esse nome.

No primeiro envio, o navegador abre para você autorizar. Se aparecer *"O Google não verificou este app"*, clique em **Continuar**. Isso é normal para apps em modo de teste. Depois disso o login fica salvo em `token.json`, que também está no `.gitignore`.

### Teste rápido da configuração

```bash
python tools/research_topic.py --topic "teste"
```

Se aparecer `8 results -> ...`, a Tavily está funcionando. Se faltar alguma chave, o script diz qual é: `Missing required env var 'X'`.

---

## Uso

### Gerar uma newsletter (sem enviar)

```bash
python tools/run_newsletter.py --topic "Agentes de IA em pequenas empresas"
```

O comando faz todas as etapas e **para antes de enviar**. Abra a prévia no navegador:

```
.tmp/agentes-de-ia-em-pequenas-empresas/preview.html
```

> **Revise os fatos antes de enviar.** A IA usa apenas dados da pesquisa, mas pode errar um rótulo ou uma interpretação. Para corrigir, edite `.tmp/<slug>/content.json` e rode de novo a partir da etapa `render`.

### Enviar

```bash
python tools/run_newsletter.py --slug agentes-de-ia-em-pequenas-empresas --from-step send --send
```

Para enviar a outro destinatário só desta vez:

```bash
python tools/run_newsletter.py --slug <slug> --from-step send --send --to alguem@email.com
```

### Retomar de uma etapa

As etapas são `research → write → render → hero → html → send`.

```bash
# Editou o content.json? Regenere as imagens e o HTML:
python tools/run_newsletter.py --slug <slug> --from-step render

# Só quer outra imagem de capa:
python tools/run_newsletter.py --slug <slug> --from-step hero
```

### Rodar etapas avulsas

| Script | O que faz |
|---|---|
| `tools/research_topic.py --topic "..."` | Pesquisa na Tavily e salva `research.json` |
| `tools/write_newsletter.py --slug X` | Escreve o conteúdo com o Groq e salva `content.json` |
| `tools/render_infographics.py --slug X` | Desenha `stats.png` e `chart.png` |
| `tools/generate_hero_image.py --slug X` | Gera `hero.jpg` com o FLUX |
| `tools/build_html.py --slug X [--preview]` | Monta `newsletter.html` (ou `preview.html`) |
| `tools/send_gmail.py --slug X [--dry-run]` | Envia, ou com `--dry-run` só gera o `.eml` |
| `tools/render_logo.py` | Converte o logo SVG em PNG (o Gmail não mostra SVG) |

---

## Estrutura

```
├── brand/                 # Logo e guia de marca (cores e tipografia LL2C)
├── templates/
│   └── newsletter.html    # Template de e-mail (tabelas e CSS inline, compatível com Gmail)
├── tools/                 # Scripts Python, um por etapa
├── workflows/
│   └── newsletter.md      # Manual operacional detalhado, com aprendizados
├── .tmp/                  # Saídas de cada execução (descartável, fora do git)
├── .env                   # Suas chaves (você cria, fora do git)
├── credentials.json       # OAuth do Google (você baixa, fora do git)
└── token.json             # Login do Gmail (gerado automaticamente, fora do git)
```

### Identidade visual

As cores vêm do guia de marca em `brand/` e estão em `tools/_env.py`:

| Cor | Hex | Uso |
|---|---|---|
| Azul Principal | `#031B2F` | fundo |
| Azul Secundário | `#0B3954` | cards |
| Azul Claro | `#BFD7EA` | texto secundário |
| Água Elétrica | `#70E4EF` | destaques e links |
| Destaque | `#E0FF4F` | botão de CTA e maior valor do gráfico |

A fonte **Plus Jakarta Sans** é baixada automaticamente na primeira execução. Ela aparece nos infográficos, mas no corpo do e-mail o Gmail troca pela fonte do sistema (Segoe UI ou Arial).

---

## Problemas comuns

| Erro | Solução |
|---|---|
| `Missing required env var 'X'` | Falta a chave `X` no `.env` |
| `model_decommissioned` (Groq) | O modelo em `GROQ_MODEL` foi descontinuado. Deixe o campo vazio. |
| `429` / rate limit (Groq) | Espere 1 minuto. O limite diário vale para a conta inteira. |
| `redirect_uri_mismatch` (Google) | Use um cliente **Desktop app** ou adicione `http://localhost:8080/` às URIs de redirecionamento |
| `access_denied` (Google) | Adicione seu Gmail em **Usuários de teste** na tela de consentimento |
| `invalid_grant` (Gmail) | O login expirou (em modo teste dura 7 dias). Apague o `token.json` e envie de novo. |
| Imagem de capa ausente | A Cloudflare falhou ou a cota do dia acabou. O resto funciona normalmente. |
| E-mail caiu no spam | Marque como "Não é spam" uma vez |

---

## Segurança

- **Nunca commite** `.env`, `credentials.json` ou `token.json`. Todos estão no `.gitignore`.
- Se uma chave vazar, **gere outra** no painel do serviço e apague a antiga.
- O token do Gmail tem apenas a permissão `gmail.send`: ele envia, mas não lê seus e-mails.

---

<div align="center">

**LL2C** · Tecnologia • Automação • IA

</div>
