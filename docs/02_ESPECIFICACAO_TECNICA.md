# Especificação Técnica — Bot "Task Manager"

> Versão 1.20.1 — documentação sincronizada com o código em 2026-06-02
> Companion do `01_PRD.md`

---

## 1. Stack recomendada e justificativa

| Camada | Escolha | Por quê |
| --- | --- | --- |
| Linguagem | **Python 3.11+** | Ecossistema maduro para bots e IA; fácil manutenção |
| Lib Telegram | **python-telegram-bot v21+** (async) | Padrão de mercado, suporte a botões inline, jobs agendados |
| Banco de dados | **PostgreSQL gerenciado (Supabase)** | Free tier generoso, backup automático, acesso de qualquer lugar, sem administrar servidor |
| ORM | **SQLAlchemy 2.x + Alembic** | Migrações versionadas, modelos limpos |
| IA | **Google Gemini API** (`google-genai`, modelo `gemini-2.5-flash`) | Interpretação de brain dump, classificação e transcrição de áudio |
| Agendamento | **APScheduler** (ou JobQueue do PTB) | Resumo diário, revisão semanal, lembretes |
| Hospedagem | **Railway** ou **Fly.io** (hobby) | Deploy via Git, 24/7, custo baixo/zero inicial |
| Config/segredos | **Variáveis de ambiente** (.env local, secrets na nuvem) | Não versionar tokens |

> **Por que Telegram resolve "celular + computador"**: o mesmo bot é acessível pelo app de celular, desktop e web do Telegram, todos sincronizados — não há necessidade de construir clientes próprios.

### 1.1 Alternativa de simplificação máxima

Se quiser evitar Postgres no início, é possível usar **SQLite** com um volume persistente na hospedagem. Porém, recomenda-se Supabase desde o MVP por causa de backup e acesso. A camada de ORM torna a troca trivial.

---

## 2. Arquitetura

```text
┌─────────────┐     webhook/polling      ┌──────────────────────┐
│   Telegram  │ <----------------------> │   Bot (Python/PTB)   │
│  (cliente)  │                          │  - handlers          │
└─────────────┘                          │  - conversação       │
                                         │  - jobs agendados    │
                                         └─────────┬────────────┘
                                                   │
                            ┌──────────────────────┼───────────────────────┐
                            │                      │                       │
                     ┌──────▼──────┐       ┌───────▼────────┐      ┌────────▼────────┐
                     │  Serviço    │       │  Serviço IA    │      │  Repositório    │
                     │  de Tarefas │       │ (Gemini API)   │      │ (SQLAlchemy)    │
                     └─────────────┘       └────────────────┘      └────────┬────────┘
                                                                            │
                                                                      ┌──────▼──────┐
                                                                      │ PostgreSQL  │
                                                                      │ (Supabase)  │
                                                                      └─────────────┘
```

### 2.1 Camadas

- **Handlers (apresentação)**: recebem updates do Telegram, montam botões inline, despacham para serviços.
- **Serviços (domínio)**: regras de negócio — captura, classificação, seleção "o que faço agora", rituais.
- **Repositório (dados)**: acesso ao banco via SQLAlchemy.
- **Cliente IA**: encapsula chamadas ao Gemini, com prompt, few-shots, parsing robusto, transcrição de áudio e fallback.

### 2.2 Polling vs Webhook

- **MVP**: long polling (mais simples, sem precisar de URL pública configurada).
- **Evolução**: webhook quando hospedado com domínio/HTTPS estável (menor latência, menos consumo).

---

## 3. Modelo de dados

### 3.1 Diagrama lógico

```text
User (1) ───< (N) List
User (1) ───< (N) Task
List (1) ───< (N) Task
Task (1) ───< (N) Reminder
Config (1 por User)
Couple (1) ───< (N) CoupleMember >─── (1) User
Couple (1) ───< (N) Task
Couple (1) ───< (N) Invite
```

### 3.2 Tabelas

#### users

| Campo | Tipo | Notas |
| --- | --- | --- |
| id | UUID PK | |
| telegram_chat_id | BIGINT unique | único autorizado (RNF10) |
| name | TEXT | |
| timezone | TEXT | ex. "America/Fortaleza" |
| created_at | TIMESTAMPTZ | |
| google_refresh_token | TEXT nullable | OAuth Google Calendar, opcional |
| google_calendar_id | TEXT nullable | calendário pessoal, opcional |

