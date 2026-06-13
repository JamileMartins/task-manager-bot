"""Textos centralizados do bot Task Manager — fonte: docs/05_TEXTOS_DO_BOT.md."""
from __future__ import annotations

import random

import pytz as _pytz

from src.version import __release_dt__, __version__

_BRT = _pytz.timezone("America/Fortaleza")
__release_date__ = __release_dt__.astimezone(_BRT).strftime("%Y-%m-%d %H:%M") + " BRT"


def _pick(*variants: str) -> str:
    return random.choice(variants)


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------

MSG_BOAS_VINDAS = (
    f"Oi! Eu sou o Task Manager v{__version__} 🧠\n\n"
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
    "🗂️ /tudo — todas as tarefas abertas de uma vez\n"
    "💊 /medicacoes — checklist de medicações do dia/semana\n"
    "☀️ /hoje — seus focos e prazos de hoje\n"
    "🌙 /amanha — o que tem prazo para amanhã\n"
    "📅 /proximos [N] — agenda dos próximos N dias (padrão 7)\n"
    "📊 /progresso — progresso por lista (e breakdown do casal)\n"
    "💞 /casal — tarefas compartilhadas com seu par\n"
    "   /casal_convidar · /casal_entrar <código> · /casal_status\n"
    "🔍 /buscar <palavra> — achar uma tarefa\n"
    "🏆 /conquistas — ver o que você concluiu na semana\n"
    "🔗 /ordem — cadeias de dependência em ordem de execução\n"
    "📤 /exportar — todas as tarefas abertas em texto\n"
    "🍅 /foco [min] [descanso] — iniciar um pomodoro (padrão 50+15)\n"
    "⏸️ /pausar [dias] — silenciar resumos e lembretes por N dias\n"
    "▶️ /retomar — reativar os resumos e lembretes\n"
    "⚙️ /config — horários e ajustes\n\n"
    "🏓 /ping — verificar se estou funcionando\n"
    "🔄 /reiniciar — reiniciar o bot\n\n"
    "📖 /quadrantes — o que significam Q1, Q2, Q3, Q4 e como uso a energia\n\n"
    "🗓️ Janela de tempo — ao criar uma lista (ou no ⚙️ dentro de /listas) você "
    "escolhe se ela mostra tudo ou só as tarefas do *dia*, da *semana* ou do *mês*. "
    "Listas mensais (ex.: Financeiro) deixam navegar entre os meses com ◀ ▶, e tarefas "
    "sem data ficam fixadas no topo.\n\n"
    "🔁 Recorrência — no detalhe de qualquer tarefa dá pra repetir *Diária*, *Semanal*, "
    "*Quinzenal* ou *Mensal*.\n\n"
    "😩 Impedimento — abra o detalhe de qualquer tarefa e toque em *Travada*. "
    "Também aparece ao pular uma tarefa no /agora.\n\n"
    "Dica: você quase nunca precisa de comando. "
    "Só me manda o que vier na cabeça.\n\n"
    f"Task Manager v{__version__} · publicado em {__release_date__}"
)

MSG_GUIA_QUADRANTES = (
    "📖 Como o Task Manager organiza suas tarefas\n\n"
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
    "🧠 Como o Task Manager pensa\n\n"
    "1. Você manda texto livre — eu identifico e separo as tarefas\n"
    "2. A IA sugere lista, quadrante, tempo e energia de cada uma\n"
    "3. Você aprova em bloco ou ajusta item a item\n"
    "4. /agora filtra por tempo e energia e te dá UMA tarefa\n"
    "5. A revisão semanal cuida do que ficou parado"
)


def msg_ping(agora: str) -> str:
    return f"Funcionando ✅ — {agora}"


MSG_REINICIANDO = f"Reiniciando Task Manager v{__version__}... 🔄"


# ---------------------------------------------------------------------------
# Acesso / erros
# ---------------------------------------------------------------------------

MSG_NAO_AUTORIZADO = "Oi! Esse bot é particular e só responde pra dona dele 🙂"

MSG_ERRO_GENERICO = (
    "Deu um probleminha aqui do meu lado 😅 "
    "Tenta de novo daqui a pouco — o que você já tinha salvo tá seguro."
)


def msg_mover_duplicada(titulo: str, lista_nome: str) -> str:
    return (
        f"⚠️ Já existe uma tarefa chamada _{titulo}_ nessa lista ({lista_nome}).\n\n"
        "Mover mesmo assim vai criar uma duplicata. Quer continuar?"
    )


MSG_MOVER_MESMA_LISTA = "Essa tarefa já está nessa lista 😊"

MSG_MOVER_OK = "Tarefa movida ✅"


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

MSG_PERGUNTAR_JANELA_LISTA = (
    'E "{nome}" deve mostrar tudo ou só as tarefas de um período? 🗓️\n\n'
    "• *Sem janela* — mostra todas as tarefas (padrão)\n"
    "• *Diária* — só as do dia\n"
    "• *Semanal* — só as da semana\n"
    "• *Mensal* — só as do mês (dá pra navegar entre os meses)"
)

_WINDOW_NOME = {"dia": "diária", "semana": "semanal", "mes": "mensal"}

MSG_LISTA_CRIADA = 'Criada ✅ "{nome}" já tá disponível.'


