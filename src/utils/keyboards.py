"""Construtores de teclados inline reutilizáveis."""
from __future__ import annotations

import uuid
from typing import Optional, Sequence

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.db.models import Task, TaskList


# ---------------------------------------------------------------------------
# Captura
# ---------------------------------------------------------------------------

def kb_undo_capture(task_id: uuid.UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ Desfazer", callback_data=f"undo_task:{task_id}")]
    ])


# ---------------------------------------------------------------------------
# Listas
# ---------------------------------------------------------------------------

def kb_listas(lists: list, inbox_count: int, couple_count: Optional[int] = None) -> InlineKeyboardMarkup:
    from src.utils.textos import lista_emoji
    rows = []
    for lst in lists:
        count = lst.open_task_count
        emoji = lista_emoji(lst.slug)
        label = f"{emoji} {lst.name} — {count} {'aberta' if count == 1 else 'abertas'}"
        rows.append([InlineKeyboardButton(label, callback_data=f"view_list:{lst.id}")])

    if couple_count is not None:
        casal_label = f"💞 Casal — {couple_count} {'tarefa' if couple_count == 1 else 'tarefas'}"
        rows.append([InlineKeyboardButton(casal_label, callback_data="view_casal")])

    inbox_label = f"📥 Inbox — {inbox_count} {'item' if inbox_count == 1 else 'itens'}"
    rows.append([InlineKeyboardButton(inbox_label, callback_data="view_inbox")])
    rows.append([InlineKeyboardButton("➕ Nova lista", callback_data="new_list")])
    return InlineKeyboardMarkup(rows)


def kb_gerenciar_lista(list_id: uuid.UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Renomear", callback_data=f"rename_list:{list_id}"),
            InlineKeyboardButton("📦 Arquivar", callback_data=f"archive_list:{list_id}"),
        ],
        [InlineKeyboardButton("🗓️ Janela de tempo", callback_data=f"list_window_cfg:{list_id}")],
        [InlineKeyboardButton("✖️ Cancelar", callback_data="cancel_mgmt")],
    ])


def kb_list_window_edit(list_id: uuid.UUID, current: str | None) -> InlineKeyboardMarkup:
    """Submenu para alterar a janela de tempo de uma lista existente (✓ na atual)."""
    def _mark(value: str | None) -> str:
        return " ✓" if (current or None) == value else ""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Sem janela" + _mark(None), callback_data=f"set_window:{list_id}:nenhuma")],
        [
            InlineKeyboardButton("📅 Diária" + _mark("dia"), callback_data=f"set_window:{list_id}:dia"),
            InlineKeyboardButton("🗓️ Semanal" + _mark("semana"), callback_data=f"set_window:{list_id}:semana"),
            InlineKeyboardButton("📆 Mensal" + _mark("mes"), callback_data=f"set_window:{list_id}:mes"),
        ],
        [InlineKeyboardButton("✖️ Cancelar", callback_data="cancel_mgmt")],
    ])


def kb_confirmar_arquivar(list_id: uuid.UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📦 Confirmar", callback_data=f"do_archive:{list_id}"),
            InlineKeyboardButton("✖️ Cancelar", callback_data="cancel_mgmt"),
        ]
    ])


# ---------------------------------------------------------------------------
# Tarefas
# ---------------------------------------------------------------------------

def _task_label(task: Task, max_len: int = 32) -> str:
    prefix = "🔒 " if task.blocked_by_task_id else ""
    title = task.title if len(task.title) <= max_len else task.title[:max_len - 1] + "…"
    return f"{prefix}{title}"