#### lists

| Campo | Tipo | Notas |
| --- | --- | --- |
| id | UUID PK | |
| user_id | UUID FK | |
| name | TEXT | ex. "Trabalho" |
| slug | TEXT | normalizado p/ comandos |
| is_couple | BOOLEAN | marca a lista exportável p/ grupo |
| couple_id | UUID FK nullable | legado/escopo de lista compartilhada |
| archived | BOOLEAN | default false |
| sort_order | INT | |

#### tasks

| Campo | Tipo | Notas |
| --- | --- | --- |
| id | UUID PK | |
| user_id | UUID FK | |
| list_id | UUID FK nullable | null = Inbox |
| couple_id | UUID FK nullable | não-nulo = tarefa compartilhada do casal |
| created_by | UUID FK nullable | usuário que criou a tarefa de casal |
| assigned_to | UUID FK nullable | dono da vez numa tarefa de casal |
| couple_joint | BOOLEAN nullable | true = tarefa conjunta |
| title | TEXT | obrigatório |
| notes | TEXT nullable | |
| quadrant | SMALLINT nullable | 1–4 (Eisenhower); null = não classificado |
| due_at | TIMESTAMPTZ nullable | prazo |
| recurrence | TEXT nullable | 'daily' \| 'weekly' \| 'monthly' \| null |
| estimate_min | INT nullable | minutos estimados |
| energy | TEXT nullable | 'alta' \| 'media' \| 'baixa' |
| status | TEXT | 'aberta' \| 'aguardando' \| 'concluida' \| 'arquivada' |
| blocker_type | TEXT nullable | 'vaga_grande' \| 'decisao_pendente' \| 'aversiva_energia' \| 'pessoa' \| 'recurso_info' \| 'data_externa' \| 'obsoleta' \| null |
| blocker_note | TEXT nullable | detalhe livre ("esperando docs do contador") |
| blocker_is_external | BOOLEAN nullable | true = externo (espera+gatilho); false = interno (resolver agora) |
| next_step | TEXT nullable | menor próximo passo sugerido pela IA |
| parent_task_id | UUID FK nullable | vínculo de subtarefa (primeiro passo / obter recurso) |
| blocked_by_task_id | UUID FK nullable | dependência explícita de outra tarefa |
| waiting_since | TIMESTAMPTZ nullable | quando entrou em "aguardando"; alimenta a revisão de esperas longas |
| due_alerted | BOOLEAN nullable | evita repetir alerta de prazo vencido |
| category | TEXT nullable | subcategoria, ex. `medicacao` ou `agendamento` |
| gcal_event_id | TEXT nullable | evento espelhado no Google Calendar |
| gcal_synced_at | TIMESTAMPTZ nullable | última sincronização com Calendar |
| sort_order | INT | ordenação manual na lista |
| created_at | TIMESTAMPTZ | |
| completed_at | TIMESTAMPTZ nullable | |
| last_touched_at | TIMESTAMPTZ | p/ revisão semanal (parada há N dias) |

#### reminders

| Campo | Tipo | Notas |
| --- | --- | --- |
| id | UUID PK | |
| task_id | UUID FK | |
| remind_at | TIMESTAMPTZ | |
| sent | BOOLEAN | default false |

#### config

| Campo | Tipo | Notas |
| --- | --- | --- |
| user_id | UUID PK FK | |
| daily_summary_time | TIME | ex. 08:00 |
| weekly_review_dow | SMALLINT | dia da semana (0–6) |
| weekly_review_time | TIME | |
| couple_group_chat_id | BIGINT nullable | grupo p/ exportar casal |
| stale_days | INT | default 7 (parada há N dias) |
| stale_waiting_days | INT | default 14 (espera longa: aguardando há M dias) |
| energia_do_dia | TEXT nullable | energia escolhida no resumo diário |
| energia_do_dia_data | DATE nullable | data da energia escolhida |
| paused_until | TIMESTAMPTZ nullable | pausa temporária dos jobs automáticos |

#### couples

| Campo | Tipo | Notas |
| --- | --- | --- |
| id | UUID PK | |
| created_at | TIMESTAMPTZ | |
| gcal_calendar_id | TEXT nullable | calendário compartilhado opcional |

#### couple_members

