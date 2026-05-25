"""Textos centralizados do bot Foco — fonte: docs/05_TEXTOS_DO_BOT.md."""
from __future__ import annotations

import random


def _pick(*variants: str) -> str:
    return random.choice(variants)


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

MSG_BOAS_VINDAS = (
    "Oi! Eu sou o Foco 🧠\n\n"
    "Pensa em mim como um lugar pra despejar tudo que tá na sua cabeça — "
    "sem se preocupar em organizar. Disso eu cuido.\n\n"
    "É só me mandar o que precisa fazer, do jeito que vier. "
    "Pode ser uma coisa só ou um monte de uma vez.\n\n"
    "Quando quiser, me chama com:\n"
    "• /agora — eu escolho UMA coisa pra você fazer\n"
    "• /listas — suas listas\n"
    "• /ajuda — tudo que eu sei fazer\n\n"
    "Bora começar? Me conta o que tá na sua mente agora."
)

MSG_AJUDA = (
    "Aqui vai o que eu faço 👇\n\n"
    "📥 Capturar\n"
    "Só me mandar o texto. Eu separo e organizo. "
    'Ex.: "comprar café, marcar dentista, ideia de aula nova"\n\n'
    "🎯 /agora — você me diz quanto tempo e energia tem, eu escolho UMA tarefa\n"
    "📋 /listas — ver e mexer nas suas listas\n"
    "📂 /ver <lista> — abrir uma lista\n"
    "📨 /inbox — o que ainda não organizei direito\n"
    "☀️ /hoje — seus focos de hoje\n"
    "👫 /casal — mandar as tarefas de casa pro grupo\n"
    "🔍 /buscar <palavra> — achar uma tarefa\n"
    "⚙️ /config — horários e ajustes\n\n"
    "🏓 /ping — verificar se estou funcionando\n"
    "🔄 /reiniciar — reiniciar o bot\n\n"
    "📖 /quadrantes — o que significam Q1, Q2, Q3, Q4 e como uso a energia\n\n"
    "Dica: você quase nunca precisa de comando. "
    "Só me manda o que vier na cabeça."
)

MSG_GUIA_QUADRANTES = (
    "📖 Como o Foco organiza suas tarefas\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🗂 Matriz de Eisenhower\n\n"
    "Cada tarefa cai num dos quatro quadrantes:\n\n"
    "🔴 Q1 — Urgente e importante\n"
    "Prazo curto e consequência real. Fazer agora.\n"
    'Ex.: "entregar relatório hoje", "consulta médica amanhã"\n\n'
    "🟡 Q2 — Importante, sem urgência\n"
    "Sem prazo imediato, mas é o que move sua vida de verdade. "
    "Priorizar antes que vire Q1.\n"
    'Ex.: "estudar para a certificação", "planejar as férias"\n\n'
    "🔵 Q3 — Urgente, mas não importante\n"
    "Alguém pediu ou tem prazo, mas não é essencial pra você. "
    "Fazer rápido ou delegar.\n"
    'Ex.: "responder e-mail de rotina", "preencher formulário"\n\n'
    "⚪ Q4 — Nem urgente nem importante\n"
    "Questione se realmente precisa ser feito. Talvez possa arquivar.\n"
    'Ex.: "organizar pasta de fotos de 2019", "pesquisa sem uso"\n\n'
    "━━━━━━━━━━━━━━━━━━━━\n"
    "⚡ Níveis de energia\n\n"
    "O /agora usa o seu nível de energia pra escolher a tarefa certa:\n\n"
    "⚡ Alta — tarefas que exigem foco, decisão ou criatividade\n"
    "🔋 Média — tarefas operacionais, comunicação, organização\n"
    "🪫 Baixa — tarefas mecânicas, leituras leves, revisões simples\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🧠 Como o Foco pensa\n\n"
    "1. Você manda texto livre — eu identifico e separo as tarefas\n"
    "2. A IA sugere lista, quadrante, tempo e energia de cada uma\n"
    "3. Você aprova em bloco ou ajusta item a item\n"
    "4. /agora filtra por tempo e energia e te dá UMA tarefa\n"
    "5. A revisão semanal cuida do que ficou parado"
)


