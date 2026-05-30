# Ativação do Google Calendar (C6)

> O **motor de sincronização** já está implementado e testado
> (`src/services/gcal_service.py`, `tests/test_gcal_service.py`). Este documento
> descreve os passos que faltam para ligar a integração **ao vivo** com a API do
> Google — eles exigem credenciais externas e um endpoint web, por isso ficam
> desativados por padrão (o motor é um no-op seguro enquanto isso).

## O que já existe

- **Modelo de dados:** `users.google_refresh_token`, `users.google_calendar_id`,
  `couples.gcal_calendar_id`, `tasks.gcal_event_id`, `tasks.gcal_synced_at`
  (migrations 0004 e 0006).
- **Motor de sync** (`gcal_service`): mapeia tarefa↔evento, escolhe o calendário
  (casal vs pessoal), é idempotente (cria/atualiza/apaga via `gcal_event_id`).
  Só tarefas com `due_at` viram evento.
- **Config:** `GOOGLE_OAUTH_CLIENT_ID/_SECRET/_REDIRECT_URI` +
  `config.google_calendar_enabled()`.
- **Ponto de injeção:** `gcal_service.set_client_factory(factory)` registra a
  fábrica que cria um `CalendarClient` real a partir de um `User`.

## Passos para ativar

### 1. Dependências (fora do requirements.txt para não pesar o MVP)

```bash
pip install google-api-python-client google-auth-oauthlib
```

### 2. Credenciais OAuth no Google Cloud

- Criar um projeto, habilitar a **Google Calendar API**.
- Criar credenciais OAuth 2.0 (tipo *Web application*).
- Registrar o redirect URI (ex.: `https://seu-app.up.railway.app/oauth/callback`).
- Definir as três variáveis `GOOGLE_OAUTH_*` no ambiente (Railway).

### 3. Endpoint web do callback

O bot hoje é **long-polling, sem servidor web**. É preciso subir um endpoint
HTTPS pequeno (aiohttp/FastAPI) com a rota do redirect URI que:

1. Recebe o `code` do Google.
2. Troca por tokens (`google-auth-oauthlib`).
3. Salva o `refresh_token` em `users.google_refresh_token` (criptografado em
   repouso) e o `google_calendar_id` escolhido.

Comandos do bot para iniciar o fluxo (ex.: `/calendario_conectar`) devem gerar a
URL de consentimento e enviá-la ao usuário.

### 4. Implementar o `CalendarClient` real e registrá-lo

Criar `src/services/gcal_client_google.py` com uma classe que cumpra o protocolo
`CalendarClient` (métodos `upsert_event` / `delete_event`) usando a Calendar API,
e no boot:

```python
from src.services import gcal_service
from src.services.gcal_client_google import make_client
gcal_service.set_client_factory(make_client)
```

### 5. Wirar o gatilho de sincronização

Chamar `gcal_service.sync_task_for_user(task_id, chat_id)` (via `asyncio.to_thread`)
após eventos que mudam `due_at`/`status`:

- conclusão (`cb_complete_task`, `cb_agora_concluir`) → apaga o evento;
- definir/alterar prazo (`cb_task_set_due`, `reschedule_task`) → cria/atualiza;
- criação com prazo.

Como `sync_task_for_user` é **no-op** quando o Google está desativado, esses
gatilhos podem ser adicionados com segurança antes mesmo da ativação completa.

## Decisões em aberto

- **Calendário do casal:** usar um calendário Google compartilhado
  (`couples.gcal_calendar_id`) vs. duplicar nos calendários pessoais. O motor já
  suporta o compartilhado com fallback pessoal (`target_calendar_id`).
- **Mão dupla (Calendar → bot):** detectar edições feitas no Google exige
  webhooks/push ou polling com *sync token* e resolução de conflito. Fora do
  escopo desta fundação (ver docs/08 §6.3).
