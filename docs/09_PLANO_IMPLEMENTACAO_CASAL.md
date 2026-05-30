# Plano de Implementação — Modo Casal e Multiusuário

> Plano executável para evoluir o bot de mono-usuário para uso por um casal.
> Complementa `08_ARQUITETURA_CASAL.md` (decisões de arquitetura) com
> **requisitos**, **tasks concretas por arquivo** e **critérios de aceitação**.
>
> Status: pronto para implementar. Ordem: C1 → C6, uma fase por vez (convenção
> do `CLAUDE.md`). Cada fase termina com testes verdes e critérios atendidos.

---

## 1. Requisitos

### 1.1 Funcionais

| ID | Requisito | Fase |
| --- | --- | --- |
| RF-01 | O bot aceita mais de um usuário autorizado (não só `AUTHORIZED_CHAT_ID`). | C1 |
| RF-02 | Cada usuário tem suas listas/tarefas pessoais isoladas; ninguém vê o pessoal do outro. | C1 |
| RF-03 | Jobs (resumo diário, revisão semanal, lembretes, medicações) rodam por usuário registrado, respeitando o horário e o `paused_until` de cada um. | C1 |
| RF-04 | Um usuário pode criar um convite de casal e gerar um código curto. | C2 |
| RF-05 | O outro usuário entra no casal usando o código, vinculando os dois chats. | C2 |
| RF-06 | Um usuário só pode pertencer a um casal por vez; convite expira e é de uso único. | C2 |
| RF-07 | Tarefas de casal são visíveis e editáveis pelos dois membros. | C3 |
| RF-08 | A captura por texto/voz pode destinar uma tarefa ao casal; `/casal` lista as tarefas compartilhadas reais (não um dump). | C3 |
| RF-09 | Quando um membro cria/conclui/reagenda uma tarefa de casal, o outro é notificado no bot dele. | C4 |
| RF-10 | Uma tarefa de casal pode ter "de quem é a vez" (`assigned_to`). | C5 |
| RF-11 | (Futuro) Tarefas com prazo sincronizam com o Google Calendar do usuário/casal. | C6 |

### 1.2 Não-funcionais

| ID | Requisito |
| --- | --- |
| RNF-01 | **Privacidade:** tarefa pessoal nunca cruza para o casal. Filtro de visibilidade num único helper, coberto por testes. |
| RNF-02 | Migrações sempre via Alembic (`run_migrations()` roda `upgrade head` no boot). Nada de alteração manual em produção. |
| RNF-03 | Datas timezone-aware (`America/Fortaleza`). Nunca naive. |
| RNF-04 | Segredos só por env (tokens, client secret OAuth). Refresh token Google criptografado em repouso. |
| RNF-05 | Serviços testáveis sem Telegram (sem dependência de `Update`). |
| RNF-06 | Tom acolhedor e PT-BR em todas as mensagens novas (`utils/textos.py`). |
| RNF-07 | Compatibilidade retroativa: o usuário atual em produção continua funcionando sem reconfiguração. |

---

## 2. Arquitetura (resumo)

Detalhes em `08_ARQUITETURA_CASAL.md`. Decisões que guiam este plano:

- **Opção B:** um bot por pessoa, mesmo código, **um Postgres único**. Começar
  com **um processo, dois `Application`** (arranjo B.1).
- O DB **já é multiusuário** (keyed por `telegram_chat_id`). O que destrava é a
  casca: `AUTHORIZED_CHAT_ID`, `setup_jobs` com chat fixo, `is_paused` hard-coded.
- Entidade `couple` + `couple_members`; tarefas/listas ganham `couple_id`.
  Visibilidade: `couple_id IS NULL` = pessoal; `couple_id = X` = do casal.
- Autenticação = **pareamento por código de convite** (o `chat_id` já é a
  identidade).

---

## 3. Fase C1 — Destravar multiusuário (base)

**Objetivo:** o bot serve N usuários registrados, com isolamento total e jobs
por usuário. Sem feature nova de casal ainda.

### 3.1 Configuração

- **`src/config.py`**
  - [ ] Adicionar `ALLOWED_CHAT_IDS: set[int]` lido de env (CSV), ex.
    `ALLOWED_CHAT_IDS="123,456"`.
  - [ ] Manter `AUTHORIZED_CHAT_ID` por compatibilidade, mas incluí-lo no
    conjunto: `ALLOWED_CHAT_IDS = {AUTHORIZED_CHAT_ID} | parsed`.
