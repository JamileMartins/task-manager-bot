# Changelog — Task Manager Bot

Todas as mudanças notáveis estão documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Não lançado]

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
