# PRD — Bot de Tarefas "Task Manager" (Telegram)

> Documento de Requisitos do Produto (Product Requirements Document)
> Versão 1.0 — MVP
> Autoria: especificação técnica para desenvolvimento via Claude Code
> Sistema mono-usuário (bot particular).

---

## 1. Visão geral

**Task Manager** é um bot de Telegram que funciona como um "segundo cérebro" para captura e organização de tarefas, projetado especificamente para reduzir o atrito de uso e apoiar funções executivas de uma pessoa com TDAH.

O princípio central é: **capturar deve ser instantâneo; organizar deve ser opcional e assistido por IA; decidir o que fazer agora deve ser guiado, não exigir esforço de priorização do usuário.**

### 1.1 Problema

Pessoas com TDAH costumam ter dificuldade em três pontos do fluxo de tarefas:

1. **Captura** — uma ideia ou compromisso surge e precisa ser registrado antes de ser esquecido, sem fricção.
2. **Organização e priorização** — categorizar, estimar e priorizar exige função executiva, que é justamente o ponto de dificuldade.
3. **Início e acompanhamento** — paralisia diante de listas longas; tarefas viram um "cemitério" sem revisão.

### 1.2 Solução

Um bot de Telegram que:

- Aceita captura em linguagem natural ("brain dump"), inclusive múltiplas tarefas numa única mensagem.
- Usa a Google Gemini API para interpretar, separar e pré-classificar as tarefas automaticamente, pedindo só uma confirmação em bloco.
- Organiza tarefas em listas/contextos personalizáveis.
- Aplica a Matriz de Eisenhower de forma assistida (a IA sugere o quadrante; o usuário confirma com um toque).
- Sugere ativamente "o que fazer agora" com base em tempo disponível e energia.
- Mantém rituais de revisão (resumo diário matinal e revisão semanal anti-acúmulo).
- Exporta as tarefas de "casal" para um grupo do Telegram.

### 1.3 Objetivos do MVP

| # | Objetivo | Métrica de sucesso |
| --- | --- | --- |
| O1 | Captura sem atrito | Registrar uma tarefa em ≤ 1 mensagem, sem comandos obrigatórios |
| O2 | Classificação automática | ≥ 80% das tarefas de um brain dump classificadas corretamente sem edição manual |
| O3 | Reduzir paralisia | Comando "o que faço agora" retorna 1 tarefa sugerida |
| O4 | Anti-acúmulo | Resumo diário e revisão semanal funcionando |
| O5 | Disponibilidade | Bot acessível 24/7 de celular e computador (via Telegram) |

### 1.4 Fora de escopo (MVP)

- Multi-usuário / colaboração real (sistema é mono-usuário).
- Lembretes por geolocalização.
- Atributo de "local" nas tarefas.
- Integração com calendários externos (Google Calendar etc.) — previsto para fase futura.
- Aplicativo web/mobile próprio (o Telegram é a interface).
- Anexos de arquivos/áudio com transcrição (fase futura).

---

## 2. Público e persona

### Persona única — usuária

- Professora com rotina intensa e viagens frequentes.
- TDAH, com dificuldade em funções executivas (organizar, priorizar, iniciar).
- Usa Telegram com frequência (alta familiaridade).
- Precisa acessar de celular e de computador (resolvido nativamente pelo Telegram).
- Valoriza baixíssimo atrito: se exigir muitos passos, não vai usar.

---

## 3. Conceitos e modelo mental

### 3.1 Listas / contextos

Agrupam tarefas por área de vida. Personalizáveis (criar, renomear, arquivar). Listas iniciais sugeridas:

- **Trabalho** - coisas relacionadas às atividades de trabalho.
- **Projetos** - coisas relacionadas à projeto pessoais
- **Casa (solo)** — coisas de casa que faço sozinha
- **Casa (casal)** — coisas de casa do casal (exportáveis para grupo)
- **Saúde** - agendamentos médicos, exames, medicações, etc.
- **Ideias** — captura de ideias, não necessariamente acionáveis

### 3.2 Caixa de entrada (Inbox)

Toda captura cai primeiro numa Inbox. A IA tenta classificar na lista correta; o usuário aprova em bloco. Tarefas não classificadas com confiança ficam na Inbox para triagem.

### 3.3 Atributos de tarefa

