# Histórias de Usuário — Bot "Foco"

> Versão 1.0 — MVP
> Formato: "Como [persona], quero [ação], para [benefício]."
> Persona única: **usuária** (com TDAH).
> Cada história tem critérios de aceitação (CA) testáveis e referência ao RF do PRD.

---

## Épico 1 — Captura sem atrito

### US-01 — Capturar uma tarefa em texto livre

**Como** a usuária, **quero** enviar uma mensagem comum e que ela vire uma tarefa, **para** registrar sem pensar em comandos.

- Refs: RF01
- **CA:**
  - Dado que envio "ligar pro dentista", quando o bot recebe, então cria uma tarefa com esse título.
  - O bot confirma com mensagem curta e botão de desfazer.
  - Se a IA estiver indisponível, a tarefa ainda é salva na Inbox.
- Prioridade: Must · Fase: F1 · **Status: ✅ Feito**

### US-02 — Brain dump com várias tarefas

**Como** a usuária, **quero** despejar várias coisas numa mensagem só, **para** esvaziar a cabeça rapidamente.

- Refs: RF02, RF03
- **CA:**
  - Dado um texto com itens separados por vírgula/linha/"e", o bot separa em tarefas atômicas.
  - Cada tarefa recebe lista, quadrante, prazo, tempo e energia sugeridos.
  - O bot mostra um resumo numerado de tudo que entendeu.
- Prioridade: Must · Fase: F2 · **Status: ✅ Feito**

### US-03 — Aprovar captura em bloco

**Como** a usuária, **quero** aprovar tudo de uma vez, **para** não tomar muitas microdecisões.

- Refs: RF04
- **CA:**
  - O resumo traz botões "✅ Aprovar tudo" e "✏️ Ajustar".
  - "Aprovar tudo" salva todas as tarefas com as sugestões.
  - "Ajustar" permite editar item a item antes de salvar.
- Prioridade: Must · Fase: F2 · **Status: ✅ Feito**

### US-04 — Triagem da Inbox

**Como** a usuária, **quero** ver itens que a IA não classificou com confiança, **para** organizá-los quando puder.

- Refs: RF03 (fallback)
- **CA:**
  - Tarefas com confiança abaixo do limiar ficam na Inbox.
  - /inbox lista esses itens com botões para atribuir lista rapidamente.
- Prioridade: Should · Fase: F2 · **Status: ✅ Feito**

---

## Épico 2 — Organização em listas

### US-05 — Ver listas e suas tarefas

**Como** a usuária, **quero** ver minhas listas e abrir uma, **para** focar numa área de vida por vez.

- Refs: RF06
- **CA:**
  - /listas mostra as listas com contagem de tarefas abertas.
  - Ao escolher uma, vejo as tarefas ordenadas por quadrante e ordem manual.
- Prioridade: Must · Fase: F1 · **Status: ✅ Feito**

### US-06 — Criar, renomear e arquivar listas

**Como** a usuária, **quero** personalizar minhas listas, **para** adaptá-las à minha vida.

- Refs: RF05
- **CA:**
  - Posso criar uma nova lista com um nome.
  - Posso renomear e arquivar (sem apagar tarefas) uma lista existente.
  - As listas iniciais vêm pré-criadas (Trabalho, Casa solo, Casa casal, Saúde, Ideias).
- Prioridade: Must · Fase: F1 · **Status: ✅ Feito**

### US-07 — Mover tarefa entre listas

**Como** a usuária, **quero** mudar a lista de uma tarefa, **para** corrigir uma classificação.

- Refs: RF08
- **CA:**
  - Na visão da tarefa, há botão para trocar de lista.
  - A mudança reflete imediatamente nas contagens.
- Prioridade: Must · Fase: F3 · **Status: ✅ Feito**

---

## Épico 3 — Priorização (Eisenhower) e atributos

### US-08 — Quadrante sugerido pela IA

**Como** a usuária, **quero** que o sistema sugira o quadrante, **para** não travar na priorização.

- Refs: RF09
- **CA:**
  - Cada tarefa exibe o quadrante sugerido (Q1–Q4) com explicação curta.
  - Botões permitem confirmar ou trocar o quadrante com um toque.
- Prioridade: Must · Fase: F3 · **Status: ✅ Feito**

### US-09 — Definir prazo

**Como** a usuária, **quero** colocar uma data/hora, **para** não perder compromissos.

- Refs: RF10, RF20
- **CA:**
  - Posso definir prazo via botões (hoje, amanhã, escolher) ou texto ("sexta 15h").
  - O bot interpreta datas em português e no meu fuso.
- Prioridade: Must · Fase: F3 · **Status: ✅ Feito**

### US-10 — Estimativa de tempo e energia

**Como** a usuária, **quero** marcar quanto tempo e energia uma tarefa pede, **para** casar com meu estado.

- Refs: RF12
- **CA:**
  - Botões rápidos de tempo (5/15/30/60/120 min) e energia (alta/média/baixa).
  - Os valores ficam visíveis na tarefa.