| Campo | Tipo | Notas |
| --- | --- | --- |
| couple_id | UUID FK PK | |
| user_id | UUID FK PK | |
| role | TEXT | default `member` |
| joined_at | TIMESTAMPTZ | |

#### invites

| Campo | Tipo | Notas |
| --- | --- | --- |
| code | TEXT PK | código curto de pareamento |
| couple_id | UUID FK | casal criado/reaproveitado |
| created_by | UUID FK | criador do convite |
| created_at | TIMESTAMPTZ | |
| expires_at | TIMESTAMPTZ | convite expira em 24h |
| used_by | UUID FK nullable | usuário que aceitou |

---

## 4. Serviço de IA (classificação do brain dump)

### 4.1 Responsabilidade

Receber um texto livre e devolver uma lista estruturada de tarefas com campos sugeridos.

### 4.2 Contrato de saída (JSON)

A IA deve responder **somente** JSON, com este formato:

```json
{
  "tarefas": [
    {
      "titulo": "Comprar ração do gato",
      "lista_sugerida": "Casa (solo)",
      "quadrante_sugerido": 3,
      "prazo_sugerido": null,
      "estimativa_min": 15,
      "energia": "baixa",
      "impedimento": null,
      "impedimento_externo": false,
      "proximo_passo": null,
      "confianca": 0.9
    }
  ]
}
```

Campo `impedimento`: um dos tipos (`vaga_grande`, `decisao_pendente`, `aversiva_energia`, `pessoa`, `recurso_info`, `data_externa`, `obsoleta`) ou `null` se não detectado. Quando `impedimento_externo` for `true`, o serviço cria a tarefa já em status `aguardando`. `proximo_passo` traz o menor passo acionável quando o impedimento for `vaga_grande` (ou quando útil).

### 4.3 Regras de robustez

- Forçar resposta apenas-JSON via instrução de sistema explícita.
- Fazer parsing seguro; se falhar, salvar o texto inteiro como **uma** tarefa na Inbox (RNF08).
- `confianca < limiar` (ex. 0.6) → mandar para Inbox em vez de lista, marcando p/ triagem.
- Uma única chamada por brain dump (custo — RNF07).
- Datas relativas resolvidas no fuso do usuário (`config.timezone`).

### 4.4 Esboço de prompt (sistema)

> O prompt completo de produção (system prompt, regras de cada campo, exemplos few-shot, parsing e pós-processamento) está em **`docs/04_PROMPT_CLASSIFICACAO_IA.md`**. O resumo abaixo serve de referência rápida.
>
> Você é um classificador de tarefas para um sistema pessoal de produtividade voltado a uma pessoa com TDAH. Receberá um texto livre que pode conter uma ou várias tarefas. Separe em tarefas atômicas e, para cada uma, sugira: lista (entre as listas existentes do usuário, fornecidas abaixo), quadrante de Eisenhower (1–4), prazo (se houver indício de data), estimativa de tempo em minutos e nível de energia (alta/media/baixa). Detecte também impedimentos: se o texto indicar que a tarefa depende de outra pessoa, de um recurso/informação que falta, de uma data futura, de uma decisão ainda não tomada, ou que é grande/vaga ou aversiva, preencha `impedimento` com o tipo apropriado e marque `impedimento_externo` como true quando depender de terceiros/recursos/datas. Quando a tarefa for grande ou vaga, preencha `proximo_passo` com a menor ação física acionável (algo que leve ≤ 2 minutos para começar). Responda SOMENTE com JSON no formato especificado, sem texto adicional. Listas disponíveis: {listas}. Data/hora atual: {agora} no fuso {timezone}.

### 4.5 Sugestão de próximo passo (sob demanda)

Quando a usuária aciona "estou travada nessa" ou escolhe o impedimento `vaga_grande`, o serviço faz uma chamada focada ao Gemini pedindo apenas o menor próximo passo acionável (≤ 2 min) para aquela tarefa específica, retornando uma frase curta no imperativo. O passo vira uma subtarefa vinculada (`parent_task_id`).

### 4.6 Manejo do estado "aguardando"

- Ao mudar uma tarefa para `aguardando`, gravar `waiting_since = now()`.
- Ao desbloquear (voltar para `aberta`), limpar `waiting_since` e atualizar `last_touched_at`.
- "Seguir esperando" na revisão reinicia `waiting_since = now()`.
- A revisão de esperas longas seleciona `status = 'aguardando' AND waiting_since < now() - stale_waiting_days`.

