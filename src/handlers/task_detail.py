"""Visão detalhada e edição de atributos de tarefa (US-07, 08, 09, 10, 11)."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta

import pytz
from telegram import Update
from telegram.ext import ContextTypes

from src.config import DEFAULT_TIMEZONE
from src.handlers.common import deny_unauthorized, is_authorized
from src.services import task_service
from src.utils import keyboards, textos

logger = logging.getLogger(__name__)

_MOVE_TASK_KEY = "move_task_id"
_MOVE_LISTAS_KEY = "move_listas"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _refresh_detail(query, task_id: uuid.UUID, context: ContextTypes.DEFAULT_TYPE) -> None:
    listas = context.user_data.get(_MOVE_LISTAS_KEY, [])
    task = await asyncio.to_thread(task_service.get_task_with_list, task_id)
    if task is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return
    await query.edit_message_text(
        textos.msg_task_detail(task),
        reply_markup=keyboards.kb_task_detail(task, listas),
    )


# ---------------------------------------------------------------------------
# Abrir detalhe
# ---------------------------------------------------------------------------

async def cb_task_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id = uuid.UUID(query.data.split(":")[1])

    listas_info = await asyncio.to_thread(
        task_service.get_user_lists, update.effective_chat.id
    )
    listas_dicts = [
        {"name": l.name, "slug": l.slug, "id": str(l.id)} for l in listas_info
    ]
    context.user_data[_MOVE_LISTAS_KEY] = listas_dicts
    context.user_data[_MOVE_TASK_KEY] = str(task_id)

    try:
        task = await asyncio.to_thread(task_service.get_task_with_list, task_id)
        if task is None:
            await query.edit_message_text(textos.MSG_ERRO_GENERICO)
            return
        await query.edit_message_text(
            textos.msg_task_detail(task),
            reply_markup=keyboards.kb_task_detail(task, listas_dicts),
        )
    except Exception:
        logger.exception("Erro ao abrir detalhe da tarefa %s", task_id)
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)


# ---------------------------------------------------------------------------
# Editar quadrante (US-08)
# ---------------------------------------------------------------------------

async def cb_task_set_quadrant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    _, task_id_str, q_str = query.data.split(":")
    task_id = uuid.UUID(task_id_str)
    await asyncio.to_thread(task_service.update_task_attrs, task_id, quadrant=int(q_str))
    await _refresh_detail(query, task_id, context)


# ---------------------------------------------------------------------------
# Editar energia e estimativa (US-10)
# ---------------------------------------------------------------------------

async def cb_task_set_energy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    parts = query.data.split(":")
    task_id = uuid.UUID(parts[1])
    await asyncio.to_thread(task_service.update_task_attrs, task_id, energy=parts[2])
    await _refresh_detail(query, task_id, context)


async def cb_task_set_estimate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    parts = query.data.split(":")
    task_id = uuid.UUID(parts[1])
    await asyncio.to_thread(task_service.update_task_attrs, task_id, estimate_min=int(parts[2]))
    await _refresh_detail(query, task_id, context)


# ---------------------------------------------------------------------------
# Recorrência (US-18)
# ---------------------------------------------------------------------------

async def cb_task_set_recurrence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    parts = query.data.split(":")
    task_id = uuid.UUID(parts[1])
    value = None if parts[2] == "none" else parts[2]
    await asyncio.to_thread(task_service.update_task_attrs, task_id, recurrence=value)
    await _refresh_detail(query, task_id, context)


# ---------------------------------------------------------------------------
# Definir prazo (US-09)
# ---------------------------------------------------------------------------

async def cb_task_set_due(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    parts = query.data.split(":")
    task_id = uuid.UUID(parts[1])
    when = parts[2]

    tz = pytz.timezone(DEFAULT_TIMEZONE)
    now = datetime.now(tz)
    if when == "hoje":
        due: datetime | None = now.replace(hour=23, minute=59, second=0, microsecond=0)
    elif when == "amanha":
        due = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        due = None

    await asyncio.to_thread(task_service.update_task_attrs, task_id, due_at=due)
    await _refresh_detail(query, task_id, context)


# ---------------------------------------------------------------------------
# Mover tarefa entre listas (US-07)
# ---------------------------------------------------------------------------

async def cb_task_start_move(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id_str = query.data.split(":")[1]
    context.user_data[_MOVE_TASK_KEY] = task_id_str

    listas = context.user_data.get(_MOVE_LISTAS_KEY)
    if not listas:
        listas_info = await asyncio.to_thread(
            task_service.get_user_lists, update.effective_chat.id
        )
        listas = [{"name": l.name, "slug": l.slug, "id": str(l.id)} for l in listas_info]
        context.user_data[_MOVE_LISTAS_KEY] = listas

    await query.edit_message_text(
        "Para qual lista mover?",
        reply_markup=keyboards.kb_mover_tarefa(task_id_str, listas),
    )


async def cb_task_move_to(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    list_idx = int(query.data.split(":")[1])
    task_id_str = context.user_data.get(_MOVE_TASK_KEY)
    listas = context.user_data.get(_MOVE_LISTAS_KEY, [])

    if not task_id_str:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    task_id = uuid.UUID(task_id_str)
    if list_idx == -1:
        new_list_id = None
    elif 0 <= list_idx < len(listas):
        new_list_id: uuid.UUID | None = uuid.UUID(listas[list_idx]["id"])
    else:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    try:
        await asyncio.to_thread(task_service.update_task_attrs, task_id, list_id=new_list_id)
        await _refresh_detail(query, task_id, context)
    except Exception:
        logger.exception("Erro ao mover tarefa %s", task_id)
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)


# ---------------------------------------------------------------------------
# Ordenação manual (US-11)
# ---------------------------------------------------------------------------

async def cb_task_reorder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    parts = query.data.split(":")
    direction = "up" if parts[0] == "task_up" else "down"
    task_id = uuid.UUID(parts[1])
    await asyncio.to_thread(task_service.reorder_task, task_id, direction)
    await _refresh_detail(query, task_id, context)