- **Título** (texto curto, obrigatório)
- **Lista/contexto** (uma)
- **Prioridade** via Matriz de Eisenhower → quadrante (Q1 a Q4)
- **Ordenação manual** dentro da lista
- **Data/prazo** (opcional)
- **Recorrência** (opcional: diária, semanal, mensal)
- **Estimativa de tempo** (opcional: ex. 5, 15, 30, 60, 120 min)
- **Nível de energia** (alta / média / baixa)
- **Status** (aberta, aguardando, concluída, arquivada/adiada)
- **Notas** (texto livre opcional)
- **Impedimento** (opcional): tipo do bloqueio + nota livre
- **Próximo passo** (opcional): menor ação acionável sugerida pela IA
- **Tarefa-pai** (opcional): vínculo de subtarefa para o primeiro passo / obtenção de recurso

### 3.4 Matriz de Eisenhower

Cada tarefa pode receber um quadrante:

- **Q1 — Urgente + Importante**: fazer agora.
- **Q2 — Importante, não urgente**: agendar.
- **Q3 — Urgente, não importante**: delegar/minimizar.
- **Q4 — Nem urgente nem importante**: eliminar/talvez.

A classificação é **assistida**: a IA sugere o quadrante (com base em prazo, palavras-chave e lista) e o usuário confirma ou ajusta com um toque (botões inline).

### 3.5 Técnicas de gestão de tempo aplicadas

- **Matriz de Eisenhower** — priorização por quadrante.
- **Time-boxing / estimativa** — campo de tempo estimado, usado na sugestão "o que faço agora".
- **Energy management** — campo de energia, para casar tarefa com o estado atual.
- **"One thing at a time"** — a sugestão ativa entrega **uma** tarefa por vez, reduzindo paralisia.
- **Revisão periódica (estilo GTD)** — resumo diário e revisão semanal.
- **Próxima ação física (GTD)** — toda tarefa travada é reduzida ao menor passo acionável.

### 3.6 Impedimentos (bloqueios)

Tarefa parada raramente é "preguiça": quase sempre há um **impedimento** não nomeado. O sistema trata o impedimento como atributo de primeira classe, não como nota solta, e associa a cada tipo uma **estratégia de desbloqueio**.

**Impedimentos internos (dependem só da usuária — resolvem-se agindo/decidindo agora):**

| Tipo | Sinal típico | Estratégia de desbloqueio |
| --- | --- | --- |
| `vaga_grande` | "não sei por onde começar" | IA sugere o **menor próximo passo** (≤ 2 min) e cria como tarefa filha |
| `decisao_pendente` | "preciso decidir antes" | Transforma "decidir X" na verdadeira primeira tarefa |
| `aversiva_energia` | chata, ansiogênica, cansativa | Rebaixa estimativa, sugere parear/agendar em horário de pico de energia |

**Impedimentos externos (dependem de terceiros/recursos/tempo — resolvem-se saindo do radar ativo + criando gatilho de retomada):**

| Tipo | Sinal típico | Estratégia de desbloqueio |
| --- | --- | --- |
| `pessoa` | "esperando fulano" | Escolha na hora: status **aguardando** (some do radar) **ou** vira tarefa "cobrar fulano" com lembrete |
| `recurso_info` | falta dado/material/acesso | Cria subtarefa "obter recurso X" |
| `data_externa` | só pode ser feita após uma data | Define `due_at` e remove do radar até lá |

**Caso honesto:** se a tarefa **não importa mais** (`obsoleta`), a melhor resolução é **arquivar sem culpa**.

**Distinção interno × externo** é central: impedimento interno aparece para ser resolvido *agora* (quebrar/decidir); externo é movido para um estado de espera com gatilho de retomada, para não poluir o radar ativo nem a revisão semanal.

**Quando o bot pergunta sobre impedimento:** na revisão semanal, ao pular uma tarefa no `/agora` ("Outra"), e sob demanda ("estou travada nessa"). Além disso, o brain dump detecta dependências e já marca a tarefa como `aguardando` quando identifica um impedimento externo na captura.

---

## 4. Requisitos funcionais (RF)