---

## 5. Lógica "o que faço agora"

Entrada: `tempo_disponivel` (min) e `energia_atual`.
Seleção entre tarefas **abertas** (status `aberta`; nunca `aguardando`):

1. Filtra `estimate_min <= tempo_disponivel` (tarefas sem estimativa entram como candidatas neutras).
2. Filtra por energia compatível (energia da tarefa ≤ energia atual; baixa cabe em qualquer estado).
3. Ordena por: quadrante (Q1 < Q2 < Q3 < Q4), depois `due_at` mais próximo, depois `sort_order`.
4. Retorna a primeira. Botões: Concluí / Outra / Adiar / **Estou travada**.

Ao tocar em **Outra** ou **Estou travada**, dispara o fluxo de impedimento (seção 6.6 do PRD): o bot pergunta o que está impedindo e aplica a estratégia de desbloqueio. Tarefas que entram em `aguardando` saem da fila do `/agora`.

Se nada casar, sugerir a menor/mais leve tarefa disponível com mensagem acolhedora.

---

## 6. Jobs agendados

| Job | Quando | Ação |
| --- | --- | --- |
| daily_summary | `config.daily_summary_time` (por fuso) | Envia focos do dia |
| weekly_review | `weekly_review_dow` + hora | Inicia fluxo de revisão: tarefas paradas + esperas longas (`aguardando` há > `stale_waiting_days`) |
| reminders_tick | a cada 1 min | Envia lembretes, desbloqueia tarefas `aguardando` por data e alerta prazo vencido ainda não avisado |
| medication_rollover | diário 00:01 por usuário | Descarta medicações não tomadas e agenda a próxima ocorrência sem acúmulo |
| recurrence_roll | ao concluir tarefa recorrente | Recria a próxima ocorrência |

---

## 7. Estrutura de pastas sugerida

```tree
foco-bot/
├── docs/
│   ├── 01_PRD.md
│   ├── 02_ESPECIFICACAO_TECNICA.md
│   └── 03_HISTORIAS_DE_USUARIO.md
├── src/
│   ├── main.py                 # bootstrap do bot
│   ├── config.py               # carrega env vars
│   ├── db/
│   │   ├── models.py           # SQLAlchemy
│   │   ├── session.py
│   │   └── migrations/         # Alembic
│   ├── handlers/
│   │   ├── capture.py          # brain dump + texto livre
│   │   ├── tasks.py            # ver/editar/concluir
│   │   ├── lists.py            # gerenciar listas
│   │   ├── agora.py            # /agora
│   │   ├── rituals.py          # diário, semanal, lembretes e medicações
│   │   └── couple.py           # /casal
│   ├── services/
│   │   ├── task_service.py
│   │   ├── ai_service.py       # cliente Gemini + prompt + áudio
│   │   ├── couple_service.py   # pareamento de casal
│   │   └── gcal_service.py     # motor Google Calendar opcional
│   └── utils/
│       ├── dates.py            # parsing de datas PT-BR
│       └── keyboards.py        # botões inline
├── tests/
├── .env.example
├── requirements.txt
├── README.md
└── CLAUDE.md
```

---

## 8. Variáveis de ambiente (.env.example)

```text
TELEGRAM_BOT_TOKEN=
BOT_TOKENS=
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname?sslmode=require
AUTHORIZED_CHAT_ID=          # chat_id da usuária (RNF10)
ALLOWED_CHAT_IDS=            # CSV opcional de outros chats autorizados
DEFAULT_TIMEZONE=America/Fortaleza
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=
```

---

## 9. Plano de fases

| Fase | Entregas |
| --- | --- |
| **F1 — Núcleo de captura** | Modelos, captura texto livre → Inbox, listar, concluir. Sem IA ainda. |
| **F2 — IA + classificação** | Brain dump multi-tarefa, classificação Gemini, aprovação em bloco. |
| **F3 — Priorização** | Quadrante assistido, edição de atributos, /agora. |
| **F4 — Rituais** | Resumo diário, revisão semanal, lembretes, recorrência. |
| **F5 — Casal + polimento** | Exportar casal p/ grupo, /config, busca, tom acolhedor. |
| **F6+ — Pós-MVP implementado** | Captura por voz, medicações, foco, multiusuário/casal real, dependência entre tarefas, `/ordem`, `/progresso`, fundação Google Calendar. |