- **`.env.example`**
  - [ ] Documentar `ALLOWED_CHAT_IDS`.

### 3.2 Autorização

- **`src/handlers/common.py:25` (`is_authorized`)**
  - [ ] Trocar `update.effective_chat.id == AUTHORIZED_CHAT_ID` por
    `update.effective_chat.id in ALLOWED_CHAT_IDS`.
- **`src/handlers/config_handler.py:25`**
  - [ ] Mesma troca no `_is_authorized` local (ou importar o de `common`).
- **`src/handlers/common.py` `error_handler` (linha ~422)**
  - [ ] `chat_id != AUTHORIZED_CHAT_ID` → `chat_id not in ALLOWED_CHAT_IDS`.

### 3.3 Jobs por usuário

- **`src/handlers/rituals.py` `setup_jobs` (linha 459)**
  - [ ] Mudar assinatura para `setup_jobs(app)` e iterar sobre **todos os
    usuários registrados** (novo `task_service.get_all_users()`), agendando
    `_schedule_daily`, `_schedule_weekly` e `rollover_medications_job` por
    `chat_id`. Os jobs já leem `context.job.data["chat_id"]` — só falta o loop.
  - [ ] `send_reminders` continua um job único (varre todos), mas o guard
    `is_paused(AUTHORIZED_CHAT_ID)` (linha 79) deve sair: a pausa é **por
    tarefa/usuário**. Filtrar cada item de `due`/`waiting`/`overdue` por
    `is_paused(chat_id)` do dono, não global.
- **`src/main.py:314`**
  - [ ] `setup_jobs(app, AUTHORIZED_CHAT_ID)` → `setup_jobs(app)`.

### 3.4 Serviço

- **`src/services/task_service.py`**
  - [ ] `get_all_users() -> list[User]` (ou `list[int]` de chat_ids) para o loop
    de jobs.

### 3.5 `cmd_setgrupo` / config

- **`src/handlers/common.py:252` (`cmd_setgrupo`)**
  - [ ] Não gravar em `AUTHORIZED_CHAT_ID` fixo. Resolver o usuário pelo
    `from_user.id` de quem deu o comando no grupo (ou adiar — o grupo será
    substituído pelo modelo de casal real na C3; marcar como deprecated).

### 3.6 Testes (C1)

- [ ] `is_authorized` aceita qualquer id da allowlist e rejeita fora dela.
- [ ] Dois usuários distintos: tarefas de A não aparecem nas queries de B.
- [ ] `get_all_users` retorna todos; jobs agendados um por usuário.

### 3.7 Critério de aceitação

> Dois chats de teste convivem no mesmo bot sem vazar dados; cada um recebe seu
> resumo diário no horário configurado; o usuário de produção segue intacto.

---

## 4. Fase C2 — Entidade casal + pareamento

**Objetivo:** dois usuários se vinculam num casal via código de convite.

### 4.1 Modelo de dados / migração

- **`src/db/models.py`**
  - [ ] `Couple` (`id`, `created_at`, `gcal_calendar_id` nullable p/ futuro).
  - [ ] `CoupleMember` (`couple_id`, `user_id`, `role`, `joined_at`, PK composta).
  - [ ] `Invite` (`code` pk, `couple_id`, `created_by`, `expires_at`, `used_by`).
  - [ ] `User`: relationship para `couple` via `couple_members` (helper
    `User.couple_id` resolvido por query/property).
- **`src/db/migrations/versions/0004_couples.py`**
  - [ ] Criar tabelas `couples`, `couple_members`, `invites`.

### 4.2 Serviço

- **`src/services/couple_service.py` (novo)**
  - [ ] `create_invite(chat_id) -> str` (cria `couple` + `invite`, retorna código).
  - [ ] `accept_invite(chat_id, code) -> AcceptResult` (valida: existe / não
    expirou / não usado / usuário ainda sem casal; cria `couple_member`; marca
    usado). Retorna erro tipado para mensagens distintas.
  - [ ] `get_couple(chat_id) -> Couple | None` e `get_partner(chat_id) -> User | None`.
  - [ ] `_gen_code()` — código curto sem caracteres ambíguos (sem O/0, I/1).

### 4.3 Handlers + comandos

- **`src/handlers/couple.py` (novo)**
  - [ ] `cmd_casal_convidar` → cria convite, mostra código + instrução.
  - [ ] `cmd_casal_entrar` (arg = código) → aceita; trata cada erro com mensagem
    própria; notifica os dois no sucesso.
  - [ ] `cmd_casal_status` → mostra com quem está pareado / como parear.