| ID | Requisito | Prioridade |
| --- | --- | --- |
| RF01 | O usuário pode enviar uma mensagem de texto livre e o bot registra como tarefa(s). | Must |
| RF02 | O bot detecta múltiplas tarefas numa só mensagem (brain dump) e as separa. | Must |
| RF03 | O bot pré-classifica cada tarefa em uma lista usando a Google Gemini API. | Must |
| RF04 | O bot mostra um resumo do que foi capturado/classificado e permite aprovar em bloco ou corrigir. | Must |
| RF05 | O usuário pode criar, renomear e arquivar listas. | Must |
| RF06 | O usuário pode ver as tarefas de uma lista, ordenadas por quadrante/ordem manual. | Must |
| RF07 | O usuário pode marcar tarefa como concluída. | Must |
| RF08 | O usuário pode editar atributos de uma tarefa (lista, data, energia, tempo, quadrante, notas). | Must |
| RF09 | A IA sugere o quadrante de Eisenhower e o usuário confirma/ajusta com botões. | Must |
| RF10 | O usuário pode definir data/prazo para uma tarefa. | Must |
| RF11 | O usuário pode definir recorrência simples (diária/semanal/mensal). | Should |
| RF12 | O usuário pode definir estimativa de tempo e nível de energia. | Must |
| RF13 | Comando "o que faço agora": o bot pergunta tempo disponível e energia atual e sugere UMA tarefa. | Must |
| RF14 | Resumo diário matinal: o bot envia os focos do dia (Q1/Q2 e tarefas com prazo hoje). | Must |
| RF15 | Revisão semanal: o bot lista tarefas paradas e oferece reagendar/arquivar uma a uma. | Must |
| RF16 | O usuário pode exportar/enviar as tarefas da lista "Casa (casal)" para um grupo do Telegram. | Should |
| RF17 | O bot envia lembretes por horário para tarefas com data/hora definida. | Should |
| RF18 | O usuário pode buscar tarefas por palavra-chave. | Could |
| RF19 | O usuário pode adiar uma tarefa ("amanhã", "próxima semana") com um toque. | Should |
| RF20 | O bot reconhece datas em linguagem natural ("amanhã 15h", "sexta"). | Should |
| RF21 | O usuário pode registrar um impedimento para uma tarefa, escolhendo um tipo (vaga/grande, decisão pendente, aversiva, pessoa, recurso/info, data externa, obsoleta). | Must |
| RF22 | O bot pergunta sobre impedimento em três momentos: revisão semanal, ao pular tarefa no /agora, e sob demanda ("estou travada nessa"). | Must |
| RF23 | Para impedimento "vaga/grande", a IA sugere automaticamente o menor próximo passo (≤ 2 min) e o cria como subtarefa. | Must |
| RF24 | Para impedimento "decisão pendente", o bot cria uma tarefa "decidir X" como primeira ação. | Should |
| RF25 | Para impedimento "pessoa", o usuário escolhe na hora entre status "aguardando" (some do radar) ou criar tarefa "cobrar fulano" com lembrete. | Must |
| RF26 | Para impedimento "recurso/info", o bot cria subtarefa "obter recurso X". | Should |
| RF27 | Tarefas em status "aguardando" não aparecem no /agora nem nos focos do dia, mas reaparecem na revisão e por gatilho (data/cobrança). | Must |
| RF28 | O brain dump detecta dependências na captura e marca a tarefa como "aguardando" quando identifica impedimento externo. | Should |
| RF29 | O usuário pode resolver um impedimento (desbloquear), retornando a tarefa ao status "aberta". | Must |
| RF30 | A revisão semanal inclui uma seção de "esperas longas": tarefas em status "aguardando" há mais de N dias, oferecendo para cada uma: cobrar agora, desbloquear, arquivar ou seguir esperando. | Should |
| RF31 | A tela de uma lista tem botão "➕ Adicionar" que cria tarefa naquela lista diretamente, sem passar pela classificação IA. | Must |
| RF32 | Comando `/tudo` exibe todas as tarefas abertas agrupadas por lista, em uma única mensagem. | Should |
| RF33 | Comando `/medicacoes` exibe tarefas recorrentes (diárias e semanais) da lista Saúde com botões de conclusão rápida, e oferece fluxo guiado para criar nova medicação com recorrência. | Should |

---

## 5. Requisitos não-funcionais (RNF)

| ID | Requisito |
| --- | --- |
| RNF01 | **Baixo atrito**: ações comuns (capturar, concluir, "o que faço agora") em no máximo 1–2 toques. |
| RNF02 | **Disponibilidade 24/7** em hospedagem na nuvem. |
| RNF03 | **Persistência confiável**: nenhuma tarefa pode ser perdida; banco com backup. |
| RNF04 | **Idioma**: toda a interface em Português do Brasil. |
| RNF05 | **Privacidade**: dados acessíveis apenas pela usuária; tokens/segredos fora do código. |
| RNF06 | **Latência**: resposta de captura simples em < 2s; classificação por IA em < 6s. |
| RNF07 | **Custo baixo**: uso de camadas gratuitas/baratas (Supabase free, Railway/Fly hobby). |
| RNF08 | **Resiliência da IA**: se a Google Gemini API falhar, a tarefa ainda é salva na Inbox sem classificação. |
| RNF09 | **Tom de voz**: mensagens acolhedoras, sem culpabilizar por acúmulo (relevante p/ TDAH). |
| RNF10 | **Restrição de acesso**: o bot responde apenas ao chat_id autorizado da usuária. |

