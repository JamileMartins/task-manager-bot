# Prompt inicial para o Claude Code

> Como usar: abra a pasta `foco-bot/` como raiz do projeto no Claude Code e cole o bloco abaixo como sua primeira mensagem. Ele orienta o Claude Code a ler a documentação e implementar a Fase F1. Os prompts das fases seguintes estão ao final.

---

## 🚀 Prompt para iniciar (Fase F1)

```
Você vai desenvolver o "Foco", um bot de tarefas para Telegram. Toda a especificação está nos arquivos do projeto. Antes de escrever qualquer código, leia nesta ordem: CLAUDE.md, docs/01_PRD.md, docs/02_ESPECIFICACAO_TECNICA.md e docs/03_HISTORIAS_DE_USUARIO.md. O CLAUDE.md contém os princípios de design que você NÃO deve violar.

Stack definida: Python 3.11+, python-telegram-bot v21+ (async), SQLAlchemy 2.x + Alembic, PostgreSQL (Supabase). Siga a estrutura de pastas da seção 7 da especificação técnica.

Implemente agora APENAS a Fase F1 (Núcleo de captura), que cobre as histórias US-01, US-05, US-06, US-13 e US-21. Nesta fase NÃO há IA ainda. Entregue:

1. Configuração do projeto: requirements.txt, config.py (lendo variáveis de ambiente conforme .env.example), estrutura de pastas.
2. Modelos SQLAlchemy das tabelas users, lists, tasks, config (campos completos conforme seção 3 da spec, incluindo os de impedimento, mesmo que ainda não usados nesta fase) e a primeira migração Alembic.
3. Bootstrap do bot (main.py) com long polling.
4. Restrição de acesso: o bot responde apenas ao AUTHORIZED_CHAT_ID; qualquer outro chat_id recebe a mensagem neutra de "bot particular". Valide o chat_id em todos os handlers (US-21).
5. Listas iniciais pré-criadas no primeiro uso: Trabalho, Casa (solo), Casa (casal), Saúde, Ideias (US-06).
6. Captura por texto livre: qualquer mensagem de texto vira UMA tarefa na Inbox (list_id nulo), com confirmação curta e botão Desfazer (US-01).
7. Gerenciar listas: criar, renomear, arquivar; comando /listas mostrando contagem de abertas (US-05, US-06).
8. Ver tarefas de uma lista e concluir tarefa com um toque, com mensagem de reforço (US-13).

Requisitos de segurança (seção 11 da spec): nenhum segredo hardcoded, tudo via config.py; DATABASE_URL com SSL; nunca logar tokens nem corpo de tarefas; .env já está no .gitignore.

Para os textos das mensagens, use docs/05_TEXTOS_DO_BOT.md e centralize tudo em utils/textos.py. Respeite o tom (acolhedor, breve, sem culpa) e as variações sorteadas.

Escreva testes unitários para a lógica que não depende do Telegram (criação/conclusão de tarefa via serviço, criação de listas iniciais). Ao terminar, me explique como rodar localmente e valide os critérios de aceitação das histórias da F1.

Não implemente nada das fases F2 a F5 ainda. Quando a F1 estiver pronta e testada, eu peço a próxima.
```

---

## Prompts das fases seguintes (use uma de cada vez, após validar a anterior)

### Fase F2 — IA + classificação
```
A Fase F1 está pronta e testada. Agora implemente a Fase F2 (IA + classificação), histórias US-02, US-03 e US-04. Leia docs/04_PROMPT_CLASSIFICACAO_IA.md por completo — ele tem o system prompt de produção, regras de cada campo, exemplos few-shot, parsing seguro e pós-processamento.

Entregue: o cliente de IA em services/ai_service.py (usando ANTHROPIC_API_KEY, temperatura baixa, uma chamada por brain dump); separação de múltiplas tarefas e classificação; o resumo aprovável com botões "Aprovar tudo" e "Ajustar"; o fluxo de Inbox para baixa confiança; e o fallback obrigatório: se a IA falhar ou o JSON vier inválido, salvar o texto como uma tarefa na Inbox sem quebrar (RNF08). Inclua testes para o parser de JSON, inclusive entradas malformadas. Não avance para F3.
```

### Fase F3 — Priorização
```
Implemente a Fase F3 (Priorização), histórias US-07 a US-12. Inclua: mover tarefa entre listas; quadrante de Eisenhower sugerido com confirmação por botões; definir prazo (com parsing de datas em PT-BR no fuso do usuário); estimativa de tempo e energia por botões; ordenação manual; e o comando /agora conforme a seção 5 da spec (pergunta tempo e energia, sugere UMA tarefa, botões Concluí/Outra/Adiar/Tô travada; nunca sugere tarefas em status "aguardando"). Testes para a lógica de seleção do /agora e para o parsing de datas. Não avance para F4.
```

### Fase F4 — Rituais + impedimentos
```
Implemente a Fase F4, histórias US-14 a US-18 e US-23 a US-29. Inclua: resumo diário matinal; revisão semanal (tarefas paradas + seção de esperas longas conforme PRD §6.4); lembretes por horário; recorrência simples (diária/semanal/mensal); e todo o sistema de impedimentos (PRD §3.6 e §6.6): registrar impedimento nos três momentos, menor próximo passo automático para vaga_grande (chamada focada da seção 4.5 da spec), escolha aguardando-ou-cobrança para dependência de pessoa, criação de subtarefas para decisão/recurso, status "aguardando" com waiting_since, e desbloqueio manual e por gatilho. Use APScheduler (ou JobQueue) conforme seção 6 da spec. Não avance para F5.
```

### Fase F5 — Casal + polimento
```
Implemente a Fase F5, histórias US-19, US-20 e US-22. Inclua: comando /casal que formata e envia as tarefas abertas da lista de casal ao grupo configurado (com confirmação antes de enviar); /config para horários, fuso, grupo de casal e parâmetros stale_days/stale_waiting_days; e /buscar por palavra-chave. Revise o tom de todas as mensagens contra docs/05_TEXTOS_DO_BOT.md. Faça uma passada final de segurança usando o checklist da seção 11.6 da spec. Prepare instruções de deploy 24/7 no Railway ou Fly.io, com os segredos configurados como variáveis de ambiente da plataforma.
```

---

## Dica de fluxo de trabalho

- **Uma fase por vez.** Valide os critérios de aceitação antes de avançar — evita acumular bugs e mantém o escopo sob controle (útil para revisar sem sobrecarga).
- **Commit ao fim de cada fase**, conferindo antes que nenhum segredo entrou (`git status` e revisar o diff).
- Se o Claude Code quiser fazer tudo de uma vez, peça para voltar e respeitar o faseamento.
- Configure as contas (BotFather, Supabase, Anthropic) antes da F1 — veja a seção de pré-requisitos do README.md.