def kb_tasks(
    tasks: Sequence[Task],
    list_id: uuid.UUID | None = None,
    window: str | None = None,
    offset: int = 0,
) -> InlineKeyboardMarkup:
    """Título da tarefa (→ detalhe) + ✅ por linha.

    Para listas com janela de tempo (`window`), prepende uma linha de navegação
    de período: ◀ anterior · [período atual] · próximo ▶.
    """
    rows = []
    if window and list_id is not None:
        from src.utils.textos import periodo_label
        rows.append([
            InlineKeyboardButton("◀", callback_data=f"lwin:{list_id}:{offset - 1}"),
            InlineKeyboardButton(periodo_label(window, offset), callback_data=f"lwin:{list_id}:0"),
            InlineKeyboardButton("▶", callback_data=f"lwin:{list_id}:{offset + 1}"),
        ])
    for task in tasks:
        rows.append([
            InlineKeyboardButton(_task_label(task), callback_data=f"task_dt:{task.id}"),
            InlineKeyboardButton("✅", callback_data=f"complete_task:{task.id}"),
        ])
    nav_row = [InlineKeyboardButton("← Voltar", callback_data="back_to_lists")]
    if list_id is not None:
        nav_row.append(InlineKeyboardButton("➕ Adicionar", callback_data=f"add_to_list:{list_id}"))
        nav_row.append(InlineKeyboardButton("⚙️", callback_data=f"manage_list:{list_id}"))
    rows.append(nav_row)
    return InlineKeyboardMarkup(rows)


def kb_list_window() -> InlineKeyboardMarkup:
    """Escolha da janela de tempo ao criar uma lista."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Sem janela", callback_data="lwin_new:nenhuma")],
        [
            InlineKeyboardButton("📅 Diária", callback_data="lwin_new:dia"),
            InlineKeyboardButton("🗓️ Semanal", callback_data="lwin_new:semana"),
            InlineKeyboardButton("📆 Mensal", callback_data="lwin_new:mes"),
        ],
    ])


def kb_classificacao_resumo() -> InlineKeyboardMarkup:
    """Teclado exibido após o resumo da classificação da IA."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Aprovar tudo", callback_data="approve_capture")],
        [
            InlineKeyboardButton("✏️ Ajustar", callback_data="adjust_capture"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancel_capture"),
        ],
    ])


def kb_ajustar_tarefa(
    task_idx: int,
    listas: list[dict],
    show_couple: bool = False,
) -> InlineKeyboardMarkup:
    """Teclado de seleção de lista para uma tarefa durante o ajuste item a item."""
    from src.utils.textos import lista_emoji
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for i, lista in enumerate(listas):
        emoji = lista_emoji(lista["slug"])
        row.append(InlineKeyboardButton(
            f"{emoji} {lista['name']}",
            callback_data=f"adj:{task_idx}:{i}",
        ))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    bottom = [InlineKeyboardButton("📥 Inbox", callback_data=f"adj:{task_idx}:-1")]
    if show_couple:
        bottom.append(InlineKeyboardButton("💞 Casal", callback_data=f"adj:{task_idx}:-2"))
    rows.append(bottom)
    return InlineKeyboardMarkup(rows)


def kb_medicacoes(daily: Sequence[Task], weekly: Sequence[Task]) -> InlineKeyboardMarkup:
    """Checklist de medicações com ✅ por item e botão de nova medicação."""
    rows = []
    for task in list(daily) + list(weekly):
        title = task.title[:28] + "…" if len(task.title) > 28 else task.title
        rows.append([
            InlineKeyboardButton(title, callback_data=f"task_dt:{task.id}"),
            InlineKeyboardButton("✅", callback_data=f"complete_task:{task.id}"),
        ])
    rows.append([InlineKeyboardButton("➕ Nova medicação", callback_data="med_nova")])
    return InlineKeyboardMarkup(rows)


def kb_med_freq() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📅 Diária", callback_data="med_freq:daily"),
        InlineKeyboardButton("📆 Semanal", callback_data="med_freq:weekly"),
    ]])


def kb_med_pular() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Pular", callback_data="med_pular"),
    ]])