---

## 10. Testes (mínimos)

- Unitários: parsing de datas PT-BR; lógica de seleção "/agora"; parsing do JSON da IA (incl. JSON malformado → fallback).
- Integração: criação/conclusão de tarefa ponta a ponta; job de lembrete.
- Manual: fluxo de brain dump com texto real; revisão semanal.

---

## 11. Segurança

### 11.1 Gestão de segredos

- **Nunca** versionar segredos. O `.gitignore` bloqueia `.env`, chaves e credenciais; apenas `.env.example` (com placeholders vazios) é versionado.
- Em desenvolvimento: segredos no arquivo `.env` local (fora do Git).
- Em produção (Railway/Fly.io): segredos como **secrets/variáveis de ambiente da plataforma**, nunca no código nem em logs.
- Tokens cobertos: `TELEGRAM_BOT_TOKEN`, `BOT_TOKENS`, `GEMINI_API_KEY`, `DATABASE_URL` e credenciais OAuth do Google.
- Rotação: se um segredo vazar, revogar e gerar novo no provedor (BotFather, Google AI Studio/Cloud Console, Supabase) e atualizar o secret na plataforma. `AUTHORIZED_CHAT_ID`/`ALLOWED_CHAT_IDS` não são segredos, mas não devem ir para logs públicos.

### 11.2 Criptografia em trânsito

- **Telegram ↔ bot**: a API do Telegram é exclusivamente HTTPS/TLS; o tráfego é cifrado por padrão.
- **Bot ↔ Google Gemini**: HTTPS/TLS via SDK `google-genai`.
- **Bot ↔ PostgreSQL (Supabase)**: exigir conexão com **SSL/TLS** (`sslmode=require` na `DATABASE_URL` ou parâmetro equivalente). Não conectar sem TLS.
- **Webhook (se adotado na evolução)**: somente sobre HTTPS com certificado válido; validar o `secret_token` do webhook do Telegram.

### 11.3 Criptografia em repouso

- **Banco gerenciado (Supabase)**: criptografia em repouso provida pela plataforma (discos cifrados) + backups gerenciados. É o motivo de preferir Supabase a um SQLite solto.
- **Dados sensíveis do conteúdo**: as tarefas podem conter informação pessoal (saúde, casa, trabalho). Para a instância privada atual, a criptografia em repouso do provedor é suficiente. **Não** implementar criptografia de campo no MVP (complexidade desnecessária para o escopo atual), mas registrar como evolução possível caso o conteúdo de saúde se torne sensível demais.
- **Sem armazenamento local de conteúdo** além do necessário; não logar o corpo das tarefas em logs de aplicação.

### 11.4 Controle de acesso

- O bot responde **apenas** ao `AUTHORIZED_CHAT_ID` (RNF10). Toda mensagem de outro `chat_id` é ignorada com resposta neutra (ver textos §11.2).
- Exceção: o grupo de casal (`couple_group_chat_id`) **recebe** envios, mas **não comanda** o bot — mensagens vindas do grupo não disparam ações.
- Validar sempre a origem do update antes de processar comandos.

### 11.5 Dados pessoais e privacidade

- Princípio de **minimização**: não coletar dados além de tarefas e configurações.
- A `GEMINI_API_KEY` envia o texto das tarefas e, quando usado, áudio para a API Google Gemini para classificação/transcrição — isso é inerente ao funcionamento. Documentar isso para a usuária (é a própria dona dos dados, mas vale registrar a consciência do fluxo).
- Não compartilhar dados com terceiros além do estritamente funcional (Telegram, Google Gemini, banco e Google Calendar quando ativado).
- Backups: confiar no backup gerenciado do Supabase; não exportar dumps para locais não cifrados.

### 11.6 Boas práticas de código (checklist)

- [ ] `.env` no `.gitignore` e ausente do histórico do Git.
- [ ] Nenhum segredo hardcoded; tudo via `config.py` lendo variáveis de ambiente.
- [ ] `DATABASE_URL` com SSL exigido.
- [ ] Logs não contêm tokens nem corpo de tarefas.
- [ ] Dependências atualizadas (sem versões com CVE conhecido).
- [ ] Tratamento de erro não vaza stack trace para o usuário (ver textos §11.3).
- [ ] Validação de `chat_id` em todo handler.