def msg_lista_criada(nome: str, view_window: str | None = None) -> str:
    if view_window in _WINDOW_NOME:
        return f'Criada ✅ "{nome}" (janela {_WINDOW_NOME[view_window]}) já tá disponível.'
    return MSG_LISTA_CRIADA.format(nome=nome)


def msg_lista_janela_menu(nome: str) -> str:
    return (
        f'Como a lista "{nome}" deve mostrar as tarefas? 🗓️\n\n'
        "• *Sem janela* — mostra todas as tarefas\n"
        "• *Diária* — só as do dia\n"
        "• *Semanal* — só as da semana\n"
        "• *Mensal* — só as do mês (dá pra navegar entre os meses)"
    )


def msg_lista_janela_alterada(nome: str, view_window: str | None = None) -> str:
    if view_window in _WINDOW_NOME:
        return f'Pronto ✅ "{nome}" agora mostra só as tarefas do período ({_WINDOW_NOME[view_window]}).'
    return f'Pronto ✅ "{nome}" voltou a mostrar todas as tarefas (sem janela).'


_MESES_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]
_MESES_ABREV = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _add_months_date(d, months: int):
    from datetime import date as _date
    total = (d.year * 12 + (d.month - 1)) + months
    year, month = divmod(total, 12)
    return _date(year, month + 1, 1)


