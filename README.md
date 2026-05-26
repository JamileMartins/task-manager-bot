# Task Manager — Bot de Tarefas para Telegram

Um "segundo cérebro" de tarefas no Telegram, **mono-usuário**, projetado para baixo atrito e apoio a funções executivas (TDAH). Captura por brain dump, classificação assistida por IA, Matriz de Eisenhower, sugestão de "o que fazer agora", sistema de impedimentos e rituais de revisão.

> **Mono-usuário por design:** cada pessoa roda a sua própria instância (próprio bot, próprio banco, próprias chaves). O bot responde apenas ao `chat_id` autorizado e ignora qualquer outro. Não é um serviço compartilhado.

## Privacidade e segurança (importante)

- **Seus segredos não vão para o Git.** O `.gitignore` bloqueia o `.env` (que guarda tokens e a URL do banco). Só o `.env.example`, com campos vazios, é versionado.
- **Seus dados (tarefas) não ficam no código** — ficam no seu banco (Supabase), separado do repositório.
- **Antes do primeiro commit**, rode `git status` e confirme que `.env` **não** aparece. Se um segredo já tiver sido commitado alguma vez, ele permanece no histórico do Git: revogue e gere novos tokens (BotFather, Google, Supabase).
- Quem clonar este repositório **não** acessa seus dados: precisa criar as próprias contas e a própria instância.

## Stack

Python 3.11+ · python-telegram-bot v21+ · PostgreSQL (Supabase) · SQLAlchemy + Alembic · Google Gemini API · APScheduler · Railway/Fly.io.

> **Sobre o uso de IA:** o bot usa a **Google Gemini API** para classificar tarefas em tempo de execução. O **Claude Code** (Anthropic) foi usado como assistente de desenvolvimento — ele não é uma dependência do bot em produção.

---

## Instalação do zero (qualquer pessoa)

Estas instruções servem tanto para a autora quanto para quem clonou o repositório.

### 1. Pré-requisitos (crie as suas próprias contas)

| Serviço | Para quê | O que você obtém |
|---------|----------|------------------|
| [@BotFather](https://t.me/BotFather) no Telegram | Criar seu bot | `TELEGRAM_BOT_TOKEN` |
| [@userinfobot](https://t.me/userinfobot) no Telegram | Descobrir seu chat_id | `AUTHORIZED_CHAT_ID` |
| [Supabase](https://supabase.com) | Banco PostgreSQL gerenciado | `DATABASE_URL` (com `?sslmode=require`) |
| [Google AI Studio](https://aistudio.google.com) | Classificação de tarefas por IA | `GEMINI_API_KEY` |
| [Railway](https://railway.app) ou [Fly.io](https://fly.io) | Hospedar 24/7 (opcional no início) | — |

### 2. Clonar e configurar

```bash
git clone <url-do-seu-fork>
cd task-manager-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                   # preencha com SEUS valores
```

Edite o `.env` com seus próprios tokens. **Nunca** versione esse arquivo.

### 3. Banco de dados

```bash
alembic upgrade head                   # cria as tabelas
```

### 4. Rodar localmente

```bash
python -m src.main
```

Abra seu bot no Telegram e mande uma mensagem. Como o bot é mono-usuário, ele só responderá ao `chat_id` que você configurou em `AUTHORIZED_CHAT_ID`.

### 5. Deploy 24/7 (opcional)

Suba o repositório para a Railway ou Fly.io e configure as variáveis de ambiente (os mesmos campos do `.env`) como **secrets da plataforma** — nunca no código. Detalhes na seção 11 da especificação técnica.

---

## Documentos (leia nesta ordem para desenvolver)

1. **`CLAUDE.md`** — guia e princípios de design para desenvolver com o Claude Code.
2. **`docs/01_PRD.md`** — requisitos do produto: visão, escopo, requisitos, fluxos.
3. **`docs/02_ESPECIFICACAO_TECNICA.md`** — stack, arquitetura, modelo de dados, IA, jobs, segurança, fases.
4. **`docs/03_HISTORIAS_DE_USUARIO.md`** — backlog de histórias com critérios de aceitação, por fase.
5. **`docs/04_PROMPT_CLASSIFICACAO_IA.md`** — prompt completo do classificador (system prompt, regras, exemplos, parsing).
6. **`docs/05_TEXTOS_DO_BOT.md`** — microcopy do bot, com tom e variações (centralizar em `utils/textos.py`).
7. **`docs/06_PROMPT_INICIAL_CLAUDE_CODE.md`** — prompts prontos para colar no Claude Code, fase a fase.

## Como desenvolver com o Claude Code

1. Abra esta pasta como raiz do projeto no Claude Code.
2. Cole o prompt inicial de `docs/06_PROMPT_INICIAL_CLAUDE_CODE.md` para começar a Fase F1.
3. Implemente **uma fase por vez** e valide os critérios de aceitação antes de avançar.

## Licença

[MIT](LICENSE) — uso livre, sem garantias. Cada instância é independente e roda com as credenciais de quem a hospeda.
