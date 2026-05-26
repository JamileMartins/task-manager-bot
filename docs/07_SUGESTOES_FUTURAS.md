# Sugestões de funcionalidades futuras

> Documento de referência — ideias para evoluir o Task Manager Bot.
> Última atualização: 2026-05-26.

---

## Sugestões gerais (sessão 2026-05-26)

Organizadas por impacto estimado para a persona principal.

### Alta prioridade — resolvem dores reais do dia a dia

**1. Check-in de energia no resumo matinal**
O resumo diário já envia focos, mas o `/agora` ainda pergunta energia toda vez.
Adicionar botões `Alta / Média / Baixa` ao final da mensagem matinal e salvar em
`config.energia_do_dia`. O `/agora` usa esse valor como padrão enquanto o dia durar,
eliminando uma pergunta repetida.

**2. Notas em tarefa existente**
O campo `notes` existe no modelo mas não há botão para editar numa tarefa aberta.
Um botão `📝 Nota` no detalhe abre um ConversationHandler simples: envia o texto → salva.
Útil para contexto: número de protocolo, link, "o que preciso levar".

**3. Histórico de conquistas**
Comando `/conquistas` ou seção no resumo matinal: "Ontem você concluiu X tarefas ✅".
Reforço positivo é uma das principais necessidades da persona — ver o que foi feito
reduz a sensação de acúmulo.

**4. Lembrete de prazo vencido**
Para tarefas com `due_at` que passou sem conclusão, notificação gentil (não punitiva)
algumas horas depois: "Ei, [tarefa] estava pra hoje — quer adiar, fazer agora ou arquivar?"
O job de lembretes já roda a cada minuto, seria fácil de plugar.

### Média prioridade — qualidade de vida

**5. `/proximos [N]` — tarefas dos próximos dias**
`/hoje` e `/amanha` já existem. Um `/proximos 7` mostraria tudo com prazo nos próximos
N dias agrupado por data, como uma agenda leve. Útil antes de viagens ou para
planejar a semana.

**6. Subtarefas visíveis no detalhe**
O modelo já tem `parent_task_id`, mas a tela de detalhe não exibe subtarefas.
Adicionar seção "Próximos passos" com as subtarefas e botão ✅ em cada uma daria
visibilidade ao progresso em tarefas do tipo `vaga_grande`.

**7. Modo pausa (`/pausar [X dias]`)**
Desativa jobs automáticos (resumo diário, revisão semanal, lembretes) por N dias.
Útil em viagens, férias ou semanas de prova quando as notificações viram ruído.
Um `/retomar` religaria tudo.

### Menor prioridade — polimento e conveniência

**8. `/exportar` — lista em texto**
Exporta todas as tarefas abertas como texto formatado para copiar. Útil para
compartilhar com alguém ou colar em outro sistema.

**9. Editar título de tarefa existente**
Hoje só dá para editar quadrante, energia, estimativa, prazo e lista. Corrigir um
título com erro de digitação exige arquivar e recriar.

**10. Streak semanal no encerramento da revisão**
Ao fechar a revisão semanal, mostrar "Você completou tarefas em X dos últimos 7 dias 🔥"
— motivação gamificada leve, sem sistema de pontos pesado.

### Fora do escopo atual (fases futuras)

- **Google Calendar sync** — mencionado no PRD como fase futura; tarefas com `due_at`
  aparecem como eventos.
- **Modo casal bidirecional** — parceiro pode adicionar tarefas ao grupo via bot sem
  ter acesso ao bot principal.

---

## Sugestões para dupla excepcionalidade — TDAH combinado + AH/SD

> Contexto: dupla excepcionalidade (2e) combina TDAH tipo combinado com Altas Habilidades
> e Superdotação. A inteligência tende a mascarar o TDAH (e vice-versa), o que dificulta
> o reconhecimento e o suporte. O perfil típico inclui: hiperfoco intenso em temas de
> interesse, produção massiva de ideias, muitos projetos iniciados com entusiasmo e
> abandonados quando o interesse cai, perfeccionismo que paralisa, e dificuldade especial
> com tarefas rotineiras e "sem sentido".
>
> As sugestões abaixo partem dessas especificidades — não apenas do TDAH genérico.

### 2e-1. Modo hiperfoco

Quando entra em hiperfoco, a usuária perde a noção de tempo, pula refeições e esquece
de pausas. Um `/hiperfoco [tarefa]` ativa um modo dedicado: o bot envia check-ins
gentis a cada intervalo configurável (ex: 45 min) com uma pergunta simples —
"Ainda focada em [tarefa]? Já tomou água? ☕" — e um botão "Concluí / Continuo / Pausa".
Ao sair do hiperfoco, registra automaticamente o tempo investido na tarefa.

*Por quê importa para 2e:* o hiperfoco é um recurso poderoso mas pode causar
esgotamento e descuido com necessidades básicas. Ter um "guardião externo" gentil
reduz o custo cognitivo de se auto-monitorar.

### 2e-2. Lista "Faísca" para captura de ideias em rajada