- **`src/main.py`**
  - [ ] Registrar `casal_convidar`, `casal_entrar`, `casal_status` e no menu
    `_BOT_COMMANDS`.
- **`src/utils/textos.py`**
  - [ ] Textos: convite gerado, sucesso, código inválido/expirado/usado, já
    pareado.

### 4.4 Testes (C2)

- [ ] `create_invite` gera código único; `accept_invite` cria o vínculo.
- [ ] Código expirado / já usado / usuário já pareado → erros distintos.
- [ ] Fluxo feliz: A convida, B entra, `get_partner` resolve dos dois lados.

### 4.5 Critério de aceitação

> A manda `/casal_convidar`, B manda `/casal_entrar <código>` no bot dele, e os
> dois recebem confirmação de que estão conectados.

---

## 5. Fase C3 — Tarefas compartilhadas

**Objetivo:** tarefas de casal visíveis/editáveis pelos dois; `/casal` real.

### 5.1 Modelo / migração

- **`src/db/models.py`**
  - [ ] `Task.couple_id` (FK nullable), `Task.created_by`, `Task.assigned_to`.
  - [ ] `TaskList.couple_id` (FK nullable).
- **`0005_couple_tasks.py`**
  - [ ] Adicionar colunas. **Data migration:** para cada usuário em um casal,
    converter a lista `is_couple=True` numa lista `couple_id`-scoped única e
    setar `couple_id` nas tarefas dela. Manter `is_couple` como legado ou dropar.

### 5.2 Serviço — filtro de visibilidade (RNF-01)

- **`src/services/task_service.py`**
  - [ ] Helper único `_visible_tasks_filter(user)`:
    `or_(Task.user_id == user.id, Task.couple_id == user.couple_id)`.
  - [ ] Aplicar em **todas** as funções de leitura de tarefas: `get_inbox_tasks`,
    `get_daily_summary_tasks`, `get_tomorrow_tasks`, `get_upcoming_tasks`,
    `search_tasks`, `get_all_open_tasks`, seleção do `/agora`, etc.
  - [ ] `get_couple_tasks` passa a filtrar por `Task.couple_id == couple.id`
    (não mais por lista `is_couple` de um usuário só).
  - [ ] Criação: `save_classified_tasks` / `create_task_in_list` aceitam destino
    casal → setam `couple_id` e `created_by`.

### 5.3 UX de captura/edição

- **`src/handlers/capture.py`**
  - [ ] No ajuste item-a-item, permitir escolher "📥 Casal" como destino
    (`kb_ajustar_tarefa` ganha a opção quando o usuário tem casal).
- **`src/handlers/common.py:227` (`cmd_casal`)**
  - [ ] Listar tarefas reais do casal com teclado de ação (concluir/editar),
    não enviar texto a grupo. Remover dependência de `couple_group_chat_id`.

### 5.4 Testes (C3)

- [ ] **Privacidade:** tarefa pessoal de A nunca aparece para B (teste explícito).
- [ ] A cria tarefa de casal → aparece para B; B edita → A vê a mudança.
- [ ] Data migration converte a lista `is_couple` legada corretamente.

### 5.5 Critério de aceitação

> A cria uma tarefa de casal; B a vê e edita; A vê a edição. Nenhuma tarefa
> pessoal cruza entre os dois.

---

## 6. Fase C4 — Sincronização ativa (notificações)

**Objetivo:** ação de um membro chega no bot do outro.

### 6.1 Multi-bot (arranjo B.1)

- **`src/config.py`**
  - [ ] `BOT_TOKENS: list[str]` (um por parceiro) além do token único legado.
- **`src/main.py`**
  - [ ] Construir um `Application` por token no mesmo event loop; registrar os
    mesmos handlers em cada; compartilhar o pool do DB.
  - [ ] Registro `chat_id -> Application` para resolver "o bot do parceiro".

### 6.2 Notificação

- **`src/services/couple_service.py`**
  - [ ] `partner_chat_id(chat_id)` para o destino da notificação.
- **`src/handlers/couple.py`** (ou um `notify.py`)
  - [ ] `notify_partner(event, task, actor)` — dispara
    `apps[partner].bot.send_message(...)` respeitando `is_paused(partner)` e
    horário. Eventos: criou, concluiu, reagendou, atribuiu.
