# Arquitetura — Modo Casal e Multiusuário

> Documento de arquitetura do modo casal (dois usuários), com tarefas compartilhadas, autenticação por
> convite e fundação para sincronização opcional com Google Calendar.
>
> Status: implementado em base, com Google Calendar opcional em fundação. Complementa `01_PRD.md` §6 e
> `02_ESPECIFICACAO_TECNICA.md`.

---

## 1. Contexto e diagnóstico

O bot começou mono-usuário, mas a implementação atual já usa allowlist e banco
multiusuário.
O que prende o sistema a uma pessoa é apenas a *casca* de autorização, não o
modelo de dados nem a lógica de domínio.

**Já é multiusuário (não precisa mudar):**

- `users` é keyed por `telegram_chat_id`; todo `task`, `list` e `config` tem FK
  para `user_id` (`src/db/models.py`).
- Os serviços sempre resolvem o usuário por `chat_id`
  (`select(User).where(User.telegram_chat_id == chat_id)`). A lógica de domínio
  já é "por usuário".

**O que prende em uma pessoa só:**

- `AUTHORIZED_CHAT_ID` — único env var, comparado em todo handler por
  `is_authorized()` (`src/handlers/common.py:25`).
- `setup_jobs(app, AUTHORIZED_CHAT_ID)` — jobs agendados rodam para um chat só
  (`src/main.py:314`).
- `cmd_setgrupo` grava `couple_group_chat_id` sempre em `AUTHORIZED_CHAT_ID`
  (`src/handlers/common.py:262`).

**O "casal" atual é um espelho read-only:**

- Uma lista com `is_couple=True` ainda pertence a **uma** pessoa (`user_id`).
- `/casal` (`src/handlers/common.py:227`) gera um **texto** e empurra para um
  grupo do Telegram via `couple_group_chat_id`. O parceiro **lê um dump**; não
  edita nada. Não existe tarefa compartilhada de verdade.

**Conclusão:** o trabalho real não é "tornar multiusuário" (o schema já é). É
**(a)** abrir o portão de autorização, **(b)** criar a entidade "casal" com
tarefas de propriedade compartilhada, e **(c)** sincronizar/notificar entre dois
chats distintos.

---

## 2. A decisão: um bot ou dois?

A pergunta "um bot ou dois bots" mistura dois eixos **independentes**:

| Eixo | Opção A | Opção B |
| --- | --- | --- |
| Token/processo do Telegram | 1 bot para os dois | 2 bots (cada um tem "o dele") |
| Backend / banco de dados | 1 backend compartilhado | 2 backends separados |

**Regra inegociável:** compartilhar dados exige um **backend/DB único**. "Dois
backends separados" nunca sincroniza tarefa de casal. Logo a escolha real é só
no eixo de cima: **um bot para os dois, ou um bot para cada um — ambos sobre o
mesmo banco.**

### Opções avaliadas

- **A — Bot único multi-inquilino:** os dois falam com o mesmo bot. Mais simples
  de operar, sincronização trivial. Mas **não** atende ao desejo de "cada um ter
  a versão dele".
- **B — Um bot por pessoa, backend compartilhado (RECOMENDADA):** mesmo código,
  dois tokens, um Postgres. Pessoal isolado por `user_id`; casal numa entidade
  `couple` compartilhada. Atende ao pedido, mantém uma única base de código,
  escala para mais gente.
- **C — Dois bots pessoais + um "bot do casal" (3 bots):** rejeitada. Triplica
  deploy/estado e força o usuário a pular entre bots — viola o princípio de
  **atrito mínimo**. Tarefa de casal e pessoal vivem no mesmo fluxo mental;
  separá-las em apps diferentes cria fricção onde o TDAH penaliza mais.

### Decisão

**Opção B.** O problema não é transporte (Telegram), é **dado compartilhado +
identidade**. Não criar um segundo bot dedicado ao casal: criar uma **camada de
dados compartilhada** que ambos os bots leem e escrevem.

---

## 3. Modelo de dados

Hoje a propriedade de uma tarefa é `task.user_id` (dono único). Para
compartilhar, a tarefa precisa poder pertencer a um **casal**.

### 3.1 Novas tabelas

```text
couples
  id            uuid pk
  created_at    timestamptz
  -- (futuro) gcal_calendar_id text  -- calendário Google compartilhado

couple_members
  couple_id     uuid fk -> couples.id
  user_id       uuid fk -> users.id
  role          text          -- 'member' (espaço para futuro)
  joined_at     timestamptz
  PK (couple_id, user_id)      -- 2 linhas = o casal

invites                        -- autenticação / pareamento (ver §5)
  code          text pk        -- token curto, ex. "AB7K9Q"
  couple_id     uuid fk -> couples.id
  created_by    uuid fk -> users.id
  expires_at    timestamptz
  used_by       uuid fk -> users.id  NULL
```

### 3.2 Alterações em `tasks` e `lists`