def kb_med_dow() -> InlineKeyboardMarkup:
    days = [
        ("Seg", 0), ("Ter", 1), ("Qua", 2), ("Qui", 3),
        ("Sex", 4), ("Sáb", 5), ("Dom", 6),
    ]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=f"med_dow:{i}") for label, i in days[:4]],
        [InlineKeyboardButton(label, callback_data=f"med_dow:{i}") for label, i in days[4:]],
    ])


def kb_tudo_group(tasks: Sequence[Task]) -> InlineKeyboardMarkup:
    """Keyboard para um grupo do /tudo — ✅ apenas para tarefas abertas; ⏳ sem botão para aguardando."""
    rows = []
    for task in tasks:
        if task.status == "aguardando":
            rows.append([InlineKeyboardButton(f"⏳ {_task_label(task)}", callback_data=f"task_dt:{task.id}")])
        else:
            rows.append([
                InlineKeyboardButton(_task_label(task), callback_data=f"task_dt:{task.id}"),
                InlineKeyboardButton("✅", callback_data=f"complete_task:{task.id}"),
            ])
    return InlineKeyboardMarkup(rows)


def kb_inbox(tasks: Sequence[Task]) -> InlineKeyboardMarkup:
    """Título da tarefa (→ detalhe) + ✅ por linha para a Inbox."""
    rows = []
    for task in tasks:
        rows.append([
            InlineKeyboardButton(_task_label(task), callback_data=f"task_dt:{task.id}"),
            InlineKeyboardButton("✅", callback_data=f"complete_task:{task.id}"),
        ])
    rows.append([InlineKeyboardButton("← Voltar", callback_data="back_to_lists")])
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# Detalhe de tarefa (F3)
# ---------------------------------------------------------------------------