- Prioridade: Must · Fase: F3 · **Status: ✅ Feito**

### US-11 — Ordenação manual

**Como** a usuária, **quero** reordenar tarefas dentro de uma lista, **para** definir minha sequência.

- Refs: RF06
- **CA:**
  - Botões "subir/descer" reordenam a tarefa na lista.
  - A ordem é persistida.
- Prioridade: Should · Fase: F3 · **Status: ✅ Feito**

---

## Épico 4 — Foco e execução

### US-12 — "O que faço agora"

**Como** a usuária, **quero** que o bot escolha UMA tarefa para mim, **para** vencer a paralisia.

- Refs: RF13
- **CA:**
  - /agora pergunta tempo disponível e energia atual (botões).
  - O bot sugere exatamente uma tarefa compatível.
  - Botões: "✅ Concluí", "⏭️ Outra", "😴 Adiar".
  - Se nada casar, sugere a tarefa mais leve com mensagem acolhedora.
- Prioridade: Must · Fase: F3 · **Status: ✅ Feito**

### US-13 — Concluir tarefa

**Como** a usuária, **quero** marcar como feita com um toque, **para** sentir progresso.

- Refs: RF07
- **CA:**
  - Botão de concluir em qualquer visão de tarefa.
  - Mensagem de reforço positivo ao concluir.
- Prioridade: Must · Fase: F1 · **Status: ✅ Feito**

### US-14 — Adiar tarefa

**Como** a usuária, **quero** empurrar uma tarefa para depois, **para** tirá-la da frente sem perdê-la.

- Refs: RF19
- **CA:**
  - Botões "amanhã", "próxima semana", "escolher data".
  - A tarefa sai dos focos de hoje e reaparece na nova data.
- Prioridade: Should · Fase: F4 · **Status: ✅ Feito**

---

## Épico 5 — Rituais anti-acúmulo

### US-15 — Resumo diário matinal

**Como** a usuária, **quero** receber meus focos de manhã, **para** começar o dia orientada.

- Refs: RF14
- **CA:**
  - No horário configurado, recebo tarefas com prazo hoje + até 3 focos (Q1/Q2).
  - Mensagem curta, com botões para iniciar /agora.
- Prioridade: Must · Fase: F4 · **Status: ✅ Feito**

### US-16 — Revisão semanal

**Como** a usuária, **quero** revisar o que está parado, **para** não acumular um cemitério de tarefas.

- Refs: RF15
- **CA:**
  - No dia/horário configurado, o bot lista tarefas paradas há mais de N dias.
  - Para cada uma, ofereço: Reagendar / Arquivar / Manter.
  - O tom é acolhedor, sem culpa.
- Prioridade: Must · Fase: F4 · **Status: ✅ Feito**

### US-17 — Lembretes por horário

**Como** a usuária, **quero** ser lembrada de tarefas com hora marcada, **para** não esquecer.

- Refs: RF17
- **CA:**
  - Tarefas com data/hora geram lembrete no horário.
  - O lembrete traz botões de concluir/adiar.
- Prioridade: Should · Fase: F4 · **Status: ✅ Feito**

### US-18 — Recorrência

**Como** a usuária, **quero** tarefas que se repetem, **para** não recriar rotinas (remédio, contas).

- Refs: RF11
- **CA:**
  - Posso marcar diária/semanal/mensal.
  - Ao concluir uma ocorrência, a próxima é criada automaticamente.
- Prioridade: Should · Fase: F4 · **Status: ✅ Feito**

---

## Épico 6 — Casal e configuração

### US-19 — Exportar tarefas de casal para grupo

**Como** a usuária, **quero** enviar a lista de casa-casal a um grupo, **para** combinar com meu parceiro.

- Refs: RF16
- **CA:**
  - /casal formata as tarefas abertas da lista de casal.
  - Envia a mensagem ao grupo configurado em /config.
  - Se o grupo não estiver configurado, o bot orienta como configurar.
- Prioridade: Should · Fase: F5 · **Status: ❌ Pendente**

### US-20 — Configurações

**Como** a usuária, **quero** ajustar horários e fuso, **para** o bot se encaixar na minha rotina.

- Refs: RF (config)
- **CA:**
  - /config permite definir hora do resumo diário, dia/hora da revisão, fuso e grupo de casal.
  - Valores padrão sensatos já vêm preenchidos.
- Prioridade: Should · Fase: F4 · **Status: ✅ Feito** (antecipado para F4)

### US-21 — Acesso restrito

**Como** a usuária, **quero** que só eu use o bot, **para** manter privacidade.

- Refs: RNF10
- **CA:**
  - O bot ignora mensagens de chat_id não autorizado.
  - A exceção é o grupo de casal, que só recebe envios (não comanda o bot).
- Prioridade: Must · Fase: F1 · **Status: ✅ Feito**

### US-22 — Buscar tarefas

**Como** a usuária, **quero** buscar por palavra, **para** achar algo rápido.

