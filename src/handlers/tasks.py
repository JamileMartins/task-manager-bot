"""Handlers de tarefas: ver lista e concluir (US-05, US-13)."""
from __future__ import annotations

import asyncio
import logging
import uuid

from telegram import Update
from telegram.ext import ContextTypes

from src.handlers.common import deny_unauthorized, is_authorized
from src.services import task_service
from src.utils import keyboards, textos

logger = logging.getLogger(__name__)


async def cb_view_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    list_id = uuid.UUID(query.data.split(":")[1])
    try:
        tasks = await asyncio.to_thread(task_service.get_tasks_for_list, list_id)

        # Obtém nome da lista a partir da ListInfo para montar cabeçalho
        lists = await asyncio.to_thread(task_service.get_user_lists, update.effective_chat.id)
        lista_info = next((l for l in lists if l.id == list_id), None)
        nome = lista_info.name if lista_info else "Lista"

        if not tasks:
            texto = textos.MSG_LISTA_VAZIA.format(nome=nome)
            kb = keyboards.kb_tasks([], list_id=list_id)
        else:
            n = len(tasks)
            texto = f"📋 {nome} — {n} {'tarefa' if n == 1 else 'tarefas'}"
            kb = keyboards.kb_tasks(tasks, list_id=list_id)

        await query.edit_message_text(texto, reply_markup=kb)
    except Exception:
        logger.exception("Erro ao ver lista %s", list_id)
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)


async def cb_view_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    try:
        tasks = await asyncio.to_thread(task_service.get_inbox_tasks, update.effective_chat.id)
        if not tasks:
            await query.edit_message_text(
                textos.MSG_INBOX_VAZIA,
                reply_markup=keyboards.kb_inbox([]),
            )
            return

        lines = [textos.msg_inbox_titulo(len(tasks))]
        for i, t in enumerate(tasks, 1):
            lines.append(f"{i}. {t.title}")

        await query.edit_message_text("\n".join(lines), reply_markup=keyboards.kb_inbox(tasks))
    except Exception:
        logger.exception("Erro ao ver inbox")
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)


async def cb_complete_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer(textos.msg_conclusao())
    if not is_authorized(update):
        return

    task_id = query.data.split(":")[1]
    try:
        await asyncio.to_thread(task_service.complete_task, task_id)
        # Recarrega a lista após conclusão
        await _refresh_after_complete(query, update.effective_chat.id, task_id)
    except Exception:
        logger.exception("Erro ao concluir tarefa %s", task_id)
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)


async def _refresh_after_complete(query, chat_id: int, completed_task_id: str) -> None:
    lists = await asyncio.to_thread(task_service.get_user_lists, chat_id)
    inbox_count = await asyncio.to_thread(task_service.get_inbox_count, chat_id)

    await query.edit_message_text(
        f"{textos.msg_conclusao()}\n\n{textos.MSG_SUAS_LISTAS}",
        reply_markup=keyboards.kb_listas(lists, inbox_count),
    )


async def cb_back_to_lists(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    await _show_lists(query, update.effective_chat.id)


async def _show_lists(query, chat_id: int) -> None:
    lists = await asyncio.to_thread(task_service.get_user_lists, chat_id)
    inbox_count = await asyncio.to_thread(task_service.get_inbox_count, chat_id)

    await query.edit_message_text(
        textos.MSG_SUAS_LISTAS,
        reply_markup=keyboards.kb_listas(lists, inbox_count),
    )