def periodo_label(window: str, offset: int) -> str:
    """Rótulo curto do período navegado, em PT-BR e no fuso de Fortaleza.

    Ex.: dia → "13/06 (sexta)"; semana → "semana de 09–15/jun"; mes → "junho/2026".
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("America/Fortaleza")
    hoje = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    if window == "dia":
        d = hoje + timedelta(days=offset)
        return f"{d.strftime('%d/%m')} ({_DOW_NOME[d.weekday()].lower()})"
    if window == "semana":
        ini = (hoje - timedelta(days=hoje.weekday())) + timedelta(weeks=offset)
        fim = ini + timedelta(days=6)
        if ini.month == fim.month:
            return f"semana de {ini.day:02d}–{fim.day:02d}/{_MESES_ABREV[ini.month - 1]}"
        return f"semana de {ini.day:02d}/{_MESES_ABREV[ini.month - 1]}–{fim.day:02d}/{_MESES_ABREV[fim.month - 1]}"
    # mes
    first = _add_months_date(hoje.date(), offset)
    return f"{_MESES_PT[first.month - 1]}/{first.year}"

MSG_PERGUNTAR_NOVO_NOME = 'Qual o novo nome para "{nome}"?'

MSG_LISTA_RENOMEADA = 'Feito ✅ Renomeada para "{nome}".'

MSG_LISTA_ARQUIVADA = '"{nome}" arquivada. As tarefas foram mantidas.'

MSG_CANCELADO = "Cancelado."

MSG_ADD_TASK_TITULO = "Qual o título da tarefa?"


def msg_add_task_ok(list_name: str) -> str:
    return f"Adicionado em {list_name} ✅"

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
    "casal": "💞",
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
        elif t.get("impedimento_externo"):
            linha += "\n   ⏳ Criada como aguardando (impedimento externo detectado)"

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
MSG_AGORA_ADIAR_QUANDO = "Para quando você quer adiar? 😴"


def msg_agora_adiada(days: int) -> str:
    if days == 1:
        return "Guardado para amanhã ✅\nVoltamos a isso depois!"
    if days <= 3:
        return f"Guardado para daqui {days} dias ✅\nVoltamos a isso depois!"
    return "Guardado para a próxima semana ✅\nVoltamos a isso depois!"


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


def msg_task_detail(task, subtasks=None, blocking_task=None, blocked_dependents=None) -> str:
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

    if task.blocker_note:
        lines.append(f"📝 {task.blocker_note}")

    if blocking_task is not None:
        lines.append(f"⛔ Bloqueada por: {blocking_task.title}")
    if blocked_dependents:
        nomes = ", ".join(d.title for d in blocked_dependents)
        lines.append(f"🔓 Desbloqueia: {nomes}")

    _CAT_LABEL = {"medicacao": "💊 Medicação", "agendamento": "📅 Agendamento"}
    if task.category and task.category in _CAT_LABEL:
        lines.append(_CAT_LABEL[task.category])

    _REC_LABEL = {"daily": "🔁 Diária", "weekly": "🔁 Semanal", "quinzenal": "🔁 Quinzenal", "monthly": "🔁 Mensal"}
    if task.recurrence and task.recurrence in _REC_LABEL:
        lines.append(_REC_LABEL[task.recurrence])

    if task.next_step:
        lines.append(f"💡 Próximo passo: {task.next_step}")
    if subtasks:
        lines.append(f"\n📌 Próximos passos ({len(subtasks)}):")
        for s in subtasks:
            est = f" · {s.estimate_min}min" if s.estimate_min else ""
            lines.append(f"  • {s.title}{est}")

    if task.notes:
        lines.append(f"\n📝 {task.notes}")
    return "\n".join(lines)


def msg_nota_pergunta(task_title: str) -> str:
    return (
        f"📝 Qual nota quer adicionar em:\n\n👉 {task_title}\n\n"
        "Pode ser um link, número de protocolo, contexto — o que ajudar a lembrar."
    )


MSG_NOTA_SALVA = "📝 Nota salva."
MSG_NOTA_APAGADA = "🗑️ Nota removida."


def msg_titulo_pergunta(task_title: str) -> str:
    return (
        f"✏️ Qual é o novo título?\n\n"
        f"Atual: {task_title}"
    )


MSG_TITULO_SALVO = "✏️ Título atualizado."


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


def msg_blocker_aversiva(estimate_min: int | None) -> str:
    estimate_info = (
        f" Reduzi o tempo estimado para {estimate_min} min para parecer menos pesada."
        if estimate_min
        else ""
    )
    return (
        f"Entendi, essa pesa.{estimate_info}\n\n"
        "Ela só vai aparecer no /agora quando você marcar *energia alta* — "
        "assim você a faz num momento de pico ⚡\n\n"
        "💡 Dica: parear com algo que você gosta (música, café, pausas) "
        "pode ajudar bastante nesse tipo de tarefa."
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

# --- Nota livre no impedimento ---

MSG_BLOCKER_NOTA_PEDIR = (
    "Quer deixar uma nota sobre o impedimento?\n"
    "Ex: _'Preciso comprar tinta na loja X'_ ou _'Aguardando resposta da Maria'_"
)

MSG_BLOCKER_NOTA_SALVA = "Nota salva ✅"

MSG_BLOCKER_NOTA_MANDE = "Mande a nota (uma frase curta):"

# --- Dependência de outra tarefa ---

MSG_BLOCKER_DEPENDE_ESCOLHA = (
    "Qual tarefa precisa ser concluída primeiro?\n\n"
    "Escolha uma da lista:"
)

MSG_BLOCKER_DEPENDE_VAZIA = (
    "Você não tem tarefas abertas para vincular aqui.\n"
    "Crie a tarefa bloqueadora primeiro e tente novamente."
)


def msg_blocker_depende_ok(blocking_title: str) -> str:
    return (
        f"Entendido ✅\n\n"
        f"Essa tarefa fica pausada até _\"{blocking_title}\"_ ser concluída.\n"
        "Quando você marcar aquela como feita, essa volta automaticamente para suas ativas."
    )


def msg_auto_unblock_dependency(unblocked_title: str, blocking_title: str) -> str:
    return (
        f"🔓 *{unblocked_title}* foi desbloqueada!\n\n"
        f"Você concluiu _{blocking_title}_ e essa tarefa voltou para suas ativas.\n"
        "Quer atacá-la agora? /agora"
    )


# --- Auto-unblock por data ---

def msg_auto_unblock(title: str) -> str:
    return (
        f"📬 *{title}*\n\n"
        "Chegou a data que você estava esperando — voltei com essa tarefa pras suas ativas. "
        "Quer dar uma olhada no /agora? 🙂"
    )


# --- /agora skip com blocker ---

MSG_AGORA_TRAVADA = "Tudo bem. O que está travando essa tarefa?"

MSG_AGORA_PULAR_MESMO = "Pular sem registrar"


# ---------------------------------------------------------------------------
# /ordem — cadeias de dependência (v1.18.0)
# ---------------------------------------------------------------------------

MSG_ORDEM_VAZIA = (
    "Nenhuma cadeia de dependência encontrada 🔓\n\n"
    "Quando você vincular tarefas com *Depende de outra tarefa*, "
    "elas aparecem aqui em ordem de execução."
)


def msg_ordem_header(n_chains: int, n_ready: int) -> str:
    pronto = "1 pronta pra começar" if n_ready == 1 else f"{n_ready} prontas pra começar"
    return (
        f"📋 *Ordem de execução* — {n_chains} {'cadeia' if n_chains == 1 else 'cadeias'}\n"
        f"▶ {pronto}"
    )


# --- Contexto de dependência no detalhe da tarefa ---

def msg_bloqueada_por(title: str) -> str:
    return f"⛔ Bloqueada por: _{title}_"


def msg_desbloqueia(titles: list[str]) -> str:
    lista = ", ".join(f"_{t}_" for t in titles)
    return f"🔓 Desbloqueia: {lista}"


# ---------------------------------------------------------------------------
# Lembretes (US-17)
# ---------------------------------------------------------------------------

def msg_lembrete(task_title: str) -> str:
    return f"⏰ Lembrete!\n\n*{task_title}*\n\nHora de atacar essa."


# ---------------------------------------------------------------------------
# Resumo diário (US-15)
# ---------------------------------------------------------------------------

MSG_DIARIO_VAZIO = (
    "Bom dia ☀️\n"
    "Hoje não tem nada com prazo. Dia livre pra escolher o que faz sentido — "
    "ou pra descansar, que também conta."
)

MSG_HOJE_VAZIO = (
    "Nenhuma tarefa com prazo para hoje ☀️\n"
    "Dia livre! Se quiser uma sugestão, é só /agora."
)

MSG_AMANHA_VAZIO = (
    "Nenhuma tarefa com prazo para amanhã 🌙\n"
    "Amanhã está livre por enquanto."
)


def msg_diario_focos(today_tasks: list, focus_tasks: list) -> str:
    lines = ["Bom dia ☀️\n", "Sem pressão — só os destaques de hoje:\n"]
    for t in today_tasks:
        est = f" · {t.estimate_min}min" if t.estimate_min else ""
        lines.append(f"📅 {t.title}{est}")
    for t in focus_tasks:
        est = f" · {t.estimate_min}min" if t.estimate_min else ""
        lines.append(f"🎯 {t.title}{est}")
    lines.append("\nSe bater dúvida do que fazer, é só /agora que eu escolho por você.")
    return "\n".join(lines)


def msg_hoje(today_tasks: list, focus_tasks: list) -> str:
    import pytz
    tz = pytz.timezone("America/Fortaleza")
    lines = ["☀️ Hoje\n"]
    if today_tasks:
        lines.append(f"📅 Com prazo ({len(today_tasks)}):")
        for t in today_tasks:
            hora = f" · {t.due_at.astimezone(tz).strftime('%H:%M')}" if t.due_at else ""
            est = f" · {t.estimate_min}min" if t.estimate_min else ""
            lines.append(f"  • {t.title}{hora}{est}")
    if focus_tasks:
        if today_tasks:
            lines.append("")
        lines.append(f"🎯 Focos Q1/Q2 ({len(focus_tasks)}):")
        for t in focus_tasks:
            est = f" · {t.estimate_min}min" if t.estimate_min else ""
            lines.append(f"  • {t.title}{est}")
    lines.append("\n/agora — eu escolho UMA pra você começar.")
    return "\n".join(lines)


def msg_amanha(tasks: list) -> str:
    import pytz
    tz = pytz.timezone("America/Fortaleza")
    s = "" if len(tasks) == 1 else "s"
    lines = [f"🌙 Amanhã — {len(tasks)} tarefa{s} com prazo\n"]
    for t in tasks:
        hora = f" · {t.due_at.astimezone(tz).strftime('%H:%M')}" if t.due_at else ""
        est = f" · {t.estimate_min}min" if t.estimate_min else ""
        lista = f" [{t.task_list.name}]" if t.task_list else ""
        lines.append(f"  • {t.title}{hora}{est}{lista}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Conquistas — histórico de conclusões (Sugestão #3)
# ---------------------------------------------------------------------------

def msg_conquistas(stats: dict) -> str:
    hoje = stats.get("hoje", 0)
    ontem = stats.get("ontem", 0)
    semana = stats.get("semana", 0)
    dias = stats.get("dias_ativos", 0)

    def _tarefas(n: int) -> str:
        return "1 tarefa" if n == 1 else f"{n} tarefas"

    lines = ["🏆 Suas conquistas\n"]

    if hoje > 0:
        lines.append(f"Hoje: {_tarefas(hoje)} concluídas ✅")
    if ontem > 0:
        lines.append(f"Ontem: {_tarefas(ontem)} concluídas ✅")
    elif hoje == 0 and semana == 0:
        lines.append("Ainda sem tarefas concluídas nos últimos 7 dias.")

    if semana > 0:
        lines.append(f"\nEsta semana (7 dias): {_tarefas(semana)} no total")
        lines.append(f"Dias produtivos: {dias} de 7")

    if semana >= 10:
        lines.append("\nVocê está numa ótima fase. Continue assim!")
    elif semana >= 5:
        lines.append("\nBoa semana! Cada tarefa feita é progresso real.")
    elif semana > 0:
        lines.append("\nCada uma conta. Você está em movimento.")

    return "\n".join(lines)


def msg_conquistas_diario(ontem: int) -> str:
    """Linha curta para o resumo matinal, só quando ontem > 0."""
    if ontem == 1:
        return "Ontem você concluiu 1 tarefa ✅"
    return f"Ontem você concluiu {ontem} tarefas ✅"


# ---------------------------------------------------------------------------
# Revisão semanal (US-16)
# ---------------------------------------------------------------------------

MSG_REVISAO_NADA = (
    "Revisão da semana: nada parado, nada esquecido 🎉\n"
    "Tá tudo fluindo. Bom fim de semana."
)

MSG_REVISAO_ESPERAS_ABERTURA = (
    "Agora as coisas que você tá esperando faz tempo ⏳\n"
    "Sem stress — só checar se ainda fazem sentido."
)


def msg_revisao_abertura(n: int) -> str:
    tarefas = "tarefa" if n == 1 else "tarefas"
    esta = "está" if n == 1 else "estão"
    s = "" if n == 1 else "s"
    return (
        "Hora da revisão da semana 🗂️\n"
        "Vou ser rápida e nada de cobrança — a ideia é só tirar o peso das costas.\n\n"
        f"Tenho {n} {tarefas} que {esta} parada{s} há um tempo. Vamos uma por uma?"
    )


def msg_revisao_tarefa(task, dias: int) -> str:
    d = "dia" if dias == 1 else "dias"
    return (
        f"Essa tá parada há {dias} {d}:\n\n"
        f"👉 {task.title}\n\n"
        "O que rola com ela?"
    )


def msg_revisao_espera(task, dias: int) -> str:
    d = "dia" if dias == 1 else "dias"
    return (
        f"Você espera essa há {dias} {d}:\n\n"
        f"👉 {task.title}\n\n"
        "Ainda faz sentido?"
    )


def msg_revisao_encerramento(stats: dict, dias_ativos: int | None = None) -> str:
    partes = []
    if stats.get("reagendadas"):
        partes.append(f"reagendou {stats['reagendadas']}")
    if stats.get("arquivadas"):
        partes.append(f"arquivou {stats['arquivadas']}")
    if stats.get("destravadas"):
        partes.append(f"destravou {stats['destravadas']}")
    resumo = (", ".join(partes) + ".").capitalize() if partes else "Tudo mantido como estava."

    streak = ""
    if dias_ativos is not None and dias_ativos > 0:
        if dias_ativos >= 7:
            streak = f"\n\n🔥 7 de 7 dias produtivos essa semana. Semana perfeita!"
        elif dias_ativos >= 5:
            streak = f"\n\n🔥 {dias_ativos} de 7 dias com tarefas concluídas. Semana muito boa!"
        elif dias_ativos >= 3:
            streak = f"\n\n🌱 {dias_ativos} de 7 dias produtivos. Você tá em movimento!"
        else:
            streak = f"\n\n🌱 {dias_ativos} de 7 dias com algo concluído. Cada um conta."

    return (
        f"Pronto, revisão fechada 🙌\n"
        f"{resumo}{streak}\n\n"
        "Isso já deixa sua semana mais leve. Até a próxima."
    )


# ---------------------------------------------------------------------------
# /casal (US-19)
# ---------------------------------------------------------------------------

MSG_CASAL_VAZIA = (
    "A lista de casa (casal) tá vazia 🏠\n"
    "Ainda não tem tarefas abertas por aqui."
)

MSG_CASAL_SEM_GRUPO = (
    "Grupo do casal ainda não configurado 👫\n\n"
    "Adicione o bot ao grupo e mande /setgrupo lá pra vincular."
)

MSG_CASAL_SEM_PAR = (
    "Você ainda não está conectado(a) a ninguém 💞\n\n"
    "Para compartilhar tarefas com seu par:\n"
    "• /casal_convidar — eu gero um código pra você enviar\n"
    "• /casal_entrar <código> — se já recebeu um\n\n"
    "Depois de conectados, marque tarefas como 💞 Casal na captura."
)

MSG_CASAL_ENVIADO = "Enviado para o grupo do casal ✅"

MSG_SETGRUPO_OK = "Grupo registrado ✅ Agora o /casal vai enviar as tarefas aqui."

MSG_SETGRUPO_APENAS_GRUPO = "Use esse comando em um grupo onde o casal está."


# ---------------------------------------------------------------------------
# Pareamento de casal (Fase C2)
# ---------------------------------------------------------------------------

def msg_casal_convite(code: str) -> str:
    return (
        "💞 Convite de casal criado!\n\n"
        f"Mande este código para o seu par:\n\n👉 *{code}*\n\n"
        "No bot dele(a), é só mandar:\n"
        f"`/casal_entrar {code}`\n\n"
        "O código vale por 24 horas."
    )


MSG_CASAL_JA_PAREADO = (
    "Vocês já estão conectados 💞\n"
    "Use /casal_status para ver com quem, ou /casal para as tarefas compartilhadas."
)

MSG_CASAL_PRECISA_START = "Antes de convidar, manda um /start pra eu te conhecer 🙂"


def msg_casal_entrou_ok(partner_name: str | None) -> str:
    nome = partner_name or "seu par"
    return (
        f"💞 Pronto! Você e {nome} agora estão conectados.\n\n"
        "Tarefas de casal vão aparecer para os dois. Use /casal pra ver."
    )


def msg_casal_parceiro_entrou(partner_name: str | None) -> str:
    nome = partner_name or "Seu par"
    return (
        f"💞 {nome} entrou no casal com você!\n\n"
        "A partir de agora, as tarefas de casal aparecem para os dois."
    )


MSG_CASAL_CODIGO_INVALIDO = "Não achei esse código 🤔 Confere se digitou certinho."

MSG_CASAL_CODIGO_EXPIRADO = (
    "Esse código expirou ⏳\n"
    "Peça um novo: a outra pessoa manda /casal_convidar de novo."
)

MSG_CASAL_CODIGO_USADO = "Esse código já foi usado 🙃 Peça um novo, se precisar."

MSG_CASAL_ENTRAR_JA_PAREADO = (
    "Você já está num casal 💞\n"
    "Use /casal_status pra ver com quem."
)

MSG_CASAL_ENTRAR_PROPRIO = "Esse é o seu próprio código 😄 Mande ele para o seu par."

MSG_CASAL_ENTRAR_CHEIO = "Esse casal já está completo (duas pessoas)."

MSG_CASAL_ENTRAR_SEM_CODIGO = (
    "Me diz o código junto, assim:\n`/casal_entrar ABC123`"
)


def msg_casal_status_pareado(partner_name: str | None) -> str:
    nome = partner_name or "seu par"
    return f"💞 Você está conectado(a) com *{nome}*.\nUse /casal pra ver as tarefas compartilhadas."


def msg_casal_concluiu(actor: str, titulo: str) -> str:
    return _pick(
        f"💞 {actor} concluiu \"{titulo}\" ✅",
        f"✅ {actor} deu conta de \"{titulo}\"!",
        f"💞 Feito por {actor}: \"{titulo}\" ✅",
    )


def msg_casal_compartilhou(actor: str, n: int) -> str:
    if n == 1:
        return f"💞 {actor} compartilhou uma tarefa de casal com você."
    return f"💞 {actor} compartilhou {n} tarefas de casal com você."


def msg_casal_atribuiu(actor: str, titulo: str) -> str:
    return f"💞 {actor} deixou \"{titulo}\" pra você 🙋"


MSG_CASAL_STATUS_SOLO = (
    "Você ainda não está num casal 👤\n\n"
    "Para conectar com alguém:\n"
    "• /casal_convidar — eu gero um código pra você compartilhar\n"
    "• /casal_entrar <código> — se já recebeu um código"
)


def couple_mode_label(task, names: dict | None = None) -> str:
    """Rótulo curto do modo de uma tarefa de casal: individual / conjunta / sem dono."""
    names = names or {}
    if getattr(task, "assigned_to", None):
        return f"🙋 {names.get(task.assigned_to, 'um de vocês')}"
    if getattr(task, "couple_joint", False):
        return "💞 os dois"
    return "🤝 sem dono"


def _autoria_casal(task, names: dict | None = None) -> str:
    """Linha de autoria de uma tarefa do casal: quem cadastrou e quando.

    Ex.: "✍️ Jamile · 12/06 às 14:30". Tolerante a tarefa sem criador
    (tarefas antigas, antes do registro de autoria) ou sem data.
    """
    names = names or {}
    criador = getattr(task, "created_by", None)
    nome = (names.get(criador) or "").split()[0] if criador else ""

    criado = getattr(task, "created_at", None)
    quando = ""
    if criado is not None:
        if criado.tzinfo is None:
            criado = criado.replace(tzinfo=_pytz.utc)
        quando = criado.astimezone(_BRT).strftime("%d/%m às %H:%M")

    if nome and quando:
        return f"✍️ {nome} · {quando}"
    if nome:
        return f"✍️ {nome}"
    if quando:
        return f"🕓 {quando}"
    return ""


def msg_casal(tasks: list, names: dict | None = None) -> str:
    n = len(tasks)
    header = f"💞 Casal — {n} {'tarefa' if n == 1 else 'tarefas'}:\n"
    lines = [header]
    for t in tasks:
        q = QUADRANT_EMOJI.get(t.quadrant, "◾") if t.quadrant else "◾"
        est = f" · {t.estimate_min}min" if t.estimate_min else ""
        lines.append(f"{q} {t.title}{est}  ({couple_mode_label(t, names)})")
        autoria = _autoria_casal(t, names)
        if autoria:
            lines.append(f"      {autoria}")
    return "\n".join(lines)


def msg_casal_marcou_conjunta(actor: str, titulo: str) -> str:
    return f"💞 {actor} marcou \"{titulo}\" como conjunta — precisa dos dois 🤝"


def msg_casal_concluiu_conjunta(actor: str, titulo: str) -> str:
    return _pick(
        f"💞 {actor} fechou a conjunta \"{titulo}\" ✅ Valeu a dupla!",
        f"🤝 Tarefa dos dois concluída por {actor}: \"{titulo}\" ✅",
    )


# ---------------------------------------------------------------------------
# /buscar (US-22)
# ---------------------------------------------------------------------------

MSG_BUSCA_SEM_TERMO = "Me diz o que buscar 🔍\nEx.: /buscar reunião"

MSG_BUSCA_VAZIA = "Não encontrei nada com esse termo 🔍\nTenta outra palavra?"


def msg_busca(tasks: list, term: str) -> str:
    n = len(tasks)
    header = f'🔍 "{term}" — {n} {"tarefa" if n == 1 else "tarefas"}:\n'
    lines = [header]
    for t in tasks:
        lista = t.task_list.name if t.task_list else "📥 Inbox"
        status_icon = "⏳" if t.status == "aguardando" else "◾"
        lines.append(f"{status_icon} {t.title}\n   → {lista}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# /medicacoes (US-32)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Áudio / voz
# ---------------------------------------------------------------------------

MSG_AUDIO_ERRO = (
    "Não consegui entender o áudio 🎙️\n"
    "Pode digitar o que você disse?"
)


def msg_audio_ouvi(texto: str) -> str:
    return f"🎙️ Ouvi:\n\"{texto}\"\n\nOrganizando..."


# ---------------------------------------------------------------------------
# /medicacoes (US-32)
# ---------------------------------------------------------------------------

MSG_MED_VAZIA = (
    "Nenhuma medicação cadastrada ainda 💊\n\n"
    "Toque em ➕ Nova medicação para adicionar a primeira."
)

MSG_MED_PEDIR_NOME = "Qual o nome da medicação?"
MSG_MED_PEDIR_HORARIO = (
    "Qual o horário aproximado para tomar?\n"
    "Ex: 08:00\n\n"
    "Ou toque em Pular."
)
MSG_MED_PEDIR_FREQ = "Com que frequência você toma?"
MSG_MED_PEDIR_DIA = "Qual dia da semana?"

_DOW_NOME = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def _dow_nome(recurrence: str) -> str:
    """Retorna o nome do dia da semana a partir de 'weekly:N'."""
    parts = recurrence.split(":")
    if len(parts) == 2:
        try:
            return _DOW_NOME[int(parts[1])]
        except (ValueError, IndexError):
            pass
    return ""


def msg_medicacoes(daily: list, weekly: list, completed_hoje: list | None = None) -> str:
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Fortaleza")

    lines = ["💊 Medicações\n"]
    if daily:
        lines.append(f"📅 Hoje ({len(daily)})")
        for t in daily:
            horario = f"  ⏰ {t.notes}" if t.notes else ""
            lines.append(f"  • {t.title}{horario}")
    if weekly:
        if daily:
            lines.append("")
        lines.append(f"📆 Semanal ({len(weekly)})")
        for t in weekly:
            dia = f" — {_dow_nome(t.recurrence or '')}" if t.recurrence and ":" in t.recurrence else ""
            horario = f"  ⏰ {t.notes}" if t.notes else ""
            lines.append(f"  • {t.title}{dia}{horario}")
    if completed_hoje:
        lines.append("")
        lines.append("✅ Tomadas hoje:")
        for t in completed_hoje:
            hora = t.completed_at.astimezone(tz).strftime("%H:%M")
            lines.append(f"  • {t.title} — {hora}")
    return "\n".join(lines)


def msg_med_ok(title: str, recurrence: str, med_time: str | None = None, dow: int | None = None) -> str:
    if recurrence == "daily":
        freq = "diária"
    elif dow is not None:
        freq = f"semanal — {_DOW_NOME[dow]}"
    else:
        freq = "semanal"
    horario = f" às {med_time}" if med_time else ""
    return f"{title} adicionada ({freq}{horario}) ✅\nAparece no /medicacoes a partir de hoje."


# ---------------------------------------------------------------------------
# /tudo (US-31)
# ---------------------------------------------------------------------------

MSG_TUDO_VAZIA = "Nenhuma tarefa aberta no momento 🎉\nTudo limpo por aqui."


def msg_tudo_header(nome: str, emoji: str, n_visivel: int, n_total: int) -> str:
    s = "" if n_total == 1 else "s"
    header = f"{emoji} {nome} — {n_total} tarefa{s}"
    if n_visivel < n_total:
        header += f"\n(mostrando {n_visivel}, +{n_total - n_visivel} mais)"
    return header


# ---------------------------------------------------------------------------
# /config (US-20)
# ---------------------------------------------------------------------------

_DOW_PT: dict[int, str] = {
    0: "segunda-feira", 1: "terça-feira", 2: "quarta-feira",
    3: "quinta-feira", 4: "sexta-feira", 5: "sábado", 6: "domingo",
}


def msg_config_status(cfg) -> str:
    if cfg is None or cfg.daily_summary_time is None:
        diario = "desativado"
    else:
        diario = cfg.daily_summary_time.strftime("%H:%M")

    if cfg is None or cfg.weekly_review_dow is None or cfg.weekly_review_time is None:
        revisao = "desativada"
    else:
        dow = _DOW_PT.get(cfg.weekly_review_dow, str(cfg.weekly_review_dow))
        revisao = f"{dow} às {cfg.weekly_review_time.strftime('%H:%M')}"

    casal = "não configurado" if cfg is None or cfg.couple_group_chat_id is None else "configurado ✅"

    return (
        "⚙️ Configurações\n\n"
        f"☀️ Resumo diário: {diario}\n"
        f"🗂️ Revisão semanal: {revisao}\n"
        f"👫 Grupo do casal: {casal}"
    )


# ---------------------------------------------------------------------------
# Energia do dia (Sugestão #1)
# ---------------------------------------------------------------------------

MSG_ENERGIA_DO_DIA_CHECK = "Como está sua energia hoje?"

MSG_ENERGIA_DO_DIA_SALVA = "Energia registrada. O /agora vai usar isso enquanto o dia durar."


# ---------------------------------------------------------------------------
# Prazo vencido (Sugestão #4)
# ---------------------------------------------------------------------------

def msg_prazo_vencido(task_title: str) -> str:
    return (
        f"⏰ *{task_title}* estava com prazo para hoje e ainda está aberta.\n\n"
        "O que quer fazer?"
    )


# ---------------------------------------------------------------------------
# Exportar (Sugestão #8)
# ---------------------------------------------------------------------------

MSG_EXPORTAR_VAZIO = "Nenhuma tarefa aberta no momento 🎉"


def msg_exportar(groups) -> str:
    """Formata todas as tarefas abertas em texto copiável."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    _tz = ZoneInfo("America/Fortaleza")
    hoje = datetime.now(_tz).strftime("%d/%m/%Y")
    lines = [f"📋 Tarefas abertas — {hoje}\n"]
    for group in groups:
        lines.append(f"\n{group.name}")
        lines.append("─" * len(group.name))
        for t in group.tasks:
            status = "⏳" if t.status == "aguardando" else "•"
            due = ""
            if t.due_at:
                due = f" [{t.due_at.astimezone(_tz).strftime('%d/%m')}]"
            lines.append(f"{status} {t.title}{due}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pomodoro / Foco
# ---------------------------------------------------------------------------

def msg_foco_iniciado(work_min: int) -> str:
    return (
        f"🍅 Foco iniciado! {work_min} min de trabalho.\n\n"
        "Fecha as abas, silencia as notificações. Te aviso quando terminar."
    )


def msg_foco_work_done(work_min: int, break_min: int, ciclo: int) -> str:
    ciclo_txt = f"Ciclo {ciclo}" if ciclo > 1 else "Primeiro ciclo"
    return (
        f"⏰ {ciclo_txt} concluído! {work_min} min — muito bem.\n\n"
        f"Hora de descansar por {break_min} min. Levanta, bebe água ☕"
    )


def msg_foco_break_iniciado(break_min: int) -> str:
    return f"☕ Descanso iniciado. Te aviso em {break_min} min."


def msg_foco_break_done(ciclo: int) -> str:
    return (
        f"🔔 Descanso acabou! Ciclo {ciclo} completo.\n\n"
        "Pronto para mais um?"
    )


def msg_foco_encerrado(ciclos: int, work_min: int) -> str:
    total = ciclos * work_min
    s = "" if ciclos == 1 else "s"
    return (
        f"✅ Sessão encerrada! {ciclos} ciclo{s} — {total} min de foco.\n\n"
        "Bom trabalho!"
    )


MSG_FOCO_NENHUM_ATIVO = "Nenhuma sessão de foco ativa no momento."


# ---------------------------------------------------------------------------
# /proximos (Sugestão #5)
# ---------------------------------------------------------------------------

_DOW_CURTO = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

MSG_PROXIMOS_VAZIO = (
    "Nenhuma tarefa com prazo nos próximos dias 🙌\n"
    "Dia(s) livre(s) por enquanto!"
)

MSG_PROXIMOS_USO = "Uso: /proximos [dias]\nEx.: /proximos 7"


def msg_proximos(tasks: list, days: int) -> str:
    import pytz
    tz = pytz.timezone("America/Fortaleza")

    by_date: dict[str, list] = {}
    dates_order: list[str] = []
    for t in tasks:
        local_dt = t.due_at.astimezone(tz)
        dow = _DOW_CURTO[local_dt.weekday()]
        key = local_dt.strftime(f"%d/%m ({dow})")
        if key not in by_date:
            by_date[key] = []
            dates_order.append(key)
        by_date[key].append(t)

    n = len(tasks)
    s = "" if n == 1 else "s"
    lines = [f"📅 Próximos {days} dias — {n} tarefa{s}\n"]
    for date_key in dates_order:
        lines.append(f"  {date_key}")
        for t in by_date[date_key]:
            hora = f" {t.due_at.astimezone(tz).strftime('%H:%M')}" if t.due_at else ""
            est = f" · {t.estimate_min}min" if t.estimate_min else ""
            lista = f" [{t.task_list.name}]" if t.task_list else ""
            lines.append(f"    • {t.title}{hora}{est}{lista}")
        lines.append("")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# /pausar / /retomar (Sugestão #7)
# ---------------------------------------------------------------------------

MSG_PAUSAR_USO = "Uso: /pausar [dias]\nEx.: /pausar 3"

MSG_RETOMADO = (
    "De volta! ▶️\n\n"
    "Resumos diários, revisão semanal e lembretes reativados."
)


def msg_pausado(until_dt) -> str:
    import pytz
    tz = pytz.timezone("America/Fortaleza")
    dt_local = until_dt.astimezone(tz)
    return (
        f"Ok, descansando até {dt_local.strftime('%d/%m às %H:%M')} ⏸️\n\n"
        "Durante esse período não vou mandar resumo diário, revisão semanal nem lembretes.\n"
        "Quando quiser retomar antes, é só /retomar."
    )


# ---------------------------------------------------------------------------
# /projetos (2e-7)
# ---------------------------------------------------------------------------

MSG_PROJETOS_VAZIO = (
    "Nenhuma lista ainda 🗂️\n"
    "Crie listas e adicione tarefas para ver o progresso aqui."
)

MSG_PROGRESSO_VAZIO = MSG_PROJETOS_VAZIO


def _barra_progresso(done: int, total: int, width: int = 8) -> str:
    if total == 0:
        return "○" * width
    filled = round(done / total * width)
    return "●" * filled + "○" * (width - filled)


def msg_projetos(projetos) -> str:
    return msg_progresso(projetos)


def msg_progresso_limite(solicitado: int, maximo: int) -> str:
    return (
        f"⚠️ Período máximo suportado: {maximo} dias. "
        f"Exibindo os últimos {maximo} dias (você pediu {solicitado})."
    )


def msg_progresso(projetos, days: int = 30) -> str:
    import pytz
    from datetime import timezone as _tz
    tz = pytz.timezone("America/Fortaleza")

    periodo = f"últimos {days} dias" if days != 30 else "últimos 30 dias"
    lines = [f"📊 Progresso · {periodo}\n"]
    for p in projetos:
        total = p.open_count + p.done_30d
        barra = _barra_progresso(p.done_30d, total)
        pct = f"{p.done_30d}/{total} ✅" if total > 0 else "0/0"

        if p.last_touch:
            lt = p.last_touch
            if lt.tzinfo is None:
                lt = lt.replace(tzinfo=_tz.utc)
            toque = lt.astimezone(tz).strftime("%d/%m")
        else:
            toque = "—"

        emoji = lista_emoji(p.slug or "")
        lines.append(f"{emoji} {p.name}")
        lines.append(f"  {barra} {pct} · {p.open_count} abertas · toque {toque}")

        if p.is_couple:
            eu_label = p.user_name or "Eu"
            par_label = p.partner_name or "Par"
            lines.append(
                f"  👤 {eu_label}: {p.couple_mine}  "
                f"👤 {par_label}: {p.couple_partner}  "
                f"💑 Dos dois: {p.couple_joint}  "
                f"🏷️ Sem dono: {p.couple_unowned}"
            )

        lines.append("")

    return "\n".join(lines).rstrip()