```text
tasks.couple_id   uuid fk -> couples.id  NULL     -- não-nulo = tarefa do casal
tasks.created_by  uuid fk -> users.id             -- quem criou (auditoria/tom)
tasks.assigned_to uuid fk -> users.id  NULL       -- "de quem é a vez" (opcional)
lists.couple_id   uuid fk -> couples.id  NULL     -- lista compartilhada
```

### 3.3 Regra de visibilidade (ponto crítico de privacidade)

- `couple_id IS NULL` → tarefa **pessoal**, visível só para `user_id`
  (comportamento atual, intacto).
- `couple_id = X` → tarefa **do casal**, visível/editável por **ambos** os
  membros de X.

As queries hoje filtram `Task.user_id == user.id`. Passam a usar um único helper
centralizado:

```python
def _visible_tasks_filter(user):
    return or_(
        Task.user_id == user.id,            # minhas pessoais
        Task.couple_id == user.couple_id,   # do nosso casal
    )
```

> **Risco nº 1 — vazamento de privacidade.** Pessoal de A nunca pode aparecer
> para B. Este filtro precisa estar em **um lugar só**, com testes unitários
> cobrindo "tarefa pessoal nunca cruza casal".

`is_couple` na lista é substituído por `couple_id`: a lista "Casa (casal)" de
cada usuário é migrada para uma lista única `couple_id`-scoped, e suas tarefas
ganham `couple_id`.

> **Nota sobre migrações:** o Alembic **está** implementado (migrations
> `0001`–`0003`, `run_migrations()` roda no boot). As colunas novas são uma
> migration normal.

---

## 4. Sincronização e notificação entre os dois bots

Com dois tokens, quando A conclui uma tarefa de casal, **B precisa saber**. Como
o backend é único:

1. A edita via bot-A → serviço grava no Postgres (fonte única da verdade).
2. O serviço identifica: "tarefa de casal, outro membro é B (chat_id Y)".
3. Dispara `bot_B.send_message(chat_id=Y, "✅ Fulano concluiu 'comprar presente'")`.

Para o passo 3, o processo precisa de acesso aos dois tokens. Dois sub-arranjos:

- **B.1 — Um processo, dois `Application` (recomendado para começar):** o mesmo
  `python -m src.main` cria dois `Application.builder().token(...)`, um por
  parceiro, no mesmo event loop, compartilhando o pool do DB. Notificar o
  parceiro é `apps[other].bot.send_message(...)`. Um deploy só no Railway.
- **B.2 — Dois processos separados:** cada bot é um deploy. Para A notificar B,
  ou chama a Bot API do token de B direto, ou usa um canal interno (tabela
  `outbox` com poll, ou Postgres `LISTEN/NOTIFY`). Mais robusto, mais peças.
  Migrar para cá só se quiser deploys independentes.

**Decisão:** começar com **B.1**.

UX: notificação de casal respeita `paused_until` e horários de cada um
individualmente (reaproveita o que já existe).

---

## 5. Autenticação / pareamento

Não é preciso OAuth nem senha para o Telegram: o `chat_id` **já é** a identidade
autenticada. Falta só **vincular dois chat_ids num casal** com segurança.

### 5.1 Fluxo de pareamento (uma vez)

1. A manda `/casal_convidar` → backend cria um `invite` (novo `couple` + código
   curto `AB7K9Q`, expira em ~24h).
2. Bot mostra: *"Mande este código para o seu par: **AB7K9Q**. Ele entra com
   /casal_entrar AB7K9Q."*
3. B manda `/casal_entrar AB7K9Q` no bot **dele** → backend valida (existe? não
   expirou? não usado? B já não está em outro casal?), cria `couple_members`
   para B, marca o invite como usado.
4. Os dois recebem: *"💞 Vocês estão conectados. Tarefas de casal agora aparecem
   para os dois."*

### 5.2 Substituindo `AUTHORIZED_CHAT_ID`

A regra deixa de ser "este chat é o único permitido" e passa a ser **allowlist
de chat_ids registrados**:

- **Curtíssimo prazo:** `ALLOWED_CHAT_IDS` (lista no env). `is_authorized()` vira
  `chat_id in allowed` — mudança de uma linha. Suficiente para 2 pessoas
  conhecidas.
- **Feature de verdade:** registro via `/start` + pareamento por convite (acima).

---

## 6. Sincronização com Google Calendar

Status em 2026-06-02: o motor de sincronização mão única (`gcal_service.py`) e
o modelo de dados já existem e são testados. A ativação ao vivo ainda depende de
cliente real, OAuth e endpoint HTTPS de callback; por padrão o serviço é no-op
seguro quando as credenciais/client factory não estão configurados.

Não é um problema de arquitetura — a base proposta (backend único, entidade
casal, `due_at` já timezone-aware) é compatível e não exige retrabalho. Mas é o
**maior subsistema novo** do roadmap, por três motivos que afetam decisões
**agora**:

### 6.1 Autenticação é diferente de tudo que existe