def msg_ping(agora: str) -> str:
    return f"Funcionando ✅ — {agora}"


MSG_REINICIANDO = "Reiniciando... 🔄"


# ---------------------------------------------------------------------------
# Acesso / erros
# ---------------------------------------------------------------------------

MSG_NAO_AUTORIZADO = "Oi! Esse bot é particular e só responde pra dona dele 🙂"

MSG_ERRO_GENERICO = (
    "Deu um probleminha aqui do meu lado 😅 "
    "Tenta de novo daqui a pouco — o que você já tinha salvo tá seguro."
)


# ---------------------------------------------------------------------------
# Captura
# ---------------------------------------------------------------------------

def msg_captura_confirmacao() -> str:
    return _pick(
        "Anotado ✅",
        "Guardado. Pode esquecer que eu lembro 🧠",
        "Tá na lista ✅",
    )


MSG_CAPTURA_FALLBACK = (
    "Salvei tudo na sua caixa de entrada pra gente organizar depois — nada se perdeu 👍\n\n"
    "(Tive um soluço pra classificar agora, mas o importante tá guardado.)"
)

MSG_DESFAZER_OK = "Desfeito ✅"


# ---------------------------------------------------------------------------
# Conclusão
# ---------------------------------------------------------------------------

def msg_conclusao() -> str:
    return _pick(
        "Feito ✅",
        "Boa! Menos uma 💪",
        "Concluído ✅ Tá indo bem.",
        "Pronto ✅ Pode comemorar essa.",
    )


# ---------------------------------------------------------------------------
# Listas
# ---------------------------------------------------------------------------

MSG_SUAS_LISTAS = "Suas listas:"

MSG_LISTA_VAZIA = "{nome} tá vazia por enquanto.\nQuando surgir algo dessa área, é só me mandar."

MSG_PERGUNTAR_NOME_LISTA = "Como vai se chamar a nova lista?"

MSG_LISTA_CRIADA = 'Criada ✅ "{nome}" já tá disponível.'

MSG_PERGUNTAR_NOVO_NOME = 'Qual o novo nome para "{nome}"?'

MSG_LISTA_RENOMEADA = 'Feito ✅ Renomeada para "{nome}".'

MSG_LISTA_ARQUIVADA = '"{nome}" arquivada. As tarefas foram mantidas.'

MSG_CANCELADO = "Cancelado."

MSG_CONFIRMAR_ARQUIVAR = 'Arquivar "{nome}"? As tarefas ficam salvas mas a lista some do menu.'


# ---------------------------------------------------------------------------
# Inbox
# ---------------------------------------------------------------------------

MSG_INBOX_VAZIA = "Sua caixa de entrada tá limpa 🎉"

MSG_INBOX_TITULO = "📥 Caixa de entrada ({n} {item}):"


def msg_inbox_titulo(n: int) -> str:
    item = "item" if n == 1 else "itens"
    return f"📥 Caixa de entrada ({n} {item}):"


# ---------------------------------------------------------------------------
# Emojis por quadrante e energia (doc §12)
# ---------------------------------------------------------------------------

QUADRANT_EMOJI = {1: "🔴", 2: "🟡", 3: "🔵", 4: "⚪"}
ENERGY_EMOJI = {"alta": "⚡", "media": "🔋", "baixa": "🪫"}

LIST_EMOJI: dict[str, str] = {
    "trabalho": "💼",
    "projetos": "📁",
    "casa-solo": "🏠",
    "casa-casal": "🏠",
    "saude": "💚",
    "ideias": "💡",
}


def lista_emoji(slug: str) -> str:
    return LIST_EMOJI.get(slug, "📋")


# ---------------------------------------------------------------------------
# Classificação / Brain dump (F2)
# ---------------------------------------------------------------------------

