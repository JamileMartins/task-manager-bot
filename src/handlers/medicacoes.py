"""Handler de medicações — checklist diário/semanal (US-32)."""
from __future__ import annotations

import asyncio
import logging

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

_MED_NOME = 1
_MED_FREQ = 2


async def cmd_medicacoes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
        chat_id = update.effective_chat.id
        daily, weekly = await asyncio.to_thread(task_service.get_medicacoes, chat_id)
        if not daily and not weekly:
            await msg.reply_text(
                textos.MSG_MED_VAZIA,
                reply_markup=keyboards.kb_medicacoes([], []),
            )
            return
        await msg.reply_text(
            textos.msg_medicacoes(daily, weekly),
            reply_markup=keyboards.kb_medicacoes(daily, weekly),
        )
    except Exception:
        logger.exception("Erro em /medicacoes")
        await msg.reply_text(textos.MSG_ERRO_GENERICO)


async def cb_med_nova_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return ConversationHandler.END
    await query.message.reply_text(textos.MSG_MED_PEDIR_NOME)
    return _MED_NOME


async def save_med_nome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return ConversationHandler.END
    title = (update.message.text or "").strip()
    if not title:
        await update.message.reply_text(textos.MSG_MED_PEDIR_NOME)
        return _MED_NOME
    context.user_data["med_title"] = title
    await update.message.reply_text(
        textos.MSG_MED_PEDIR_FREQ,
        reply_markup=keyboards.kb_med_freq(),
    )
    return _MED_FREQ


async def save_med_freq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return ConversationHandler.END
    recurrence = query.data.split(":")[1]
    title = context.user_data.pop("med_title", "")
    if not title:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return ConversationHandler.END
    try:
        await asyncio.to_thread(
            task_service.create_medicacao,
            update.effective_chat.id,
            title,
            recurrence,
        )
        await query.edit_message_text(textos.msg_med_ok(title, recurrence))
    except Exception:
        logger.exception("Erro ao criar medicação")
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
    return ConversationHandler.END


async def cmd_cancel_med(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return ConversationHandler.END
    context.user_data.pop("med_title", None)
    await update.message.reply_text(textos.MSG_CANCELADO)
    return ConversationHandler.END


medicacoes_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(cb_med_nova_start, pattern=r"^med_nova$"),
    ],
    states={
        _MED_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_med_nome)],
        _MED_FREQ: [CallbackQueryHandler(save_med_freq, pattern=r"^med_freq:")],
    },
    fallbacks=[CommandHandler("cancel", cmd_cancel_med)],
    per_message=False,
    name="medicacoes",
)