- Refs: RF18
- **CA:**
  - /buscar termo retorna tarefas que contêm o termo no título/notas.
- Prioridade: Could · Fase: F5 · **Status: ❌ Pendente**

---

## Épico 7 — Impedimentos e desbloqueio

### US-23 — Registrar impedimento de uma tarefa

**Como** a usuária, **quero** dizer o que está me impedindo numa tarefa, **para** transformar um bloqueio invisível em algo acionável.

- Refs: RF21, RF22
- **CA:**
  - Posso registrar impedimento na revisão semanal, ao pular no /agora ("Outra") e sob demanda ("estou travada nessa").
  - O bot mostra botões com os tipos: vaga/grande, decisão pendente, aversiva, pessoa, recurso/info, data externa, não importa mais.
  - O tipo e uma nota livre opcional ficam salvos na tarefa.
- Prioridade: Must · Fase: F4 · **Status: ✅ Feito**

### US-24 — Menor próximo passo automático

**Como** a usuária, **quero** que o bot quebre uma tarefa grande no menor passo possível, **para** vencer a paralisia de início.

- Refs: RF23
- **CA:**
  - Ao escolher impedimento "vaga/grande", a IA sugere um passo de ≤ 2 min no imperativo.
  - O passo é criado como subtarefa vinculada à tarefa-pai.
  - Botão "Começar por aqui" coloca o passo como sugestão imediata.
- Prioridade: Must · Fase: F4 · **Status: ✅ Feito**

### US-25 — Dependência de pessoa (aguardando ou cobrança)

**Como** a usuária, **quero** escolher o que fazer quando dependo de alguém, **para** tirar a tarefa do meu radar sem perdê-la.

- Refs: RF25, RF27
- **CA:**
  - Ao escolher impedimento "pessoa", recebo dois botões: "Aguardando" e "Criar cobrança com lembrete".
  - "Aguardando" muda o status e remove a tarefa do /agora e dos focos do dia.
  - "Criar cobrança" gera tarefa "cobrar fulano" com lembrete na data que eu definir.
- Prioridade: Must · Fase: F4 · **Status: ✅ Feito**

### US-26 — Decisão pendente e recurso faltante

**Como** a usuária, **quero** que o bot crie a ação certa quando falta decidir ou obter algo, **para** atacar a causa real do bloqueio.

- Refs: RF24, RF26
- **CA:**
  - "Decisão pendente" cria tarefa "decidir X" como primeira ação.
  - "Recurso/info" cria subtarefa "obter recurso X".
- Prioridade: Should · Fase: F4 · **Status: ✅ Feito**

### US-27 — Detectar impedimento na captura

**Como** a usuária, **quero** que o bot perceba dependências já quando anoto, **para** a tarefa não aparecer como pronta quando não está.

- Refs: RF28
- **CA:**
  - Se o texto indicar dependência externa, a tarefa é criada em status "aguardando".
  - O resumo de captura mostra o impedimento detectado para eu confirmar.
- Prioridade: Should · Fase: F4 · **Status: ✅ Feito** (`save_classified_tasks` aplica status `aguardando` para impedimentos externos; resumo exibe marcador visual)

### US-28 — Resolver/desbloquear impedimento

**Como** a usuária, **quero** marcar um impedimento como resolvido, **para** a tarefa voltar a ficar disponível.

- Refs: RF29
- **CA:**
  - Na tarefa bloqueada, há botão "Desbloquear".
  - Ao desbloquear, o status volta para "aberta" e a tarefa reentra no /agora.
  - Gatilhos automáticos (data atingida, cobrança concluída) também desbloqueiam.
- Prioridade: Must · Fase: F4 · **Status: ✅ Feito**

### US-29 — Revisar esperas longas

**Como** a usuária, **quero** revisar o que estou esperando há muito tempo, **para** não acumular um "cemitério de esperas".

- Refs: RF30
- **CA:**
  - Na revisão semanal, depois das tarefas paradas, vejo uma seção de tarefas em "aguardando" há mais de M dias (padrão 14, configurável).
  - O tom é acolhedor ("você espera isto há X dias — ainda faz sentido?").
  - Para cada uma, recebo botões: "Cobrar agora", "Desbloquear", "Arquivar", "Seguir esperando".
  - "Seguir esperando" reinicia o contador de espera.
- Prioridade: Should · Fase: F4 · **Status: ✅ Feito**

---

## Resumo de priorização e status

| Fase | Histórias | Status |
| --- | --- | --- |
| F1 | US-01, US-05, US-06, US-13, US-21 | ✅ Completa |
| F2 | US-02, US-03, US-04 | ✅ Completa |
| F3 | US-07, US-08, US-09, US-10, US-11, US-12 | ✅ Completa |
| F4 | US-14, US-15, US-16, US-17, US-18, US-20, US-23, US-24, US-25, US-26, US-27, US-28, US-29 | ✅ Completa |
| F5 | US-19, US-22 | ✅ Completa |
