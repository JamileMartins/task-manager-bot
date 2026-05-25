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
    """Botão ✅ numerado para cada tarefa + botão Voltar."""
    rows = []
    # Botões de conclusão agrupados em linhas de 4
    check_row: list[InlineKeyboardButton] = []
    for i, task in enumerate(tasks, start=1):
        check_row.append(
            InlineKeyboardButton(f"✅ {i}", callback_data=f"complete_task:{task.id}")
        )
        if len(check_row) == 4:
            rows.append(check_row)
            check_row = []
    if check_row:
        rows.append(check_row)

    nav_row = [InlineKeyboardButton("← Voltar", callback_data="back_to_lists")]
    if list_id is not None:
        nav_row.append(
            InlineKeyboardButton("⚙️ Gerenciar", callback_data=f"manage_list:{list_id}")
        )
    rows.append(nav_row)
    return InlineKeyboardMarkup(rows)


def kb_inbox(tasks: Sequence[Task]) -> InlineKeyboardMarkup:
    """Botão ✅ numerado para tarefas da Inbox + botão Voltar."""
    rows = []
    check_row: list[InlineKeyboardButton] = []
    for i, task in enumerate(tasks, start=1):
        check_row.append(
            InlineKeyboardButton(f"✅ {i}", callback_data=f"complete_task:{task.id}")
        )
        if len(check_row) == 4:
            rows.append(check_row)
            check_row = []
    if check_row:
        rows.append(check_row)
    rows.append([InlineKeyboardButton("← Voltar", callback_data="back_to_lists")])
    return InlineKeyboardMarkup(rows)
