# CLAUDE.md — Guia para desenvolvimento do Bot "Task Manager"

> Este arquivo orienta o Claude Code no desenvolvimento deste projeto.
> Leia também `docs/01_PRD.md`, `docs/02_ESPECIFICACAO_TECNICA.md` e `docs/03_HISTORIAS_DE_USUARIO.md` antes de codar.

## O que é este projeto

Bot de Telegram chamado **Task Manager**: um "segundo cérebro" de tarefas, mono-usuário, projetado para reduzir atrito e apoiar funções executivas de uma pessoa com TDAH. Captura por texto livre (brain dump), classificação assistida por IA (Google Gemini API), priorização via Matriz de Eisenhower, sugestão ativa de "o que fazer agora", e rituais de revisão (diário e semanal).

## Princípios de design (não violar)

1. **Atrito mínimo**: ações comuns em 1–2 toques. Texto livre é o caminho principal; comandos são atalhos.
2. **Menos microdecisões**: classificar em lote e aprovar em bloco. A IA sugere, a usuária confirma.
3. **Uma coisa de cada vez**: `/agora` entrega UMA tarefa, nunca uma lista longa.
4. **Tom acolhedor**: nunca culpar por acúmulo ou tarefas paradas. Reforço positivo ao concluir.
5. **Nada se perde**: se a IA falhar, salvar na Inbox. Banco com persistência confiável.
6. **Tudo em Português do Brasil**: interface, mensagens e comentários de domínio.

## Stack

- Python 3.11+, `python-telegram-bot` v21+ (async).
- PostgreSQL (Supabase) via SQLAlchemy 2.x + Alembic.
- Google Gemini API para classificação.
- APScheduler (ou JobQueue) para jobs.
- Hospedagem: Railway/Fly.io. MVP usa long polling.

## Convenções de código

- Arquitetura em camadas: `handlers/` (Telegram) → `services/` (domínio) → `db/` (dados). Handlers não acessam o banco direto; passam por serviços.
- Funções de serviço são testáveis sem o Telegram (sem dependência de `Update`).
- Datas sempre com timezone-aware (`America/Fortaleza` por padrão). Nunca usar datetime naive.
- Segredos só via variáveis de ambiente. Nunca commitar `.env` nem tokens. O `.gitignore` já bloqueia `.env`, chaves e credenciais — confirme que continua assim. Conexão ao banco sempre com SSL/TLS (`sslmode=require`). Validar `chat_id` em todo handler. Nunca logar tokens nem o corpo das tarefas. Detalhes completos em `docs/02_ESPECIFICACAO_TECNICA.md` §11.
- O cliente de IA deve isolar prompt + parsing; resposta da IA é sempre validada como JSON, com fallback para Inbox.
- Mensagens ao usuário ficam centralizadas (módulo `utils/textos.py`) para manter tom consistente e PT-BR. **Todos os textos prontos, com tom e variações, estão em `docs/05_TEXTOS_DO_BOT.md` — use-os como fonte ao implementar.**

## Ordem de implementação (fases)

- **F1 — Núcleo**: modelos + migrações; captura texto livre → Inbox; listar; concluir; restrição de chat_id. (US-01, US-05, US-06, US-13, US-21)
- **F2 — IA**: brain dump multi-tarefa; classificação Claude; aprovação em bloco; triagem Inbox. (US-02, US-03, US-04)
- **F3 — Priorização**: quadrante assistido; editar atributos; prazo/tempo/energia; `/agora`. (US-07 a US-12)
- **F4 — Rituais**: resumo diário; revisão semanal; lembretes; recorrência. (US-14 a US-18)
- **F5 — Casal + polimento**: exportar casal p/ grupo; `/config`; busca; refino de tom. (US-19, US-20, US-22)

Implemente uma fase por vez. Ao final de cada fase, rode os testes e confirme os critérios de aceitação das histórias daquela fase.

## Modelo de dados (resumo)