_ENERGIA_EMOJI = {"alta": "⚡", "media": "🔋", "baixa": "🪫"}
_QUADRANT_LABEL = {1: "Q1 🔴", 2: "Q2 🟡", 3: "Q3 🔵", 4: "Q4 ⚪"}


def msg_classificacao_resumo(tarefas: list[dict]) -> str:
    """Monta o resumo numerado das tarefas classificadas pela IA."""
    n = len(tarefas)
    header = f"Entendi {'1 tarefa' if n == 1 else f'{n} tarefas'}:\n"
    linhas: list[str] = []

    for i, t in enumerate(tarefas, 1):
        lista = t.get("lista_sugerida")
        destino = lista if lista else "📥 Inbox"
        detalhes: list[str] = [f"→ {destino}"]

        q = t.get("quadrante_sugerido")
        if q:
            detalhes.append(_QUADRANT_LABEL[q])

        est = t.get("estimativa_min")
        if est:
            detalhes.append(f"{est}min")

        energia = t.get("energia", "")
        if energia in _ENERGIA_EMOJI:
            detalhes.append(_ENERGIA_EMOJI[energia])

        linha = f"{i}. {t.get('titulo', '')}\n   {' · '.join(detalhes)}"

        if t.get("impedimento") == "vaga_grande" and t.get("proximo_passo"):
            linha += f"\n   💡 {t['proximo_passo']}"

        linhas.append(linha)

    return header + "\n\n".join(linhas)


def msg_ajustar_tarefa(tarefa: dict, index: int, total: int) -> str:
    lista_atual = tarefa.get("lista_sugerida") or "Inbox"
    titulo = tarefa.get("titulo", "")
    return (
        f"Tarefa {index + 1} de {total}: \"{titulo}\"\n"
        f"Sugerida para: {lista_atual}\n\n"
        "Onde colocar?"
    )


def msg_captura_salva(n: int) -> str:
    return f"{'Tarefa salva' if n == 1 else f'{n} tarefas salvas'} ✅"


MSG_CLASSIFICANDO = "Classificando... 🧠"


# ---------------------------------------------------------------------------
# /agora (F3 — US-12)
# ---------------------------------------------------------------------------

MSG_AGORA_TEMPO = "Quanto tempo você tem agora?"
MSG_AGORA_ENERGIA = "Qual sua energia agora?"
MSG_AGORA_NADA = (
    "Nada na lista encaixa agora 😌\n"
    "Aproveita para descansar ou me manda algo novo."
)
MSG_AGORA_ADIAR_PENDENTE = "Adiamento chega na próxima versão — por enquanto, pula ou conclui 😊"


def msg_agora_tarefa(task, fallback: bool = False) -> str:
    lista_nome = task.task_list.name if task.task_list else "📥 Inbox"
    detalhes: list[str] = [f"→ {lista_nome}"]
    q = task.quadrant
    if q:
        detalhes.append(_QUADRANT_LABEL[q])
    if task.energy and task.energy in _ENERGIA_EMOJI:
        detalhes.append(_ENERGIA_EMOJI[task.energy])
    if task.estimate_min:
        detalhes.append(f"{task.estimate_min}min")
    info = " · ".join(detalhes)

    if fallback:
        header = "Não achei nada perfeito para agora, mas que tal começar por isso?"
    else:
        header = "🎯 Sugestão para agora:"
    return f"{header}\n\n{task.title}\n{info}"


# ---------------------------------------------------------------------------
# Detalhe e edição de tarefa (F3 — US-07, 08, 09, 10, 11)
# ---------------------------------------------------------------------------

_BLOCKER_LABEL: dict[str, str] = {
    "vaga_grande": "🌫️ Grande/vaga",
    "decisao_pendente": "🤔 Falta decidir",
    "aversiva_energia": "😖 Chata/pesada",
    "pessoa": "🧍 Depende de alguém",
    "recurso_info": "🧩 Falta algo",
    "data_externa": "📅 Aguardando data",
    "obsoleta": "🗑️ Não importa mais",
}