def kb_task_detail(task: Task, listas: list[dict], subtasks=None, show_couple: bool = False, show_category: bool = False) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if task.status == "aguardando":
        rows.append([InlineKeyboardButton("✅ Desbloquear", callback_data=f"unblock:{task.id}")])
    else:
        rows.append([
            InlineKeyboardButton("✅ Concluir", callback_data=f"complete_task:{task.id}"),
            InlineKeyboardButton("😩 Travada", callback_data=f"blk_start:{task.id}"),
        ])

        q_row = []
        for q, label in [(1, "Q1 🔴"), (2, "Q2 🟡"), (3, "Q3 🔵"), (4, "Q4 ⚪")]:
            mark = " ✓" if task.quadrant == q else ""
            q_row.append(InlineKeyboardButton(label + mark, callback_data=f"task_q:{task.id}:{q}"))
        rows.append(q_row)

        e_row = []
        for e, label in [("alta", "⚡ Alta"), ("media", "🔋 Média"), ("baixa", "🪫 Baixa")]:
            mark = " ✓" if task.energy == e else ""
            e_row.append(InlineKeyboardButton(label + mark, callback_data=f"task_e:{task.id}:{e}"))
        rows.append(e_row)

        m_row = []
        for m, label in [(5, "5min"), (15, "15min"), (30, "30min"), (60, "1h"), (120, "2h+")]:
            mark = " ✓" if task.estimate_min == m else ""
            m_row.append(InlineKeyboardButton(label + mark, callback_data=f"task_m:{task.id}:{m}"))
        rows.append(m_row)

        rows.append([
            InlineKeyboardButton("📅 Hoje", callback_data=f"task_d:{task.id}:hoje"),
            InlineKeyboardButton("📅 Amanhã", callback_data=f"task_d:{task.id}:amanha"),
            InlineKeyboardButton("🚫 Sem prazo", callback_data=f"task_d:{task.id}:none"),
        ])
        rows.append([
            InlineKeyboardButton("+3 dias", callback_data=f"task_dd:{task.id}:3"),
            InlineKeyboardButton("+1 sem", callback_data=f"task_dd:{task.id}:7"),
            InlineKeyboardButton("+1 mês", callback_data=f"task_dd:{task.id}:30"),
            InlineKeyboardButton("📅 Digitar...", callback_data=f"task_dc:{task.id}"),
        ])

        r_row = []
        for val, label in [("daily", "🔁 Diária"), ("weekly", "🔁 Semanal"), ("quinzenal", "🔁 Quinzenal"), ("monthly", "🔁 Mensal")]:
            mark = " ✓" if task.recurrence == val else ""
            r_row.append(InlineKeyboardButton(label + mark, callback_data=f"task_rec:{task.id}:{val}"))
        rows.append(r_row)
        sem_rep_mark = " ✓" if not task.recurrence else ""
        rows.append([InlineKeyboardButton("🚫 Sem rep." + sem_rep_mark, callback_data=f"task_rec:{task.id}:none")])
        rows.append([
            InlineKeyboardButton("📂 Mover lista", callback_data=f"task_list:{task.id}"),
            InlineKeyboardButton("↑", callback_data=f"task_up:{task.id}"),
            InlineKeyboardButton("↓", callback_data=f"task_dn:{task.id}"),
        ])
        if subtasks:
            for s in subtasks[:5]:
                rows.append([InlineKeyboardButton(
                    f"✅ {s.title}", callback_data=f"sub_done:{s.id}:{task.id}"
                )])

        if show_category:
            cat = task.category
            med_mark = " ✓" if cat == "medicacao" else ""
            age_mark = " ✓" if cat == "agendamento" else ""
            sem_mark = " ✓" if cat is None else ""
            rows.append([
                InlineKeyboardButton("💊 Medicação" + med_mark, callback_data=f"task_cat:{task.id}:medicacao"),
                InlineKeyboardButton("📅 Agendamento" + age_mark, callback_data=f"task_cat:{task.id}:agendamento"),
                InlineKeyboardButton("🏷️ Nenhuma" + sem_mark, callback_data=f"task_cat:{task.id}:none"),
            ])

        nota_label = "📝 Nota ✓" if task.notes else "📝 Nota"
        rows.append([
            InlineKeyboardButton(nota_label, callback_data=f"task_note:{task.id}"),
            InlineKeyboardButton("✏️ Título", callback_data=f"task_title:{task.id}"),
        ])

        # Modo da tarefa de casal: individual (minha/do par), sem dono ou conjunta.
        if task.couple_id:
            joint = bool(getattr(task, "couple_joint", False))
            individual = task.assigned_to is not None
            shared_mark = " ✓" if (not joint and not individual) else ""
            joint_mark = " ✓" if joint else ""
            rows.append([
                InlineKeyboardButton("🙋 Minha vez", callback_data=f"task_assign:{task.id}:me"),
                InlineKeyboardButton("🤝 Vez do par", callback_data=f"task_assign:{task.id}:partner"),
            ])
            rows.append([
                InlineKeyboardButton("🆓 Sem dono" + shared_mark, callback_data=f"task_assign:{task.id}:shared"),
                InlineKeyboardButton("💞 Conjunta" + joint_mark, callback_data=f"task_assign:{task.id}:joint"),
            ])
            rows.append([InlineKeyboardButton("👤 Tornar pessoal", callback_data=f"task_couple:{task.id}:0")])
        elif show_couple:
            rows.append([InlineKeyboardButton("💞 Tornar do casal", callback_data=f"task_couple:{task.id}:1")])

    rows.append([InlineKeyboardButton("🗑️ Remover", callback_data=f"task_rm_ask:{task.id}")])

    if task.list_id:
        rows.append([InlineKeyboardButton("← Voltar", callback_data=f"view_list:{task.list_id}")])
    else:
        rows.append([InlineKeyboardButton("← Voltar", callback_data="view_inbox")])

    return InlineKeyboardMarkup(rows)


