# Changelog — Task Manager Bot

Todas as mudanças notáveis estão documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Não lançado]

## [1.22.1] — 2026-06-13 — Editar janela de tempo + ajuda

### Adicionado

- **Editar a janela de tempo de listas existentes**: no menu ⚙️ de uma lista (em `/listas`) há o botão **🗓️ Janela de tempo**, que abre um submenu para alternar entre Sem janela / Diária / Semanal / Mensal (com ✓ na atual).
- Comando `/ajuda` agora explica a janela de tempo das listas e as opções de recorrência (incluindo a quinzenal).

## [1.22.0] — 2026-06-13 — Janela de tempo por lista + recorrência quinzenal

### Adicionado

- **Janela de tempo por lista**: ao criar uma lista, dá pra escolher se ela mostra tudo (padrão) ou só as tarefas de um período — **diária**, **semanal** ou **mensal**. Listas com janela filtram pelas tarefas do período (pela data), com as tarefas **sem data fixadas no topo**, e trazem navegação **◀ ▶** entre períodos (ex.: navegar entre os meses numa lista "Financeiro"). Nova coluna `lists.view_window` (migração 0010).
- **Recorrência quinzenal** por botão no detalhe da tarefa, junto de Diária/Semanal/Mensal — repete a cada 14 dias.

### Mantido

- A lista de medicações continua com comando e comportamento próprios, sem alteração.

## [1.21.0] — 2026-06-13 — Autoria nas tarefas do casal

### Adicionado

- A lista de tarefas compartilhadas do casal (`/casal` e botão "ver casal") agora exibe, abaixo de cada tarefa, quem a cadastrou (primeiro nome) e a data/hora de criação no fuso de Fortaleza-CE — ex.: `✍️ Jamile · 12/06 às 14:30`. Tarefas antigas sem criador registrado mostram só a data.

## [1.20.1] — 2026-06-02 — Ajustes do /progresso de casal

### Corrigido

- `/progresso` agora exibe a seção de casal mesmo quando não há listas pessoais com atividade.
- Breakdown de casal usa o primeiro nome dos dois membros, com contagens por "minhas", parceiro, conjuntas e sem dono.
- `/progresso [dias]` aceita janela customizada e limita valores muito altos.

## [1.20.0] — 2026-06-02 — Datas futuras e tooltips

### Adicionado

- Presets de prazo futuro e opção de digitar data customizada no detalhe da tarefa.
- Tooltips/textos auxiliares nos controles de edição para reduzir ambiguidade.

### Corrigido

- Movimento de tarefa trata duplicata de título no destino e melhora mensagens de erro em `BadRequest`.
- Stats de casal em `/progresso` usam `couple_id`, não `list_id`.

## [1.19.0] — 2026-06-02 — /progresso

### Adicionado

- **`/progresso`** substitui `/projetos` como visão de progresso por lista.
- Todas as listas ativas entram no relatório, com período explícito e breakdown de casal.
- `/projetos` permanece como alias legado.

### Corrigido

- Horário BRT no `/ajuda`.
- `/casal` registrado no menu de comandos.

## [1.18.0] — 2026-06-02 — /ordem

### Adicionado

- **`/ordem`** exibe cadeias de dependência em ordem de execução.
- Cadeias mostram tarefas prontas e bloqueadas com botões clicáveis e detecção de ciclos no serviço.

## [1.17.0] — 2026-06-02 — Dependência entre tarefas

### Adicionado

- Novo impedimento por tarefa bloqueadora: uma tarefa pode ficar `aguardando` por depender de outra.
- Campo `tasks.blocked_by_task_id` e migration `0009`.
- Ao concluir uma tarefa bloqueadora, dependentes são destravadas automaticamente.
- Detalhe da tarefa mostra "bloqueada por" e "desbloqueia".
- Nota livre no fluxo de impedimento e entrada pelo `/agora`.

## [1.16.0] — 2026-06-02 — Saúde e classificação

### Adicionado

- `tasks.category` separa medicações de agendamentos na lista Saúde.
- Backfill de medicações existentes via migration `0008`.

### Melhorado

- Separação de tarefas no brain dump, incluindo listas com verbo implícito.
- Robustez de transcrição de áudio via Gemini Files API.
- Medicações recorrentes usam horários/dias corretos e evitam acúmulo entre dias.
- `/amanha` inclui recorrentes ainda abertas hoje.

## [1.15.0] — 2026-05-26 — /proximos, /pausar, /projetos e streak semanal

### Adicionado

