"""Construtores de teclados inline reutilizáveis."""
from __future__ import annotations

import uuid
from typing import Sequence

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

def kb_listas(lists: list, inbox_count: int) -> InlineKeyboardMarkup:
    from src.utils.textos import lista_emoji
    rows = []
    for lst in lists:
        count = lst.open_task_count
        emoji = lista_emoji(lst.slug)
        label = f"{emoji} {lst.name} — {count} {'aberta' if count == 1 else 'abertas'}"
        rows.append([InlineKeyboardButton(label, callback_data=f"view_list:{lst.id}")])

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

def kb_tasks(tasks: Sequence[Task], list_id: uuid.UUID | None = None) -> InlineKeyboardMarkup:
    """Título da tarefa (→ detalhe) + ✅ por linha."""
    rows = []
    for task in tasks:
        title = task.title[:32] + "…" if len(task.title) > 32 else task.title
        rows.append([
            InlineKeyboardButton(title, callback_data=f"task_dt:{task.id}"),
            InlineKeyboardButton("✅", callback_data=f"complete_task:{task.id}"),
        ])
    nav_row = [InlineKeyboardButton("← Voltar", callback_data="back_to_lists")]
    if list_id is not None:
        nav_row.append(
            InlineKeyboardButton("⚙️ Gerenciar", callback_data=f"manage_list:{list_id}")
        )
    rows.append(nav_row)
    return InlineKeyboardMarkup(rows)


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
    rows.append([InlineKeyboardButton("📥 Inbox", callback_data=f"adj:{task_idx}:-1")])
    return InlineKeyboardMarkup(rows)


def kb_inbox(tasks: Sequence[Task]) -> InlineKeyboardMarkup:
    """Título da tarefa (→ detalhe) + ✅ por linha para a Inbox."""
    rows = []
    for task in tasks:
        title = task.title[:32] + "…" if len(task.title) > 32 else task.title
        rows.append([
            InlineKeyboardButton(title, callback_data=f"task_dt:{task.id}"),
            InlineKeyboardButton("✅", callback_data=f"complete_task:{task.id}"),
        ])
    rows.append([InlineKeyboardButton("← Voltar", callback_data="back_to_lists")])
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# Detalhe de tarefa (F3)
# ---------------------------------------------------------------------------

def kb_task_detail(task: Task, listas: list[dict]) -> InlineKeyboardMarkup:
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

        r_row = []
        for val, label in [("daily", "🔁 Diária"), ("weekly", "🔁 Semanal"), ("monthly", "🔁 Mensal"), (None, "🚫 Sem rep.")]:
            mark = " ✓" if task.recurrence == val else ""
            r_row.append(InlineKeyboardButton(label + mark, callback_data=f"task_rec:{task.id}:{val or 'none'}"))
        rows.append(r_row)
        rows.append([
            InlineKeyboardButton("📂 Mover lista", callback_data=f"task_list:{task.id}"),
            InlineKeyboardButton("↑", callback_data=f"task_up:{task.id}"),
            InlineKeyboardButton("↓", callback_data=f"task_dn:{task.id}"),
        ])

    if task.list_id:
        rows.append([InlineKeyboardButton("← Voltar", callback_data=f"view_list:{task.list_id}")])
    else:
        rows.append([InlineKeyboardButton("← Voltar", callback_data="view_inbox")])

    return InlineKeyboardMarkup(rows)


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

def kb_blocker_types(task_id: uuid.UUID) -> InlineKeyboardMarkup:
    tid = str(task_id)
    return InlineKeyboardMarkup([
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
        [InlineKeyboardButton("🗑️ Não importa mais", callback_data=f"blk_t:{tid}:obsoleta")],
    ])


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