AH/SD produz conexões e ideias em alta velocidade, muitas vezes fora de hora. A Inbox
atual mistura tarefas acionáveis com ideias, o que polui a triagem. Uma lista especial
`Faísca` (ou nome escolhido pela usuária) seria acessível por atalho rápido (`/f Ideia aqui`)
sem passar pela classificação IA — captura instantânea, triagem posterior. A revisão
semanal teria uma seção dedicada: "Você tem X faíscas — alguma vale virar projeto?"

*Por quê importa para 2e:* não filtrar as ideias na captura reduz o atrito e respeita
o modo de pensar divergente. Ter um lugar separado evita que ideias poluam o radar
de ações concretas.

### 2e-3. Detector de projetos abandonados (síndrome do "novo brinquedo")

O perfil 2e tende a iniciar projetos com entusiasmo e abandoná-los quando a
novidade passa. Uma seção na revisão semanal — separada das tarefas paradas normais —
para projetos com mais de X subtarefas criadas mas nenhuma concluída nos últimos N dias,
com pergunta direta: "Esse projeto ainda te move? (Sim / Pausar / Arquivar)".
Sem culpa. A linguagem reconhece o padrão como parte do perfil, não como falha.

*Por quê importa para 2e:* nomear o padrão ("você iniciou 3 projetos no mês passado")
sem punir tira o peso da culpa e convida a uma decisão consciente sobre o que merece
energia real.

### 2e-4. Atributo "interesse" na tarefa (além do quadrante)

O TDAH tipo combinado opera por sistema de interesse, não por importância ou urgência
— tarefas chatas ficam paradas independente da prioridade. Adicionar um campo binário
`interessante: sim / não` (ou uma escala de 1–3) na tarefa. O `/agora` poderia oferecer
um modo `--balancear`: intercala uma tarefa necessária com uma interessante, tornando
o fluxo sustentável ao invés de só urgente-importante.

*Por quê importa para 2e:* reconhecer que o interesse é um dado real de priorização
(não "frescura") e usá-lo a favor, ao invés de ignorá-lo, aumenta muito a adesão.

### 2e-5. Anti-perfeccionismo integrado

O perfeccionismo em AH/SD combinado com TDAH cria um loop perigoso: a tarefa precisa
ser perfeita → nunca é suficientemente boa → nunca começa ou nunca termina.
Para tarefas marcadas com o impedimento `aversiva_energia` ou com mais de X dias
paradas, o bot poderia oferecer um "modo suficiente": "Qual seria a versão mínima
aceitável dessa tarefa? Me diz em uma frase." — salva como `next_step` e vira a
primeira ação. Mensagem de conclusão especial: "Feito! Feito é melhor que perfeito. 💚"

*Por quê importa para 2e:* o perfeccionismo paralisa mais em pessoas com AH/SD porque
o padrão interno é muito alto. Externalizar a definição de "suficiente" quebra o
loop sem invalidar a qualidade.

### 2e-6. Janela criativa configurável

AH/SD frequentemente tem blocos de alta criatividade e foco em horários específicos
(manhã cedo, noite, etc.). Configurar em `/config` uma "janela criativa" (ex: 22h–00h)
faria o `/agora` sugerir tarefas de Projetos e Ideias nesse horário, e reservar
tarefas administrativas/rotineiras para outros momentos. Respeita o ritmo natural
ao invés de lutar contra ele.

*Por quê importa para 2e:* produtividade não é distribuída linearmente no dia.
Alocar os tipos de tarefa certos nos momentos certos reduz o esforço e aumenta
a qualidade do resultado.

### 2e-7. Modo multiprojectos — visão de progresso

Com muitos projetos em paralelo (característica 2e), é difícil ter clareza de onde
cada um está. Um `/projetos` mostraria todas as listas com subtarefas ativas,
com barra de progresso textual (3/7 ✅) e último toque. Permite decidir
conscientemente qual projeto merece atenção agora sem varredura mental.

*Por quê importa para 2e:* a carga cognitiva de "onde estão meus projetos" é alta
e consome energia executiva que poderia ir para o trabalho em si.

### 2e-8. Captura de insights durante tarefas

Durante o trabalho, conexões e insights surgem e precisam ser registrados sem
interromper o fluxo. Um comando `/insight [texto]` (ou prefixo `> texto`) captura
o pensamento diretamente numa lista dedicada "Insights", sem classificação, sem
confirmação — resposta mínima: "Guardado 🧠". Diferente da Faísca (que é ideia de
projeto), o Insight é uma observação, conexão ou aprendizado.

*Por quê importa para 2e:* o pensamento associativo acelerado de AH/SD gera insights
constantemente. Não ter onde colocá-los gera ansiedade ou interrupção do foco.
Ter um repositório dedicado — revisado semanalmente — honra esse modo de pensar.

---

## Como priorizar

Para decidir o que implementar a seguir, considere:

1. **Frequência de uso** — funcionalidades usadas várias vezes por dia têm mais
   impacto que as usadas uma vez por semana.
2. **Custo de implementação** — sugestões 1, 2, 9 são pequenas; 2e-1, 2e-2 são médias;
   2e-3, 2e-6, 2e-7 são maiores.
3. **Dor atual** — se uma situação específica atrapalha o fluxo hoje, priorizar ela.
4. **Não implementar tudo de uma vez** — respeitar o princípio de baixo atrito:
   cada nova funcionalidade deve ganhar seu lugar pelo uso, não pela ambição.