def msg_task_detail(task) -> str:
    import pytz
    lista_nome = task.task_list.name if task.task_list else "📥 Inbox"
    lines = [f"📋 {task.title}\n", f"📂 {lista_nome}"]

    atributos: list[str] = []
    if task.quadrant:
        atributos.append(_QUADRANT_LABEL[task.quadrant])
    if task.energy and task.energy in _ENERGIA_EMOJI:
        atributos.append(_ENERGIA_EMOJI[task.energy] + f" {task.energy}")
    if task.estimate_min:
        atributos.append(f"{task.estimate_min}min")
    lines.append(" · ".join(atributos) if atributos else "Sem atributos definidos")

    if task.due_at:
        try:
            tz = pytz.timezone("America/Fortaleza")
            prazo = task.due_at.astimezone(tz).strftime("%d/%m às %H:%M")
        except Exception:
            prazo = str(task.due_at)[:16]
        lines.append(f"📅 {prazo}")
    else:
        lines.append("📅 Sem prazo")

    if task.status == "aguardando":
        blocker_label = _BLOCKER_LABEL.get(task.blocker_type or "", "impedimento externo")
        lines.append(f"\n⏳ Aguardando — {blocker_label}")
    elif task.blocker_type:
        lines.append(f"\n⚠️ Travada: {_BLOCKER_LABEL.get(task.blocker_type, task.blocker_type)}")

    if task.next_step:
        lines.append(f"💡 Próximo passo: {task.next_step}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Impedimentos (F4 — US-23 a US-28)
# ---------------------------------------------------------------------------

def msg_blocker_pergunta(task_title: str) -> str:
    return f"Sem problema. O que tá travando essa aqui?\n\n👉 {task_title}"


def msg_blocker_vaga_sugestao(passo: str) -> str:
    return (
        "Essa é grande mesmo. A gente não vai resolver tudo agora — "
        "só dar o primeiro passinho:\n\n"
        f"👉 {passo}\n\n"
        "Leva uns 2 minutos. Topa começar só por aí?"
    )


def msg_blocker_decidir(task_title: str) -> str:
    return (
        "Então o verdadeiro primeiro passo é decidir. Vou criar isso como tarefa:\n\n"
        f"👉 Decidir: {task_title}\n\n"
        "Quando você decidir, o resto destrava sozinho."
    )


MSG_BLOCKER_PESSOA = "Essa depende de outra pessoa. Como prefere?"

MSG_BLOCKER_AGUARDANDO = (
    "Belê. Tirei do seu radar por enquanto ⏳\n"
    "Ela volta na revisão se demorar demais. "
    "Você não precisa segurar isso na cabeça."
)

MSG_BLOCKER_COBRAR_QUANDO = "Quando devo te lembrar de cobrar?"


def msg_blocker_cobrar_ok(data: str) -> str:
    return f"Feito 🔔 Vou te lembrar de cobrar em {data}."


MSG_BLOCKER_AVERSIVA = (
    "Entendi, essa pesa. Guardei pra quando você tiver mais energia ⚡\n"
    "Só aparece no /agora quando você marcar energia alta."
)


def msg_blocker_recurso(task_title: str) -> str:
    return (
        "Falta uma coisa antes de fazer essa. Vou criar o passo que destrava:\n\n"
        f"👉 Obter o necessário para: {task_title}\n\n"
        "Assim que você tiver isso, a tarefa principal libera."
    )


MSG_BLOCKER_DATA_QUANDO = "Essa só dá pra fazer mais pra frente. A partir de quando?"


def msg_blocker_data_ok(data: str) -> str:
    return f"Combinado 📅 Guardei até {data}. Não te incomodo com ela antes disso."


MSG_BLOCKER_OBSOLETA = (
    "Tudo bem deixar isso ir. Nem tudo que a gente anota continua importante "
    "— e isso não é falha sua.\n\nArquivo essa pra você?"
)

MSG_BLOCKER_ARQUIVADA = "Arquivada sem culpa 🗑️"
MSG_BLOCKER_KEEP = "Ok, mantida como está."
MSG_UNBLOCK_OK = "Destravada ✅ Voltou pras suas tarefas ativas."