- **`/proximos [N]` (Sugestão #5)** — agenda dos próximos N dias (padrão 7, máx 30), tarefas agrupadas por data com hora, estimativa e lista. Cobre o gap entre `/amanha` (1 dia) e uma visão de semana completa.
- **`/pausar [dias]` + `/retomar` (Sugestão #7)** — silencia todos os jobs automáticos (resumo diário, revisão semanal, lembretes de prazo) por N dias (padrão 1, máx 90). Campo `paused_until` em `config`; `/retomar` limpa imediatamente.
- **Streak semanal no fechamento da revisão (Sugestão #10)** — ao fechar a revisão semanal, `msg_revisao_encerramento` exibe quantos dos últimos 7 dias tiveram tarefas concluídas, com tom progressivo (🌱 / 🔥).
- **`/projetos` (2e-7)** — visão de progresso por lista: barra textual `●●●○○○○○`, contagem `concluídas/total (30d)`, tarefas abertas e data do último toque. Listas sem atividade ficam ocultas.

### Corrigido

- **`msg_exportar` usava `group.list_name`** — campo inexistente em `TaskGroup`; corrigido para `group.name`.

### Infraestrutura

- Migration `0003`: coluna `paused_until` (DateTime with timezone) em `config`.
- 13 novos testes: `get_upcoming_tasks` (4), `is_paused`/`pause_bot`/`resume_bot` (5), `get_projetos` (4). 342 total.

## [1.14.0] — 2026-05-26 — Energia do dia, prazo vencido, /exportar e /foco

### Adicionado

- **Check-in de energia no resumo matinal (Sugestão #1)** — bom dia envia botões `⚡ Alta / 🔋 Média / 🪫 Baixa`; escolha salva em `config.energia_do_dia`. O `/agora` usa esse valor como padrão durante o dia, pulando a pergunta de energia enquanto a data for a mesma.
- **Lembrete de prazo vencido (Sugestão #4)** — `send_reminders` detecta tarefas abertas com `due_at` no passado e ainda não alertadas; envia notificação gentil com opções "📅 Adiar 1 dia", "👀 Ver tarefa" e "🗑️ Arquivar". Campo `due_alerted` evita repetição.
- **`/exportar` (Sugestão #8)** — lista todas as tarefas abertas em texto plano copiável, agrupadas por lista com separador, prazo e símbolo ⏳ para `aguardando`.
- **`/foco [work] [break]`** — Pomodoro configurável (padrão 50 + 15 min). Agenda timers reais via JobQueue. Notifica ao fim do trabalho com botões descanso/pular; notifica ao fim do descanso com botões novo ciclo/encerrar. `/parar_foco` cancela a sessão ativa a qualquer momento.

### Infraestrutura

- Migration `0002`: colunas `energia_do_dia` e `energia_do_dia_data` em `config`; `due_alerted` em `tasks`.
- 6 novos testes: energia do dia e prazo vencido. 329 total.

## [1.13.0] — 2026-05-26 — Subtarefas no detalhe e edição de título

### Adicionado

- **Subtarefas visíveis no detalhe (Sugestão #6)** — tarefa com subtarefas abertas exibe seção "📌 Próximos passos" com título e estimativa de cada uma. Botão `✅ <subtarefa>` em cada item conclui a subtarefa e refresca o detalhe sem sair da tela.
- **Editar título de tarefa (Sugestão #9)** — botão `✏️ Título` no detalhe abre ConversationHandler simples: envia o novo texto → salvo em até 500 caracteres. Elimina a necessidade de arquivar e recriar uma tarefa para corrigir erro de digitação.
- `get_subtasks(task_id)` — retorna subtarefas abertas de uma tarefa-pai em ordem de sort/criação.
- `kb_cancelar(task_id)` — teclado genérico de cancelamento reutilizável.
- `title_conversation` e `cb_sub_complete` em `handlers/task_detail.py`.
- Campo `"title"` adicionado ao whitelist de `update_task_attrs`.
- 5 novos testes para `get_subtasks`; 1 para edição de título; 1 teste existente corrigido.

## [1.12.0] — 2026-05-26 — Histórico de conquistas

### Adicionado

- **`/conquistas`** — mostra tarefas concluídas hoje, ontem, nos últimos 7 dias e quantos dias produtivos houve na semana. Tom de reforço positivo gradual.
- **Blurb no resumo matinal** — quando há conclusões de ontem, o bom-dia começa com "Ontem você concluiu X tarefas ✅" antes dos focos do dia.
- `get_conquistas(chat_id)` — função de serviço retornando `{hoje, ontem, semana, dias_ativos}`.
- `msg_conquistas(stats)` e `msg_conquistas_diario(ontem)` em `utils/textos.py`.
- 6 novos testes unitários cobrindo todos os cenários de conquistas.

## [1.11.0] — 2026-05-26 — Nota em tarefa existente

### Adicionado

- **Nota em tarefa (Sugestão #2)** — botão `📝 Nota` no detalhe de qualquer tarefa abre um ConversationHandler: a usuária envia o texto e ele é salvo no campo `notes`. Nota exibida no detalhe com `📝`. Botão mostra `✓` quando já existe nota.
- `kb_nota(task_id, has_notes)` — teclado inline com `🗑️ Apagar nota` (se houver nota) e `✖️ Cancelar`.
- `msg_nota_pergunta`, `MSG_NOTA_SALVA`, `MSG_NOTA_APAGADA` em `utils/textos.py`.
- `note_conversation` — ConversationHandler em `handlers/task_detail.py`, registrado antes de `list_conversation` em `main.py`.
- Campo `"notes"` adicionado ao whitelist de `update_task_attrs`.
- 3 novos testes unitários cobrindo salvar, apagar e sobrescrever nota.

## [1.10.0] — 2026-05-26 — Correções de lacunas e polimento

### Corrigido

- **`/tudo` exibia medicações do dia seguinte** — tarefas recorrentes com `due_at` depois de hoje ficam ocultas; só aparecem quando chegar a data delas (`get_all_open_tasks`).
- **Lembrete da cobrança (US-25) nunca era salvo** — `cb_blocker_cobrar_date` calculava `remind_at` mas não persistia. `create_related_task` agora aceita `due_at` e o `Reminder` é criado corretamente.
- **`aversiva_energia` não reduzia estimativa** — se `estimate_min > 30`, o valor é dividido pela metade (mínimo 15 min) para tornar a tarefa mais acessível. Mensagem reformulada com dica de parear com algo agradável.

### Adicionado

- **Desbloqueio automático por data (US-28 CA)** — `get_due_waiting_tasks()` detecta tarefas `aguardando` cujo `due_at` passou; o job `send_reminders` (a cada minuto) as desbloqueia automaticamente e notifica a usuária.
- **Comando `/ver <lista>`** — abre qualquer lista pelo nome ou parte do nome (ex.: `/ver trabalho`, `/ver casa`). Busca por slug exato → slug contém → nome contém.

### Infraestrutura

- Markdownlint corrigido em `CLAUDE.md` (MD031, MD032) e `README.md` (MD060).
- 19 novos testes unitários cobrindo as funções adicionadas/corrigidas.

---

## [1.9.0] — 2026-05-26 — /hoje e /amanhã

### Adicionado

- **`/hoje`** — exibe prazos do dia e até 3 focos Q1/Q2, com hora e estimativa. Comando que já estava no `/ajuda` mas sem handler implementado.
- **`/amanha`** — lista tarefas com prazo no dia seguinte, ordenadas por hora, com lista e estimativa.
- `task_service.get_tomorrow_tasks()` — query para o janela de amanhã no fuso da usuária.
- Novas mensagens `MSG_HOJE_VAZIO` e `MSG_AMANHA_VAZIO` com tom acolhedor.

---

## [1.8.0] — 2026-05-26 — Transcrição de áudio via Gemini

### Adicionado

- **Captura por voz:** mensagens de voz (e arquivos de áudio) enviados ao bot são transcritos pelo Gemini e entram no fluxo normal de brain dump — mesmo resumo, mesma aprovação em bloco.
- Transcrito exibido antes da classificação: `🎙️ Ouvi: "..."` para que a usuária possa verificar o que foi capturado.
- Fallback explícito se transcrição falhar ou retornar vazio: `MSG_AUDIO_ERRO` pede para digitar.
- `ai_service.transcrever_audio()` — chamada Gemini multimodal com `inline_data` para OGG/OPUS e outros formatos de áudio.
- `handlers/audio.py` — handler independente registrado antes do catch-all de texto.
- `capture.process_text_capture()` — lógica de captura extraída em função pública reutilizável.

---

## [1.7.0] — 2026-05-26 — Medicações: horário, dia da semana e histórico

### Adicionado

- **Horário aproximado por medicação:** fluxo de criação pergunta o horário (ex: `08:00`) após o nome; exibido com ⏰ no `/medicacoes`. Campo é preservado nas renovações automáticas.
- **Dia da semana para medicações semanais:** recorrência semanal agora inclui o dia (`weekly:N`); fluxo de criação apresenta botões Seg–Dom. Exibido como "• Citobê — Terça ⏰ 20:00".
- **Histórico de tomadas do dia:** `/medicacoes` exibe seção "✅ Tomadas hoje" com horário exato de cada medicação concluída no dia.
- **Número de versão:** aparece no `/ajuda` e na mensagem do `/reiniciar`.

### Corrigido

- `complete_task` agora gera próxima ocorrência correta para recorrências no formato `weekly:N`.
- Migração Alembic com múltiplos heads (`001` e `0001`) removida; mantido apenas `0001_initial_schema` com verificações idempotentes.

### Infraestrutura

- `src/version.py` centraliza `__version__` consumido pelos textos do bot.

---

## [1.6.0] — 2026-05-26 — F6: Captura direta, visão geral e medicações

### Adicionado

- **US-30** — Botão `➕ Adicionar` na tela de qualquer lista: cria tarefa diretamente sem passar pela IA, com confirmação e botão desfazer.
- **US-31** — Comando `/tudo`: exibe todas as tarefas abertas agrupadas por lista (Inbox primeiro). Tarefas `aguardando` aparecem com ⏳. Se total > 30, limita a 5 por grupo.
- **US-32** — Comando `/medicacoes`: checklist de medicações diárias e semanais da lista Saúde, com botão ✅ por item e fluxo guiado `➕ Nova medicação` (nome → frequência).

### Infraestrutura

- Alembic configurado com migração inicial (`0001_initial_schema`); startup usa `alembic upgrade head`.

### Renomeado

- Bot renomeado de "Foco" para "Task Manager".

---

## [1.5.0] — 2026-05-25 — F5: Casal, busca e polimento

### Adicionado

- **US-19** — Comando `/casal`: envia tarefas da lista Casa (casal) para o grupo configurado.
- **US-19** — Comando `/setgrupo`: registra o grupo do Telegram como destino das tarefas de casal.
- **US-22** — Comando `/buscar <termo>`: busca por palavra-chave no título e nas notas de todas as tarefas ativas.

### Corrigido

- **US-29** — `cb_rev_wait_seguir` agora reinicia o contador `waiting_since` ao escolher "Seguir esperando" na revisão.

### Melhorado

- Substituído "Jamile" por "usuária" em todos os textos e fallbacks do código.
- Referências à API do Claude corrigidas para Google Gemini API.

---

## [1.4.0] — 2026-05 — F4: Rituais, impedimentos e recorrência

### Adicionado

- **US-15** — Resumo diário automático com tarefas do dia e focos Q1/Q2.
- **US-16** — Revisão semanal automática: tarefas paradas há N dias com opções reagendar / arquivar / manter.
- **US-17** — Lembretes por horário via `due_at` (job a cada minuto).
- **US-18** — Recorrência de tarefas (diária, semanal, mensal): ao concluir, cria automaticamente a próxima ocorrência.
- **US-20** — Comando `/config`: horário do resumo diário e dia/hora da revisão semanal.
- **US-23–28** — Fluxo completo de impedimentos: identifica causa (vaga_grande, decisão_pendente, aversiva, pessoa, recurso, data_externa, obsoleta) e encaminha para próximo passo ou status `aguardando`.
- **US-29** — Revisão de esperas: tarefas `aguardando` há mais de N dias aparecem em seção separada com opções cobrar / destravar / arquivar / seguir esperando.
- Comando `/quadrantes`: guia da Matriz de Eisenhower e níveis de energia.

---

## [1.3.0] — 2026-05 — F3: Priorização e /agora

### Adicionado

- **US-07** — Detalhe de tarefa com edição inline de quadrante, energia, tempo estimado, prazo e recorrência.
- **US-08** — Edição de quadrante (Q1–Q4) direto no detalhe.
- **US-09** — Edição de energia (alta / média / baixa).
- **US-10** — Edição de estimativa de tempo (5 / 15 / 30 / 60 / 120 min).
- **US-11** — Definição de prazo (hoje / amanhã / sem prazo) e reordenação (↑ ↓).
- **US-12** — Comando `/agora`: filtra por tempo e energia, retorna UMA tarefa sugerida.

---

## [1.2.0] — 2026-05 — F2: Classificação por IA

### Adicionado

- **US-02** — Brain dump: múltiplas tarefas em uma mensagem, separadas e classificadas pela IA (Google Gemini).
- **US-03** — Aprovação em bloco: "✅ Aprovar tudo" ou ajuste item a item.
- **US-04** — Triagem da Inbox: itens com baixa confiança ficam na Inbox para organização manual.

---

## [1.1.0] — 2026-05 — F1: Núcleo

### Adicionado

- **US-01** — Captura de tarefa em texto livre → Inbox automático.
- **US-05** — Listagem de listas com contagem de tarefas abertas.
- **US-06** — Criar, renomear e arquivar listas.
- **US-13** — Concluir tarefa com botão ✅; desfazer com ↩️.
- **US-21** — Restrição de acesso por `chat_id` autorizado.
- Comando `/start`, `/ajuda`, `/inbox`, `/listas`, `/ping`, `/reiniciar`.
- Deploy no Railway com PostgreSQL (Supabase).

---

## [1.0.0] — 2026-05 — Estrutura inicial

### Adicionado

- Scaffolding do projeto: estrutura de pastas, modelos SQLAlchemy, sessão com pool, configuração Railway.
- Modelos: `users`, `lists`, `tasks`, `reminders`, `config`.
- Documentação inicial: PRD, especificação técnica, histórias de usuário, prompt de IA, textos do bot.