---

## 6. Fluxos principais

### 6.1 Brain dump (captura + classificação)

1. Usuária envia: *"comprar ração, marcar dentista, ideia: curso de bordado, pagar luz até sexta"*.
2. Bot chama a Google Gemini API → separa em 4 tarefas e sugere lista + quadrante + prazo de cada uma.
3. Bot responde com um resumo numerado e botões: **✅ Aprovar tudo** | **✏️ Ajustar**.
4. Em "Aprovar tudo", as tarefas são salvas. Em "Ajustar", a usuária corrige item a item.

### 6.2 O que faço agora

1. Usuária toca em /agora (ou botão).
2. Bot pergunta (botões): tempo disponível (5/15/30/60+) e energia (alta/média/baixa).
3. Bot escolhe UMA tarefa que caiba no tempo e energia, priorizando Q1 > Q2, prazo próximo e ordem manual.
4. Botões: **✅ Concluí** | **⏭️ Outra** | **😴 Adiar**.

### 6.3 Resumo diário

- Em horário configurado (ex. 8h), bot envia: tarefas com prazo hoje + até 3 focos sugeridos (Q1/Q2).

### 6.4 Revisão semanal

- Em dia/horário configurado, bot lista tarefas abertas há mais de N dias sem ação e oferece, uma a uma: **Reagendar | Arquivar | Manter**.
- Em seguida, uma seção de **esperas longas**: tarefas em status `aguardando` há mais de M dias (configurável, padrão 14). Para cada uma, com tom acolhedor ("você está esperando isto há X dias — ainda faz sentido?"), oferece: **Cobrar agora** (cria/dispara a cobrança) | **Desbloquear** (volta para aberta) | **Arquivar** (sem culpa) | **Seguir esperando** (reinicia o contador).

### 6.5 Exportar casal

- Usuária toca /casal → bot formata as tarefas abertas da lista "Casa (casal)" e envia ao grupo configurado.

### 6.6 Desbloquear impedimento

1. O bot pergunta (na revisão, ao pular no /agora, ou via "estou travada nessa"): *"O que está te impedindo?"* com botões dos tipos de impedimento.
2. Conforme o tipo escolhido, dispara a estratégia:
   - **vaga/grande** → IA sugere o menor próximo passo; cria subtarefa de ≤ 2 min; oferece "começar por aqui".
   - **decisão pendente** → cria tarefa "decidir X".
   - **aversiva/energia** → rebaixa estimativa e sugere horário de pico / parear com algo agradável.
   - **pessoa** → botões: "Aguardando (tirar do radar)" ou "Criar cobrança com lembrete".
   - **recurso/info** → cria subtarefa "obter recurso X".
   - **data externa** → pede a data; define due_at e tira do radar até lá.
   - **obsoleta** → arquiva sem culpa, com mensagem acolhedora.
3. A tarefa registra o tipo de impedimento e (se houver) o próximo passo/subtarefa.

---

## 7. Comandos do bot (proposta)

| Comando | Função |
| --- | --- |
| (texto livre) | Captura/brain dump |
| /agora | Sugestão de uma tarefa para fazer agora |
| /listas | Ver e gerenciar listas |
| /ver `<lista>` | Ver tarefas de uma lista |
| /inbox | Ver itens não triados |
| /hoje | Focos do dia sob demanda |
| /casal | Exportar tarefas de casal para o grupo |
| /tudo | Ver todas as tarefas abertas agrupadas por lista |
| /medicacoes | Checklist de medicações recorrentes (diárias e semanais) |
| /buscar `<termo>` | Buscar tarefas |
| /config | Configurar horários, fuso, grupo de casal |
| /ajuda | Lista de comandos |

> Observação: comandos são atalhos; o uso primário é texto livre + botões inline, para manter o atrito baixo.

---

## 8. Riscos e mitigações

| Risco | Mitigação |
| --- | --- |
| Classificação da IA erra muito e gera retrabalho | Confirmação em bloco + aprendizado por exemplos no prompt; fallback para Inbox |
| Acúmulo de tarefas (cemitério) | Revisão semanal obrigatória + tom acolhedor |
| Custo de API sobe com uso intenso | Classificar em lote (uma chamada por brain dump); cache de padrões |
| Falha da hospedagem | Banco gerenciado com backup; bot stateless reinicia sem perda |
| Excesso de notificações vira ruído | Configurável; padrões conservadores |
