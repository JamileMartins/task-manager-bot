# Textos do Bot "Foco" (Microcopy)

> Versão 1.0 — companion dos demais docs.
> Centraliza todas as mensagens ao usuário, para manter tom consistente (ver CLAUDE.md).
> No código, recomenda-se um módulo `utils/textos.py` com estas strings e funções auxiliares.

---

## 0. Princípios de voz

- **Acolhedor, não infantil.** Trata a usuária como adulta competente que às vezes trava.
- **Breve.** Frases curtas. Evitar parágrafos. Um emoji ocasional ajuda a escanear, mas sem exagero.
- **Sem culpa.** Nunca "você esqueceu", "de novo parada", "você não fez". Em vez disso: foco no próximo passo.
- **Celebra progresso real,** sem bajulação. "Feito ✅" vale mais que três frases de elogio.
- **Linguagem de ação.** Verbos no imperativo gentil: "Bora?", "Que tal começar por...".
- **Variação.** Mensagens muito repetidas (conclusão, captura) têm várias versões sorteadas.
- **PT-BR**, informal-respeitoso (você).

> Convenção: textos com `|` separam variações que o código deve sortear aleatoriamente.

---

## 1. Onboarding e ajuda

### 1.1 Primeira mensagem (/start)

```prompt
Oi! Eu sou o Foco 🧠

Pensa em mim como um lugar pra despejar tudo que tá na sua cabeça — sem se preocupar em organizar. Disso eu cuido.

É só me mandar o que precisa fazer, do jeito que vier. Pode ser uma coisa só ou um monte de uma vez.

Quando quiser, me chama com:
• /agora — eu escolho UMA coisa pra você fazer
• /listas — suas listas
• /ajuda — tudo que eu sei fazer

Bora começar? Me conta o que tá na sua mente agora.
```

### 1.2 Ajuda (/ajuda)

```prompt
Aqui vai o que eu faço 👇

📥 Capturar
Só me mandar o texto. Eu separo e organizo. Ex.: "comprar café, marcar dentista, ideia de aula nova"

🎯 /agora — você me diz quanto tempo e energia tem, eu escolho UMA tarefa
📋 /listas — ver e mexer nas suas listas
📂 /ver <lista> — abrir uma lista
📨 /inbox — o que ainda não organizei direito
☀️ /hoje — seus focos de hoje
👫 /casal — mandar as tarefas de casa pro grupo
🔍 /buscar <palavra> — achar uma tarefa
⚙️ /config — horários e ajustes

Dica: você quase nunca precisa de comando. Só me manda o que vier na cabeça.
```

---

## 2. Captura (brain dump)

### 2.1 Confirmação de captura simples (1 tarefa)

Sortear entre:

```prompt
Anotado ✅
```

```text
Guardado. Pode esquecer que eu lembro 🧠
```

```text
Tá na lista ✅
```

Com botão: `[ Desfazer ]`

### 2.2 Resumo de brain dump (várias tarefas)

```text
Boa, esvaziei sua cabeça 🧠 Entendi {n} tarefas:

{lista_numerada}

Tá tudo certo?
```

Botões: `[ ✅ Aprovar tudo ]` `[ ✏️ Ajustar ]`

Formato de cada item em `{lista_numerada}`:

```text
{i}. {titulo}
   📂 {lista} · {quadrante_emoji} {energia_emoji} {tempo}{prazo_str}{impedimento_str}
```

- `{prazo_str}`: `· 📅 {data}` quando houver, senão vazio.
- `{impedimento_str}`: `· ⏳ aguardando` quando externo, senão vazio.

### 2.3 Quando a IA falha (fallback)

```text
Salvei tudo na sua caixa de entrada pra gente organizar depois — nada se perdeu 👍

(Tive um soluço pra classificar agora, mas o importante tá guardado.)
```

### 2.4 Item que foi pra Inbox por baixa confiança

Dentro do resumo, marcar:

```text
   📥 deixei na caixa de entrada (não tive certeza da lista)
```

---

## 3. Conclusão de tarefa

Sortear entre (reforço positivo leve, sem exagero):

```text
Feito ✅
```

```text
Boa! Menos uma 💪
```

```text
Concluído ✅ Tá indo bem.
```

```text
Pronto ✅ Pode comemorar essa.
```

### 3.1 Quando conclui via /agora

```text
Mandou bem ✅ Quer que eu te dê a próxima ou parar por aqui?
```

Botões: `[ ➡️ Próxima ]` `[ ✋ Parar por agora ]`

---

## 4. "O que faço agora" (/agora)

### 4.1 Pergunta de tempo

```text
Quanto tempo você tem agora?
```

Botões: `[ 5 min ]` `[ 15 min ]` `[ 30 min ]` `[ 1h+ ]`

### 4.2 Pergunta de energia

```text
E como tá sua energia?
```

