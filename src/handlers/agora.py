"""Handler /agora — sugere UMA tarefa baseada em tempo e energia (US-12)."""
from __future__ import annotations

import asyncio
import logging
import uuid

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from src.handlers.common import deny_unauthorized, is_authorized
from src.services import task_service
from src.utils import keyboards, textos

logger = logging.getLogger(__name__)

_TEMPO_KEY = "agora_tempo"
_ENERGIA_KEY = "agora_energia"
_EXCLUIDOS_KEY = "agora_excluidos"


async def cmd_agora(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    context.user_data[_EXCLUIDOS_KEY] = []
    await msg.reply_text(
        textos.MSG_AGORA_TEMPO,
        reply_markup=keyboards.kb_agora_tempo(),
    )


async def cb_agora_tempo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    tempo_min = int(query.data.split(":")[1])
    context.user_data[_TEMPO_KEY] = tempo_min
    await query.edit_message_text(
        textos.MSG_AGORA_ENERGIA,
        reply_markup=keyboards.kb_agora_energia(),
    )


async def cb_agora_energia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    energia = query.data.split(":")[1]
    context.user_data[_ENERGIA_KEY] = energia
    await _show_agora_task(query, update, context)


async def cb_agora_outra(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    task_id_str = query.data.split(":")[1]
    excluidos: list[str] = context.user_data.get(_EXCLUIDOS_KEY, [])
    excluidos.append(task_id_str)
    context.user_data[_EXCLUIDOS_KEY] = excluidos
    await _show_agora_task(query, update, context)


async def cb_agora_concluir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    task_id = query.data.split(":")[1]
    try:
        await asyncio.to_thread(task_service.complete_task, task_id)
        await query.edit_message_text(textos.msg_conclusao())
    except Exception:
        logger.exception("Erro ao concluir tarefa pelo /agora")
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)


async def cb_agora_adiar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    task_id = uuid.UUID(query.data.split(":")[1])
    await query.edit_message_text(
        textos.MSG_AGORA_ADIAR_QUANDO,
        reply_markup=keyboards.kb_agora_adiar(task_id),
    )


async def cb_agora_adiar_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    parts = query.data.split(":")
    task_id = parts[1]
    days = int(parts[2])
    try:
        await asyncio.to_thread(task_service.reschedule_task, task_id, days)
        await query.edit_message_text(textos.msg_agora_adiada(days))
    except Exception:
        logger.exception("Erro ao adiar tarefa do /agora")
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)


async def _show_agora_task(
    query,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    chat_id = update.effective_chat.id
    tempo_min: int = context.user_data.get(_TEMPO_KEY, 30)
    energia: str = context.user_data.get(_ENERGIA_KEY, "media")
    excluidos_str: list[str] = context.user_data.get(_EXCLUIDOS_KEY, [])
    excluidos = [uuid.UUID(s) for s in excluidos_str]

    try:
        task = await asyncio.to_thread(
            task_service.get_task_for_agora, chat_id, tempo_min, energia, excluidos
        )

        if task is None:
            task = await asyncio.to_thread(
                task_service.get_lightest_task, chat_id, excluidos
            )
            if task is None:
                await query.edit_message_text(textos.MSG_AGORA_NADA)
                return
            await query.edit_message_text(
                textos.msg_agora_tarefa(task, fallback=True),
                reply_markup=keyboards.kb_agora_task(task.id),
            )
        else:
            await query.edit_message_text(
                textos.msg_agora_tarefa(task),
                reply_markup=keyboards.kb_agora_task(task.id),
            )
    except Exception:
        logger.exception("Erro ao buscar tarefa para /agora")
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