No Telegram o `chat_id` já é identidade de graça. O Google exige **OAuth 2.0 por
usuário**: link de consentimento, callback HTTPS e armazenamento do *refresh
token* (sensível — criptografar em repouso, client secret só via env).

O bot hoje é long-polling **sem servidor web**. Será preciso subir um endpoint
pequeno (aiohttp/FastAPI) só para o callback do OAuth. O Railway hospeda isso.

Tabelas/colunas previstas:

```text
users.google_refresh_token   text  NULL   -- criptografado
users.google_calendar_id     text  NULL   -- calendário pessoal alvo
couples.gcal_calendar_id     text  NULL   -- calendário compartilhado do casal
tasks.gcal_event_id          text  NULL   -- mapeamento task -> evento
tasks.gcal_synced_at         timestamptz NULL
```

### 6.2 A pergunta do casal reaparece

Tarefa de casal vai para o calendário **de quem**? Três opções, todas
dependentes do modelo `couple`:

- calendário pessoal de cada membro (evento duplicado nos dois);
- um **calendário Google compartilhado** do casal (`couples.gcal_calendar_id`);
- ambos.

Por isso a entidade `couples` já reserva espaço para um calendário associado. A
decisão pode ficar para depois, mas o modelo não trava.

### 6.3 Mão única é fácil; mão dupla é o custo real

- **Bot → Calendar** (criar/atualizar evento a partir de tarefa com `due_at`):
  simples. Recomendado como primeira entrega.
- **Calendar → Bot** (detectar edição feita no Google): exige *webhooks/push* ou
  polling com *sync token*, mapeamento `task ↔ gcal_event_id` e resolução de
  conflito.

Só tarefas com `due_at` viram evento — o que já bate com o modelo atual.
Quadrante, energia e estimativa não mapeiam para o calendário.

> A integração Google Calendar ao vivo segue opcional; a fundação está pronta
> para ativação conforme `docs/10_ATIVACAO_GOOGLE_CALENDAR.md`.
> Esta seção é planejamento arquitetural para não fechar portas, não escopo
> imediato.

---

## 7. Roadmap de implementação (fases)

Seguindo a convenção de fases do `CLAUDE.md`:

- **C1 — Destravar multiusuário (base):** trocar `AUTHORIZED_CHAT_ID` por
  allowlist; `setup_jobs` itera sobre todos os usuários registrados;
  `cmd_setgrupo`/config deixam de assumir o id único. Sem feature nova.
  *Critério: dois chats de teste convivem sem vazar dados.*
- **C2 — Entidade casal + pareamento:** migration (`couples`, `couple_members`,
  `invites`, colunas `couple_id`); `/casal_convidar` e `/casal_entrar`.
  *Critério: A e B viram um casal.*
- **C3 — Tarefas compartilhadas:** helper de visibilidade; captura, edição,
  `/agora`, `/casal` passam a enxergar tarefas `couple_id`. Migrar a lista "Casa
  (casal)". *Critério: A cria, B vê e edita, A vê a edição.*
- **C4 — Sincronização ativa:** notificar o parceiro em eventos de casal (criou,
  concluiu, mudou prazo) via arranjo B.1. *Critério: ação de A chega no bot de B.*
- **C5 — Polimento de tom de casal:** `assigned_to` ("de quem é a vez"), tom
  acolhedor nas notificações, respeitar pause/horário de cada um.
- **C6 — Google Calendar:** motor bot → Calendar mão única implementado;
  endpoint OAuth/cliente real ficam para ativação quando necessário.

---

## 8. Riscos e pontos de atenção

1. **Vazamento de privacidade (maior risco).** Pessoal de A nunca aparece para
   B. Mitigação: filtro de visibilidade num único helper, com testes unitários.
2. **Concorrência:** os dois editando a mesma tarefa de casal. Volume baixíssimo
   para um casal; `last_touched_at` + "última escrita vence" basta. Não inventar
   locking.
3. **Estado em memória:** `context.user_data` (captura) já é por-chat no PTB,
   naturalmente isolado por pessoa. OK.
4. **Jobs duplicados:** ao iterar usuários nos jobs, garantir que a revisão
   semanal de casal não dispare 2x. Lembretes de casal deduplicados por
   `couple_id` ou "pertencentes" a um membro.
5. **`/reiniciar` com `os._exit`** (`src/handlers/common.py:220`) derruba o
   processo; com dois `Application` no mesmo processo (B.1), reinicia os dois
   bots. Aceitável — ficar ciente.

---

## 9. Resumo

Não fazer um segundo bot para o casal: o problema é **dado compartilhado +
identidade**, não transporte. Manter **um bot por pessoa rodando o mesmo código
sobre um Postgres único**, adicionar uma entidade `couple` com tarefas de
visibilidade compartilhada, autenticar por **convite com código** (o `chat_id`
já é a identidade) e notificar o parceiro pelo bot dele a partir do backend
comum. O Google Calendar encaixa depois como um subsistema OAuth, sem retrabalho
da base.
