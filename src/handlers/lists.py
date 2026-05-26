"""Handlers de listas: /listas, criar, renomear, arquivar (US-05, US-06)."""
from __future__ import annotations

import asyncio
import logging
import uuid

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.handlers.common import deny_unauthorized, is_authorized
from src.services import task_service
from src.utils import keyboards, textos

logger = logging.getLogger(__name__)

# Estados da conversa
_CREATE_NAME = 1
_RENAME_NAME = 2
_ADD_TASK_TITLE = 3


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

async def _show_lists(update_or_query, chat_id: int, *, via_message: bool = False) -> None:
    lists = await asyncio.to_thread(task_service.get_user_lists, chat_id)
    inbox_count = await asyncio.to_thread(task_service.get_inbox_count, chat_id)

    kb = keyboards.kb_listas(lists, inbox_count)

    if via_message:
        await update_or_query.reply_text(textos.MSG_SUAS_LISTAS, reply_markup=kb)
    else:
        await update_or_query.edit_message_text(textos.MSG_SUAS_LISTAS, reply_markup=kb)


# ---------------------------------------------------------------------------
# /listas
# ---------------------------------------------------------------------------

async def cmd_listas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
        await _show_lists(msg, update.effective_chat.id, via_message=True)
    except Exception:
        logger.exception("Erro em /listas")
        await msg.reply_text(textos.MSG_ERRO_GENERICO)


# ---------------------------------------------------------------------------
# Gerenciar lista
# ---------------------------------------------------------------------------

async def cb_manage_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    list_id = uuid.UUID(query.data.split(":")[1])
    await query.edit_message_reply_markup(reply_markup=keyboards.kb_gerenciar_lista(list_id))


async def cb_cancel_mgmt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    await _show_lists(query, update.effective_chat.id)


# ---------------------------------------------------------------------------
# Criar lista (ConversationHandler)
# ---------------------------------------------------------------------------

async def cb_start_new_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return ConversationHandler.END
    await query.edit_message_text(textos.MSG_PERGUNTAR_NOME_LISTA)
    return _CREATE_NAME


async def save_new_list_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return ConversationHandler.END

    name = (update.message.text or "").strip()
    if not name:
        await update.message.reply_text(textos.MSG_PERGUNTAR_NOME_LISTA)
        return _CREATE_NAME

    try:
        lst = await asyncio.to_thread(task_service.create_list, update.effective_chat.id, name)
        await update.message.reply_text(textos.MSG_LISTA_CRIADA.format(nome=lst.name if lst else name))
        await _show_lists(update.message, update.effective_chat.id, via_message=True)
    except Exception:
        logger.exception("Erro ao criar lista")
        await update.message.reply_text(textos.MSG_ERRO_GENERICO)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Renomear lista (ConversationHandler)
# ---------------------------------------------------------------------------

async def cb_start_rename_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return ConversationHandler.END

    list_id = uuid.UUID(query.data.split(":")[1])
    context.user_data["rename_list_id"] = str(list_id)

    lists = await asyncio.to_thread(task_service.get_user_lists, update.effective_chat.id)
    lista_info = next((l for l in lists if l.id == list_id), None)
    nome_atual = lista_info.name if lista_info else "lista"

    await query.edit_message_text(textos.MSG_PERGUNTAR_NOVO_NOME.format(nome=nome_atual))
    return _RENAME_NAME


async def save_rename_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return ConversationHandler.END

    new_name = (update.message.text or "").strip()
    if not new_name:
        await update.message.reply_text("Preciso de um nome para continuar. Qual será o novo nome?")
        return _RENAME_NAME

    list_id_str = context.user_data.get("rename_list_id", "")
    if not list_id_str:
        await update.message.reply_text(textos.MSG_ERRO_GENERICO)
        return ConversationHandler.END

    try:
        lst = await asyncio.to_thread(task_service.rename_list, uuid.UUID(list_id_str), new_name)
        await update.message.reply_text(textos.MSG_LISTA_RENOMEADA.format(nome=lst.name if lst else new_name))
        await _show_lists(update.message, update.effective_chat.id, via_message=True)
    except Exception:
        logger.exception("Erro ao renomear lista")
        await update.message.reply_text(textos.MSG_ERRO_GENERICO)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Arquivar lista
# ---------------------------------------------------------------------------

async def cb_archive_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    list_id = uuid.UUID(query.data.split(":")[1])
    lists = await asyncio.to_thread(task_service.get_user_lists, update.effective_chat.id)
    lista_info = next((l for l in lists if l.id == list_id), None)
    nome = lista_info.name if lista_info else "lista"

    await query.edit_message_text(
        textos.MSG_CONFIRMAR_ARQUIVAR.format(nome=nome),
        reply_markup=keyboards.kb_confirmar_arquivar(list_id),
    )


async def cb_do_archive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    list_id = uuid.UUID(query.data.split(":")[1])
    try:
        nome = await asyncio.to_thread(task_service.archive_list, list_id)
        if nome:
            await query.edit_message_text(textos.MSG_LISTA_ARQUIVADA.format(nome=nome))
        await _show_lists(query, update.effective_chat.id)
    except Exception:
        logger.exception("Erro ao arquivar lista %s", list_id)
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)


# ---------------------------------------------------------------------------
# Adicionar tarefa diretamente em lista (US-30)
# ---------------------------------------------------------------------------

async def cb_start_add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return ConversationHandler.END

    list_id_str = query.data.split(":")[1]
    context.user_data["add_task_list_id"] = list_id_str

    lists = await asyncio.to_thread(task_service.get_user_lists, update.effective_chat.id)
    lista_info = next((l for l in lists if str(l.id) == list_id_str), None)
    context.user_data["add_task_list_name"] = lista_info.name if lista_info else "lista"

    await query.edit_message_text(textos.MSG_ADD_TASK_TITULO)
    return _ADD_TASK_TITLE


async def save_add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return ConversationHandler.END

    title = (update.message.text or "").strip()
    if not title:
        await update.message.reply_text(textos.MSG_ADD_TASK_TITULO)
        return _ADD_TASK_TITLE

    list_id_str = context.user_data.get("add_task_list_id", "")
    list_name = context.user_data.get("add_task_list_name", "lista")
    if not list_id_str:
        await update.message.reply_text(textos.MSG_ERRO_GENERICO)
        return ConversationHandler.END

    try:
        task = await asyncio.to_thread(
            task_service.create_task_in_list,
            update.effective_chat.id,
            uuid.UUID(list_id_str),
            title,
        )
        await update.message.reply_text(
            textos.msg_add_task_ok(list_name),
            reply_markup=keyboards.kb_undo_capture(task.id),
        )
    except Exception:
        logger.exception("Erro ao adicionar tarefa na lista %s", list_id_str)
        await update.message.reply_text(textos.MSG_ERRO_GENERICO)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Cancelar conversa
# ---------------------------------------------------------------------------

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text(textos.MSG_CANCELADO)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# ConversationHandler exportado
# ---------------------------------------------------------------------------

list_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(cb_start_new_list, pattern="^new_list$"),
        CallbackQueryHandler(cb_start_rename_list, pattern=r"^rename_list:"),
        CallbackQueryHandler(cb_start_add_task, pattern=r"^add_to_list:"),
    ],
    states={
        _CREATE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_list_name)],
        _RENAME_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_rename_list)],
        _ADD_TASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_add_task)],
    },
    fallbacks=[CommandHandler("cancel", cmd_cancel)],
    per_message=False,
    name="list_management",
)
