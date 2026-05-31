"""Handlers de tarefas: ver lista e concluir (US-05, US-13)."""
from __future__ import annotations

import asyncio
import logging
import uuid

from telegram import Update
from telegram.ext import ContextTypes

from src.handlers.common import deny_unauthorized, is_authorized
from src.handlers import notify
from src.services import couple_service, task_service
from src.utils import keyboards, textos

logger = logging.getLogger(__name__)


async def cmd_ver(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ver <lista> — abre uma lista pelo nome ou parte do nome."""
    if not is_authorized(update):
        await deny_unauthorized(update)
        return

    msg = update.effective_message
    term = " ".join(context.args).strip() if context.args else ""
    if not term:
        await msg.reply_text("Use /ver seguido do nome da lista. Ex.: /ver Trabalho")
        return

    chat_id = update.effective_chat.id
    try:
        lst = await asyncio.to_thread(task_service.find_list_by_term, chat_id, term)
        if lst is None:
            await msg.reply_text(
                f'Não encontrei nenhuma lista com "{term}". Use /listas para ver todas.'
            )
            return

        tasks = await asyncio.to_thread(task_service.get_tasks_for_list, lst.id)
        if not tasks:
            texto = textos.MSG_LISTA_VAZIA.format(nome=lst.name)
        else:
            n = len(tasks)
            texto = f"📋 {lst.name} — {n} {'tarefa' if n == 1 else 'tarefas'}"

        await msg.reply_text(texto, reply_markup=keyboards.kb_tasks(tasks, list_id=lst.id))
    except Exception:
        logger.exception("Erro ao ver lista por termo '%s'", term)
        await msg.reply_text(textos.MSG_ERRO_GENERICO)


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
        task = await asyncio.to_thread(task_service.get_task_with_list, task_id)
        await asyncio.to_thread(task_service.complete_task, task_id)
        await _notify_if_couple(update, context, task)
        # Recarrega a lista após conclusão
        await _refresh_after_complete(query, update.effective_chat.id, task_id)
    except Exception:
        logger.exception("Erro ao concluir tarefa %s", task_id)
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)


async def _notify_if_couple(update: Update, context: ContextTypes.DEFAULT_TYPE, task) -> None:
    """Avisa o parceiro quando uma tarefa de casal é concluída."""
    if task is None or getattr(task, "couple_id", None) is None:
        return
    actor = (update.effective_user.full_name if update.effective_user else None) or "Seu par"
    if getattr(task, "couple_joint", False):
        texto = textos.msg_casal_concluiu_conjunta(actor, task.title)
    else:
        texto = textos.msg_casal_concluiu(actor, task.title)
    await notify.notify_partner(update.effective_chat.id, context.bot, texto)


async def _refresh_after_complete(query, chat_id: int, completed_task_id: str) -> None:
    lists = await asyncio.to_thread(task_service.get_user_lists, chat_id)
    inbox_count = await asyncio.to_thread(task_service.get_inbox_count, chat_id)
    couple_count = await asyncio.to_thread(task_service.get_couple_task_count, chat_id)

    await query.edit_message_text(
        f"{textos.msg_conclusao()}\n\n{textos.MSG_SUAS_LISTAS}",
        reply_markup=keyboards.kb_listas(lists, inbox_count, couple_count),
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
    couple_count = await asyncio.to_thread(task_service.get_couple_task_count, chat_id)

    await query.edit_message_text(
        textos.MSG_SUAS_LISTAS,
        reply_markup=keyboards.kb_listas(lists, inbox_count, couple_count),
    )


async def cb_view_casal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    try:
        chat_id = update.effective_chat.id
        tasks = await asyncio.to_thread(task_service.get_couple_tasks, chat_id)
        if not tasks:
            await query.edit_message_text(
                textos.MSG_CASAL_VAZIA,
                reply_markup=keyboards.kb_inbox([]),
            )
            return
        names = await asyncio.to_thread(couple_service.member_names, chat_id)
        await query.edit_message_text(
            textos.msg_casal(tasks, names),
            reply_markup=keyboards.kb_tasks(tasks),
        )
    except Exception:
        logger.exception("Erro ao ver tarefas do casal")
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