Tabelas: `users`, `lists`, `tasks`, `reminders`, `config`. Detalhes completos em `docs/02_ESPECIFICACAO_TECNICA.md` seção 3. Pontos-chave:

- `tasks.list_id` nulo = Inbox.
- `tasks.quadrant` 1–4 (Eisenhower), nulo = não classificado.
- `tasks.energy` em {alta, media, baixa}; `tasks.estimate_min` em minutos.
- `tasks.last_touched_at` alimenta a revisão semanal (parada há N dias).
- `tasks.status` inclui `aguardando` (tarefa com impedimento externo, fora do radar ativo).
- `tasks.blocker_type` (vaga_grande, decisao_pendente, aversiva_energia, pessoa, recurso_info, data_externa, obsoleta) + `blocker_note`, `blocker_is_external`, `next_step`, `parent_task_id` para subtarefas.

## Impedimentos (regra central)

Tarefa parada tem causa nomeável. O sistema distingue impedimento **interno** (resolver agora: quebrar em próximo passo, ou virar "decidir X") de **externo** (sair do radar: status `aguardando` + gatilho de retomada por data ou cobrança). O bot pergunta o impedimento na revisão semanal, ao pular no `/agora` e sob demanda. Para `vaga_grande`, a IA sempre sugere o menor próximo passo (≤ 2 min) como subtarefa. Tarefas `aguardando` nunca aparecem no `/agora` nem nos focos do dia. A revisão semanal tem uma seção de **esperas longas**: tarefas `aguardando` há mais de `stale_waiting_days` (padrão 14), com opções cobrar/desbloquear/arquivar/seguir esperando. Gravar `waiting_since` na entrada do estado e limpar ao desbloquear. Detalhes em `docs/01_PRD.md` §3.6 e §6.6.

## Contrato do serviço de IA

A IA recebe texto livre + listas existentes + data/fuso e responde **somente JSON**:

```json
{"tarefas":[{"titulo":"...","lista_sugerida":"...","quadrante_sugerido":1,"prazo_sugerido":null,"estimativa_min":15,"energia":"baixa","impedimento":null,"impedimento_externo":false,"proximo_passo":null,"confianca":0.9}]}
```

Regras: uma chamada por brain dump; parsing seguro; `confianca` baixa → Inbox; falha → salvar texto como uma tarefa na Inbox. **O prompt completo de produção, com regras de cada campo, exemplos few-shot e pós-processamento, está em `docs/04_PROMPT_CLASSIFICACAO_IA.md` — leia antes de implementar a F2.**

## Lógica "/agora"

Pergunta tempo e energia; filtra por `estimate_min <= tempo` e energia compatível; ordena por quadrante (Q1→Q4), depois `due_at`, depois `sort_order`; retorna UMA. Sem candidatas, sugere a mais leve com mensagem gentil. (Detalhe na spec, seção 5.)

## Comandos

Texto livre = captura. `/agora`, `/listas`, `/ver <lista>`, `/inbox`, `/hoje`, `/casal`, `/buscar <termo>`, `/config`, `/ajuda`.

## Qualidade

- Escreva testes unitários para: parsing de datas PT-BR, seleção do `/agora`, parsing do JSON da IA (inclusive malformado → fallback).
- Não introduza dependências pesadas sem necessidade.
- Prefira clareza a esperteza; este projeto será mantido por uma só pessoa.

## O que NÃO fazer no MVP

- Multi-usuário/colaboração real.
- Geolocalização ou atributo de "local".
- Integração com Google Calendar/Notion/Todoist.
- Cliente web/mobile próprio.
- Transcrição de áudio/anexos.

## Setup local (resumo)

1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. Copie `.env.example` para `.env` e preencha tokens. (O `.env` está no `.gitignore` — nunca o versione. Use `DATABASE_URL` com SSL exigido.)
4. `alembic upgrade head`
5. `python -m src.main`
