"""Handler de medicações — checklist diário/semanal (US-32)."""
from __future__ import annotations

import asyncio
import logging
import re

from telegram import Update
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
_MED_TIME = 2
_MED_FREQ = 3
_MED_DOW = 4

_TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")


async def cmd_medicacoes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    try:
        from telegram.constants import ChatAction
        await msg.reply_chat_action(ChatAction.TYPING)
        chat_id = update.effective_chat.id
        daily, weekly, completed_hoje = await asyncio.to_thread(task_service.get_medicacoes, chat_id)
        if not daily and not weekly and not completed_hoje:
            await msg.reply_text(
                textos.MSG_MED_VAZIA,
                reply_markup=keyboards.kb_medicacoes([], []),
            )
            return
        await msg.reply_text(
            textos.msg_medicacoes(daily, weekly, completed_hoje),
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
        textos.MSG_MED_PEDIR_HORARIO,
        reply_markup=keyboards.kb_med_pular(),
    )
    return _MED_TIME


async def save_med_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return ConversationHandler.END
    text = (update.message.text or "").strip()
    if not _TIME_RE.match(text):
        await update.message.reply_text(
            "Formato inválido. Use HH:MM, ex: 08:00\n\nOu toque em Pular.",
            reply_markup=keyboards.kb_med_pular(),
        )
        return _MED_TIME
    context.user_data["med_time"] = text
    await update.message.reply_text(
        textos.MSG_MED_PEDIR_FREQ,
        reply_markup=keyboards.kb_med_freq(),
    )
    return _MED_FREQ


async def cb_med_pular_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return ConversationHandler.END
    context.user_data["med_time"] = None
    await query.message.reply_text(
        textos.MSG_MED_PEDIR_FREQ,
        reply_markup=keyboards.kb_med_freq(),
    )
    return _MED_FREQ


async def save_med_freq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return ConversationHandler.END
    recurrence_base = query.data.split(":")[1]
    if recurrence_base == "daily":
        return await _finalizar_medicacao(query, context, recurrence="daily")
    context.user_data["med_recurrence_base"] = "weekly"
    await query.edit_message_text(
        textos.MSG_MED_PEDIR_DIA,
        reply_markup=keyboards.kb_med_dow(),
    )
    return _MED_DOW


async def save_med_dow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return ConversationHandler.END
    dow = int(query.data.split(":")[1])
    recurrence = f"weekly:{dow}"
    return await _finalizar_medicacao(query, context, recurrence=recurrence, dow=dow)


async def _finalizar_medicacao(query, context, recurrence: str, dow: int | None = None) -> int:
    title = context.user_data.pop("med_title", "")
    med_time = context.user_data.pop("med_time", None)
    context.user_data.pop("med_recurrence_base", None)
    if not title:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return ConversationHandler.END
    try:
        await asyncio.to_thread(
            task_service.create_medicacao,
            query.message.chat_id,
            title,
            recurrence,
            med_time,
        )
        await query.edit_message_text(textos.msg_med_ok(title, recurrence, med_time, dow))
    except Exception:
        logger.exception("Erro ao criar medicação")
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
    return ConversationHandler.END


async def cmd_cancel_med(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return ConversationHandler.END
    for key in ("med_title", "med_time", "med_recurrence_base"):
        context.user_data.pop(key, None)
    await update.message.reply_text(textos.MSG_CANCELADO)
    return ConversationHandler.END


medicacoes_conversation = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(cb_med_nova_start, pattern=r"^med_nova$"),
    ],
    states={
        _MED_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_med_nome)],
        _MED_TIME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, save_med_time),
            CallbackQueryHandler(cb_med_pular_time, pattern=r"^med_pular$"),
        ],
        _MED_FREQ: [CallbackQueryHandler(save_med_freq, pattern=r"^med_freq:")],
        _MED_DOW: [CallbackQueryHandler(save_med_dow, pattern=r"^med_dow:")],
    },
    fallbacks=[CommandHandler("cancel", cmd_cancel_med)],
    per_message=False,
    name="medicacoes",
)