Botões: `[ ⚡ Alta ]` `[ 🔋 Média ]` `[ 🪫 Baixa ]`

### 4.3 Sugestão de tarefa

```text
Então foca nisso 👇

👉 {titulo}
{lista} · {tempo} · {energia_emoji}{prazo_str}

Não precisa pensar no resto agora. Só essa.
```

Botões: `[ ✅ Concluí ]` `[ ⏭️ Outra ]` `[ 😴 Adiar ]` `[ 😩 Tô travada ]`

### 4.4 Nada casou exatamente

```text
Não achei nada que encaixe certinho no seu tempo e energia agora. Que tal algo bem leve só pra destravar?

👉 {titulo}
```

Botões: `[ ✅ Topo ]` `[ ⏭️ Outra ]` `[ ✋ Agora não ]`

### 4.5 Sem tarefas abertas

```text
Olha só: você não tem nada pendente pra agora 🎉
Aproveita.
```

---

## 5. Impedimentos (destravar)

### 5.1 Pergunta inicial ("Tô travada" / pular no /agora / revisão)

```text
Sem problema. O que tá travando essa aqui?

👉 {titulo}
```

Botões (2 por linha):

```text
[ 🌫️ Grande/vaga ]   [ 🤔 Falta decidir ]
[ 😖 Chata/pesada ]   [ 🧍 Depende de alguém ]
[ 🧩 Falta algo ]      [ 📅 Só depois de uma data ]
[ 🗑️ Não importa mais ]
```

### 5.2 vaga_grande → próximo passo

```text
Essa é grande mesmo. A gente não vai resolver tudo agora — só dar o primeiro passinho:

👉 {proximo_passo}

Leva uns 2 minutos. Topa começar só por aí?
```

Botões: `[ ✅ Começar por aqui ]` `[ 🔁 Sugerir outro passo ]`

### 5.3 decisao_pendente

```text
Então o verdadeiro primeiro passo é decidir. Vou criar isso como tarefa:

👉 Decidir: {titulo}

Quando você decidir, o resto destrava sozinho.
```

Botão: `[ 👍 Criar "decidir" ]`

### 5.4 aversiva_energia

```text
Entendi, essa pesa. Sem drama — dá pra deixar mais fácil:

• Reduzi a estimativa pra um pedaço pequeno
• Te sugiro ela num momento de energia melhor

Quer que eu guarde pra quando você tiver mais pique?
```

Botões: `[ 🔋 Guardar p/ energia alta ]` `[ ✂️ Fazer só um pedaço agora ]`

### 5.5 pessoa → escolha

```text
Essa depende de outra pessoa. Como prefere?
```

Botões: `[ ⏳ Deixar aguardando ]` `[ 🔔 Criar cobrança com lembrete ]`

#### 5.5.1 Escolheu aguardando

```text
Belê. Tirei do seu radar por enquanto ⏳
Ela volta na revisão se demorar demais. Você não precisa segurar isso na cabeça.
```

#### 5.5.2 Escolheu cobrança

```text
Quando devo te lembrar de cobrar?
```

Botões: `[ Amanhã ]` `[ Em 3 dias ]` `[ Em 1 semana ]` `[ Escolher data ]`
Depois:

```text
Feito 🔔 Vou te lembrar de cobrar em {data}.
```

### 5.6 recurso_info

```text
Falta uma coisa antes de fazer essa. Vou criar o passo que destrava:

👉 Conseguir: {recurso}

Assim que você tiver isso, a tarefa principal libera.
```

Botão: `[ 👍 Criar esse passo ]`

### 5.7 data_externa

```text
Essa só dá pra fazer mais pra frente. A partir de quando?
```

Botões: `[ Escolher data ]`
Depois:

```text
Combinado 📅 Guardei até {data}. Não te incomodo com ela antes disso.
```

### 5.8 obsoleta

```text
Tudo bem deixar isso ir. Nem tudo que a gente anota continua importante — e isso não é falha sua.

Arquivo essa pra você?
```

Botões: `[ 🗑️ Arquivar sem culpa ]` `[ ↩️ Deixa, ainda quero ]`

### 5.9 Desbloqueio manual

```text
Destravada ✅ Voltou pras suas tarefas ativas.
```

---

## 6. Resumo diário

### 6.1 Mensagem matinal

```text
Bom dia ☀️

Sem pressão — só os destaques de hoje:

{focos}

Se bater dúvida do que fazer, é só /agora que eu escolho por você.
```

Formato de `{focos}` (até 3 + prazos de hoje):

```text
🎯 {titulo} · {tempo}
📅 (com prazo hoje) {titulo}
```

### 6.2 Dia sem nada marcado

```text
Bom dia ☀️
Hoje não tem nada com prazo. Dia livre pra escolher o que faz sentido — ou pra descansar, que também conta.
```

---

## 7. Revisão semanal