def kb_confirmar_remover(task_id) -> InlineKeyboardMarkup:
    """Confirmação de remoção de uma tarefa (descarte, não conclusão)."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑️ Sim, remover", callback_data=f"task_rm:{task_id}"),
        InlineKeyboardButton("✖️ Cancelar", callback_data=f"task_dt:{task_id}"),
    ]])


def kb_notif_ver_tarefa(task_id) -> InlineKeyboardMarkup:
    """Botão anexado à notificação ao par: abre o detalhe da tarefa (onde dá pra editar/remover)."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔍 Ver tarefa", callback_data=f"task_dt:{task_id}")
    ]])


def kb_notif_ver_casal() -> InlineKeyboardMarkup:
    """Botão para a notificação de várias tarefas compartilhadas de uma vez."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("💞 Ver tarefas do casal", callback_data="view_casal")
    ]])


def kb_nota(task_id: str, has_notes: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if has_notes:
        rows.append([InlineKeyboardButton("🗑️ Apagar nota", callback_data=f"task_note_del:{task_id}")])
    rows.append([InlineKeyboardButton("✖️ Cancelar", callback_data=f"task_note_cancel:{task_id}")])
    return InlineKeyboardMarkup(rows)


def kb_cancelar(task_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✖️ Cancelar", callback_data=f"task_title_cancel:{task_id}")
    ]])


def kb_mover_confirmar_duplicata(task_id: str, list_idx: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Sim, mover", callback_data=f"mv_force:{task_id}:{list_idx}"),
        InlineKeyboardButton("✖️ Cancelar", callback_data=f"task_dt:{task_id}"),
    ]])


def kb_mover_tarefa(task_id: str, listas: list[dict]) -> InlineKeyboardMarkup:
    from src.utils.textos import lista_emoji
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for i, lista in enumerate(listas):
        emoji = lista_emoji(lista["slug"])
        row.append(InlineKeyboardButton(f"{emoji} {lista['name']}", callback_data=f"mv:{i}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([
        InlineKeyboardButton("📥 Inbox", callback_data="mv:-1"),
        InlineKeyboardButton("✖️ Cancelar", callback_data=f"task_dt:{task_id}"),
    ])
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# /agora (F3)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Impedimentos (F4)
# ---------------------------------------------------------------------------

def kb_blocker_types(task_id: uuid.UUID, show_skip: bool = False) -> InlineKeyboardMarkup:
    tid = str(task_id)
    rows = [
        [
            InlineKeyboardButton("🌫️ Grande/vaga", callback_data=f"blk_t:{tid}:vaga_grande"),
            InlineKeyboardButton("🤔 Falta decidir", callback_data=f"blk_t:{tid}:decisao_pendente"),
        ],
        [
            InlineKeyboardButton("😖 Chata/pesada", callback_data=f"blk_t:{tid}:aversiva_energia"),
            InlineKeyboardButton("🧍 Depende de alguém", callback_data=f"blk_t:{tid}:pessoa"),
        ],
        [
            InlineKeyboardButton("🧩 Falta algo", callback_data=f"blk_t:{tid}:recurso_info"),
            InlineKeyboardButton("📅 Só em outra data", callback_data=f"blk_t:{tid}:data_externa"),
        ],
        [
            InlineKeyboardButton("🔗 Depende de outra tarefa", callback_data=f"blk_t:{tid}:tarefa_bloqueadora"),
        ],
        [InlineKeyboardButton("🗑️ Não importa mais", callback_data=f"blk_t:{tid}:obsoleta")],
    ]
    if show_skip:
        rows.append([InlineKeyboardButton("⏭️ Pular sem registrar", callback_data=f"ag_pular:{tid}")])
    return InlineKeyboardMarkup(rows)


def kb_blocker_nota(task_id: uuid.UUID) -> InlineKeyboardMarkup:
    tid = str(task_id)
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📝 Adicionar nota", callback_data=f"blk_nota_s:{tid}"),
        InlineKeyboardButton("✅ Pronto", callback_data=f"blk_nota_skip:{tid}"),
    ]])


_TASKS_PER_PAGE = 6


def kb_blocker_task_select(
    tasks: list[Task],
    blocked_task_id: uuid.UUID,
    page: int = 0,
) -> InlineKeyboardMarkup:
    """Teclado paginado para selecionar tarefa bloqueadora."""
    tid = str(blocked_task_id)
    start = page * _TASKS_PER_PAGE
    page_tasks = tasks[start : start + _TASKS_PER_PAGE]
    total_pages = (len(tasks) + _TASKS_PER_PAGE - 1) // _TASKS_PER_PAGE

    rows = []
    for task in page_tasks:
        label = task.title[:40] + ("…" if len(task.title) > 40 else "")
        rows.append([InlineKeyboardButton(label, callback_data=f"blk_dep:{tid}:{task.id}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀ Anterior", callback_data=f"blk_tp:{tid}:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Próxima ▶", callback_data=f"blk_tp:{tid}:{page + 1}"))
    if nav:
        rows.append(nav)

    return InlineKeyboardMarkup(rows)


def kb_blocker_pessoa(task_id: uuid.UUID) -> InlineKeyboardMarkup:
    tid = str(task_id)
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⏳ Aguardando", callback_data=f"blk_wait:{tid}"),
        InlineKeyboardButton("🔔 Criar cobrança", callback_data=f"blk_cobrar:{tid}"),
    ]])


def kb_blocker_cobrar_date(task_id: uuid.UUID) -> InlineKeyboardMarkup:
    tid = str(task_id)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Amanhã", callback_data=f"blk_cd:{tid}:1"),
            InlineKeyboardButton("Em 3 dias", callback_data=f"blk_cd:{tid}:3"),
            InlineKeyboardButton("Em 1 semana", callback_data=f"blk_cd:{tid}:7"),
        ],
    ])


def kb_blocker_next_step(task_id: uuid.UUID) -> InlineKeyboardMarkup:
    tid = str(task_id)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Começar por aqui", callback_data=f"blk_nok:{tid}")],
        [InlineKeyboardButton("🔁 Sugerir outro passo", callback_data=f"blk_nretry:{tid}")],
    ])


def kb_blocker_decidir(task_id: uuid.UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👍 Criar tarefa 'decidir'", callback_data=f"blk_dok:{task_id}"),
    ]])


def kb_blocker_recurso(task_id: uuid.UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👍 Criar esse passo", callback_data=f"blk_rook:{task_id}"),
    ]])


def kb_blocker_data_externa(task_id: uuid.UUID) -> InlineKeyboardMarkup:
    tid = str(task_id)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1 semana", callback_data=f"blk_dd:{tid}:7"),
            InlineKeyboardButton("2 semanas", callback_data=f"blk_dd:{tid}:14"),
            InlineKeyboardButton("1 mês", callback_data=f"blk_dd:{tid}:30"),
        ],
    ])


def kb_blocker_obsoleta(task_id: uuid.UUID) -> InlineKeyboardMarkup:
    tid = str(task_id)
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑️ Arquivar sem culpa", callback_data=f"blk_arc:{tid}"),
        InlineKeyboardButton("↩️ Deixa, ainda quero", callback_data=f"blk_keep:{tid}"),
    ]])


# ---------------------------------------------------------------------------
# Revisão semanal (US-16)
# ---------------------------------------------------------------------------

def kb_revisao_abertura() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👍 Bora", callback_data="rv_start"),
        InlineKeyboardButton("⏰ Agora não", callback_data="rv_skip"),
    ]])


def kb_revisao_tarefa(task_id) -> InlineKeyboardMarkup:
    tid = str(task_id)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Reagendar", callback_data=f"rv_rg:{tid}"),
            InlineKeyboardButton("🗑️ Arquivar", callback_data=f"rv_arch:{tid}"),
        ],
        [InlineKeyboardButton("✋ Manter", callback_data=f"rv_ok:{tid}")],
    ])


def kb_revisao_reagendar(task_id) -> InlineKeyboardMarkup:
    tid = str(task_id)
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Amanhã", callback_data=f"rv_rd:{tid}:1"),
        InlineKeyboardButton("1 semana", callback_data=f"rv_rd:{tid}:7"),
        InlineKeyboardButton("2 semanas", callback_data=f"rv_rd:{tid}:14"),
    ]])


def kb_revisao_espera(task_id) -> InlineKeyboardMarkup:
    tid = str(task_id)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔔 Cobrar agora", callback_data=f"rv_wc:{tid}"),
            InlineKeyboardButton("✅ Destravar", callback_data=f"rv_wu:{tid}"),
        ],
        [
            InlineKeyboardButton("🗑️ Arquivar", callback_data=f"rv_wa:{tid}"),
            InlineKeyboardButton("⏳ Seguir esperando", callback_data=f"rv_ws:{tid}"),
        ],
    ])


# ---------------------------------------------------------------------------
# /config (US-20)
# ---------------------------------------------------------------------------

def kb_config() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏰ Horário diário", callback_data="cfg_daily"),
            InlineKeyboardButton("🗓️ Dia da revisão", callback_data="cfg_rev_dow"),
        ],
        [
            InlineKeyboardButton("🔕 Desativar diário", callback_data="cfg_off_daily"),
            InlineKeyboardButton("🔕 Desativar revisão", callback_data="cfg_off_rev"),
        ],
    ])


def kb_config_daily_time() -> InlineKeyboardMarkup:
    opts = [("6:00", "06:00"), ("7:00", "07:00"), ("8:00", "08:00"), ("9:00", "09:00")]
    row = [InlineKeyboardButton(label, callback_data=f"cfg_dt:{val}") for label, val in opts]
    return InlineKeyboardMarkup([row, [InlineKeyboardButton("← Voltar", callback_data="cfg_back")]])


def kb_config_review_dow() -> InlineKeyboardMarkup:
    days = [("Seg", "0"), ("Ter", "1"), ("Qua", "2"), ("Qui", "3"),
            ("Sex", "4"), ("Sáb", "5"), ("Dom", "6")]
    row1 = [InlineKeyboardButton(l, callback_data=f"cfg_rdow:{v}") for l, v in days[:4]]
    row2 = [InlineKeyboardButton(l, callback_data=f"cfg_rdow:{v}") for l, v in days[4:]]
    return InlineKeyboardMarkup([row1, row2, [InlineKeyboardButton("← Voltar", callback_data="cfg_back")]])


def kb_config_review_time() -> InlineKeyboardMarkup:
    opts = [("8:00", "08:00"), ("18:00", "18:00"), ("19:00", "19:00"), ("20:00", "20:00")]
    row = [InlineKeyboardButton(label, callback_data=f"cfg_rt:{val}") for label, val in opts]
    return InlineKeyboardMarkup([row, [InlineKeyboardButton("← Voltar", callback_data="cfg_back")]])


def kb_agora_tempo() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("5min", callback_data="ag_t:5"),
            InlineKeyboardButton("15min", callback_data="ag_t:15"),
            InlineKeyboardButton("30min", callback_data="ag_t:30"),
        ],
        [
            InlineKeyboardButton("1h", callback_data="ag_t:60"),
            InlineKeyboardButton("2h+", callback_data="ag_t:120"),
        ],
    ])


def kb_agora_energia() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⚡ Alta", callback_data="ag_e:alta"),
        InlineKeyboardButton("🔋 Média", callback_data="ag_e:media"),
        InlineKeyboardButton("🪫 Baixa", callback_data="ag_e:baixa"),
    ]])


def kb_agora_task(task_id: uuid.UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Concluí!", callback_data=f"ag_ok:{task_id}")],
        [
            InlineKeyboardButton("⏭️ Outra", callback_data=f"ag_nx:{task_id}"),
            InlineKeyboardButton("😩 Travada", callback_data=f"blk_start:{task_id}"),
        ],
        [InlineKeyboardButton("😴 Adiar", callback_data=f"ag_ad:{task_id}")],
    ])


def kb_lembrete(task_id: uuid.UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Concluir", callback_data=f"complete_task:{task_id}"),
        InlineKeyboardButton("😴 Adiar", callback_data=f"ag_ad:{task_id}"),
    ]])


def kb_agora_adiar(task_id: uuid.UUID) -> InlineKeyboardMarkup:
    tid = str(task_id)
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Amanhã", callback_data=f"ag_adf:{tid}:1"),
        InlineKeyboardButton("3 dias", callback_data=f"ag_adf:{tid}:3"),
        InlineKeyboardButton("1 semana", callback_data=f"ag_adf:{tid}:7"),
    ]])


# ---------------------------------------------------------------------------
# Energia do dia (Sugestão #1)
# ---------------------------------------------------------------------------

def kb_energia_do_dia() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⚡ Alta", callback_data="edia:alta"),
        InlineKeyboardButton("🔋 Média", callback_data="edia:media"),
        InlineKeyboardButton("🪫 Baixa", callback_data="edia:baixa"),
    ]])


# ---------------------------------------------------------------------------
# Prazo vencido (Sugestão #4)
# ---------------------------------------------------------------------------

def kb_prazo_vencido(task_id: uuid.UUID) -> InlineKeyboardMarkup:
    tid = str(task_id)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Adiar 1 dia", callback_data=f"od_adiar:{tid}"),
            InlineKeyboardButton("👀 Ver tarefa", callback_data=f"task_dt:{tid}"),
        ],
        [InlineKeyboardButton("🗑️ Arquivar", callback_data=f"od_arch:{tid}")],
    ])


# ---------------------------------------------------------------------------
# Pomodoro / Foco
# ---------------------------------------------------------------------------

def kb_foco_cancelar() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⏹ Cancelar foco", callback_data="foco_cancel"),
    ]])


def kb_foco_work_done(break_min: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(f"☕ Descansar {break_min}min", callback_data=f"foco_descanso:{break_min}"),
        InlineKeyboardButton("⏭️ Pular", callback_data="foco_pular"),
    ]])


def kb_foco_break_done(work_min: int, break_min: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🔄 Mais um ciclo ({work_min}min)", callback_data=f"foco_ciclo:{work_min}:{break_min}")],
        [InlineKeyboardButton("✅ Encerrar", callback_data="foco_encerrar")],
    ])


# ---------------------------------------------------------------------------
# /ordem — cadeias de dependência (v1.18.0)
# ---------------------------------------------------------------------------

_INDENT = "   "  # 3 espaços por nível de indentação
_MAX_TITLE = 36  # caracteres visíveis no botão


def _chain_button_label(task: Task, depth: int, is_ready: bool) -> str:
    icon = "▶" if is_ready else "🔒"
    indent = _INDENT * depth
    title = task.title if len(task.title) <= _MAX_TITLE else task.title[:_MAX_TITLE - 1] + "…"
    return f"{indent}{icon} {title}"


def kb_ordem(chains: list[list[Task]]) -> InlineKeyboardMarkup:
    """Teclado para /ordem: uma linha por tarefa, indentação por nível.

    Cada cadeia exibe do objetivo final (índice 0, sem indentação) até a tarefa
    que pode ser feita agora (último índice, mais indentada).
    Separadores de cadeia são botões não-funcionais com o número da cadeia.
    """
    rows: list[list[InlineKeyboardButton]] = []
    for i, chain in enumerate(chains, start=1):
        rows.append([
            InlineKeyboardButton(f"🔗 Cadeia {i}", callback_data="noop"),
        ])
        for depth, task in enumerate(chain):
            is_ready = (depth == len(chain) - 1)
            label = _chain_button_label(task, depth, is_ready)
            rows.append([InlineKeyboardButton(label, callback_data=f"task_dt:{task.id}")])
    return InlineKeyboardMarkup(rows)