- **Pontos de gatilho:** ao concluir/criar/reagendar tarefa **com `couple_id`**,
  chamar `notify_partner`.

### 6.3 Testes (C4)

- [ ] Resolver `partner_chat_id` dos dois lados.
- [ ] `notify_partner` respeita pausa do parceiro (não envia se pausado).

### 6.4 Critério de aceitação

> A conclui uma tarefa de casal e B recebe, no bot dele, "✅ Fulano concluiu …".

---

## 7. Fase C5 — Polimento de tom de casal

- [ ] `assigned_to` ("de quem é a vez") editável no detalhe da tarefa.
- [ ] Tom acolhedor nas notificações de casal (reforço positivo, nunca cobrança).
- [ ] Revisão semanal e lembretes de casal **deduplicados por `couple_id`**
  (não disparar 2x, uma por membro).
- [ ] Mensagens de casal respeitam pause/horário individual de cada um.

**Critério:** notificações de casal soam acolhedoras, não duplicam, e respeitam
o silêncio de cada um.

---

## 8. Fase C6 — Google Calendar (futuro)

Detalhe arquitetural em `08_ARQUITETURA_CASAL.md` §6. Resumo das tasks:

- [ ] **Endpoint OAuth:** subir um servidor web mínimo (aiohttp/FastAPI) para o
  callback — o bot hoje é long-polling sem web server.
- [ ] **Modelo:** `users.google_refresh_token` (criptografado),
  `users.google_calendar_id`, `couples.gcal_calendar_id`, `tasks.gcal_event_id`,
  `tasks.gcal_synced_at`.
- [ ] **Mão única (primeiro):** tarefa com `due_at` → cria/atualiza evento.
  Decidir destino de tarefa de casal (calendário pessoal de cada um vs.
  calendário compartilhado do casal).
- [ ] **Mão dupla (depois):** webhooks/push ou polling com sync token;
  resolução de conflito; mapeamento `task ↔ gcal_event_id`.
- [ ] Só tarefas com `due_at` viram evento (quadrante/energia não mapeiam).

> Fora do MVP segundo `CLAUDE.md`. Planejado para não fechar portas.

---

## 9. Resumo de arquivos por fase

| Fase | Novos | Alterados |
| --- | --- | --- |
| C1 | — | `config.py`, `handlers/common.py`, `handlers/config_handler.py`, `handlers/rituals.py`, `main.py`, `services/task_service.py`, `.env.example` |
| C2 | `services/couple_service.py`, `handlers/couple.py`, migration `0004` | `db/models.py`, `main.py`, `utils/textos.py` |
| C3 | migration `0005` | `db/models.py`, `services/task_service.py`, `handlers/capture.py`, `handlers/common.py`, `utils/keyboards.py` |
| C4 | (opc.) `handlers/notify.py` | `config.py`, `main.py`, `services/couple_service.py`, `handlers/couple.py` |
| C5 | — | `handlers/task_detail.py`, `handlers/rituals.py`, `utils/textos.py` |
| C6 | servidor OAuth, `services/gcal_service.py`, migration | `db/models.py`, `config.py`, `main.py` |

---

## 10. Riscos e mitigações

| Risco | Mitigação |
| --- | --- |
| Vazamento de pessoal entre parceiros (RNF-01) | Filtro de visibilidade único + teste explícito "pessoal nunca cruza". |
| Data migration da lista `is_couple` legada | Migration idempotente + teste; backup do banco antes do deploy da C3. |
| Jobs de casal disparando em duplicidade | Deduplicar por `couple_id` na C5. |
| `/reiniciar` (`os._exit`) derruba os dois `Application` (B.1) | Aceito; documentar. Migrar para B.2 se precisar isolamento. |
| Token OAuth Google vazando | Criptografia em repouso, client secret só em env, escopo mínimo. |
| Quebra do usuário de produção (RNF-07) | `AUTHORIZED_CHAT_ID` entra na allowlist; migrations retrocompatíveis; testar em staging. |

---

## 11. Ordem recomendada e "definição de pronto"

Implementar **C1 → C2 → C3 → C4 → C5**, uma por vez. C6 quando o casal estiver
estável. Cada fase só é "pronta" quando:

1. Testes unitários da fase passam (`pytest`).
2. Critério de aceitação da fase verificado manualmente com dois chats de teste.
3. Migration (se houver) aplica e reverte limpa em banco de teste.
4. Nenhuma regressão no fluxo mono-usuário existente.