### 7.1 Abertura

```text
Hora da revisão da semana 🗂️
Vou ser rápida e nada de cobrança — a ideia é só tirar o peso das costas.

Tenho {n} tarefas que estão paradas há um tempo. Vamos uma por uma?
```

Botões: `[ 👍 Bora ]` `[ ⏰ Agora não ]`

### 7.2 Cada tarefa parada

```text
Essa tá parada há {dias} dias:

👉 {titulo}

O que rola com ela?
```

Botões: `[ 📅 Reagendar ]` `[ 😩 Tô travada ]` `[ 🗑️ Arquivar ]` `[ ✋ Manter ]`

> Nota: "Tô travada" entra no fluxo de impedimentos (seção 5).

### 7.3 Esperas longas (abertura da seção)

```text
Agora as coisas que você tá esperando faz tempo ⏳
Sem stress — só checar se ainda fazem sentido.
```

### 7.4 Cada espera longa

```text
Você espera essa há {dias} dias:

👉 {titulo}{quem_str}

Ainda faz sentido?
```

- `{quem_str}`: `(de {pessoa})` quando registrado, senão vazio.
Botões: `[ 🔔 Cobrar agora ]` `[ ✅ Destravar ]` `[ 🗑️ Arquivar ]` `[ ⏳ Seguir esperando ]`

### 7.5 Encerramento

```text
Pronto, revisão fechada 🙌
{resumo_curto}

Isso já deixa sua semana mais leve. Até a próxima.
```

- `{resumo_curto}` ex.: `Você reagendou 3, arquivou 2 e destravou 1.` (omitir zeros).

### 7.6 Nada a revisar

```text
Revisão da semana: nada parado, nada esquecido 🎉
Tá tudo fluindo. Bom fim de semana.
```

---

## 8. Lembretes

### 8.1 Lembrete de tarefa com horário

```text
🔔 Lembrete: {titulo}
{quando_str}
```

Botões: `[ ✅ Feito ]` `[ ⏰ +1h ]` `[ 😴 Amanhã ]`

### 8.2 Lembrete de cobrança

```text
🔔 Hora de cobrar: {titulo}
{quem_str}
```

Botões: `[ ✅ Já cobrei ]` `[ ⏰ Lembrar depois ]` `[ ✅ Resolveu ]`

---

## 9. Listas

### 9.1 Ver listas (/listas)

```text
Suas listas:

{linhas}
```

Formato: `{emoji} {nome} — {n} abertas`
Botões: `[ ➕ Nova lista ]`

### 9.2 Lista vazia

```text
{nome} tá vazia por enquanto. 
Quando surgir algo dessa área, é só me mandar.
```

### 9.3 Criar lista

```text
Como vai se chamar a nova lista?
```

Depois:

```text
Criada ✅ "{nome}" já tá disponível.
```

---

## 10. Casal (/casal)

### 10.1 Antes de enviar

```text
Vou mandar essas {n} tarefas de casa pro grupo:

{lista_curta}

Pode enviar?
```

Botões: `[ 📤 Enviar pro grupo ]` `[ ✖️ Cancelar ]`

### 10.2 Mensagem enviada ao grupo

```text
🏠 Tarefas de casa — combinando aqui:

{checklist}

(enviado pela usuária via Foco)
```

### 10.3 Grupo não configurado

```text
Ainda não sei pra qual grupo mandar. Configura rapidinho em /config que aí eu cuido disso.
```

---

## 11. Erros e bordas

### 11.1 Mensagem não compreendida como tarefa

```text
Não tenho certeza se isso é uma tarefa. Quer que eu guarde mesmo assim?
```

Botões: `[ 📥 Guardar ]` `[ ✖️ Era só conversa ]`

### 11.2 Acesso não autorizado

```text
Oi! Esse bot é particular e só responde pra dona dele 🙂
```

### 11.3 Falha genérica

```text
Deu um probleminha aqui do meu lado 😅 Tenta de novo daqui a pouco — o que você já tinha salvo tá seguro.
```

---

## 12. Mapa de emojis (consistência)

| Conceito | Emoji |
| --- | --- |
| Quadrante 1 (urgente+importante) | 🔴 |
| Quadrante 2 (importante) | 🟡 |
| Quadrante 3 (urgente, operacional) | 🔵 |
| Quadrante 4 (talvez eliminar) | ⚪ |
| Energia alta | ⚡ |
| Energia média | 🔋 |
| Energia baixa | 🪫 |
| Prazo/data | 📅 |
| Aguardando | ⏳ |
| Lista trabalho | 💼 |
| Lista casa | 🏠 |
| Lista saúde | 💚 |
| Lista ideias | 💡 |
| Caixa de entrada | 📥 |

> Use os emojis com parcimônia: no máximo 1–2 por mensagem fora das listas, para não virar ruído visual.
