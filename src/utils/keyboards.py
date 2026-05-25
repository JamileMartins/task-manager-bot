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

def kb_listas(lists_with_count: list[tuple[TaskList, int]], inbox_count: int) -> InlineKeyboardMarkup:
    from src.utils.textos import lista_emoji
    rows = []
    for lst, count in lists_with_count:
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

    rows.append([InlineKeyboardButton("✅ Concluir", callback_data=f"complete_task:{task.id}")])

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
            InlineKeyboardButton("😴 Adiar", callback_data=f"ag_ad:{task_id}"),
        ],
    ])
