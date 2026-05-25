"""Handler de captura por texto livre → Inbox (US-01)."""
from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.handlers.common import deny_unauthorized, is_authorized
from src.services import task_service
from src.utils import keyboards, textos

logger = logging.getLogger(__name__)


async def handle_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return

    text = (update.message.text or "").strip()
    if not text:
        return

    try:
        user_name = update.effective_user.full_name or "Jamile"
        task = await asyncio.to_thread(
            task_service.create_task_in_inbox, update.effective_chat.id, text, user_name
        )
        await update.message.reply_text(
            textos.msg_captura_confirmacao(),
            reply_markup=keyboards.kb_undo_capture(task.id),
        )
    except Exception:
        logger.exception("Erro ao capturar tarefa")
        await update.message.reply_text(textos.MSG_ERRO_GENERICO)


async def cb_undo_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not is_authorized(update):
        return

    task_id = query.data.split(":")[1]
    try:
        await asyncio.to_thread(task_service.delete_task, task_id)
        await query.edit_message_text(textos.MSG_DESFAZER_OK)
    except Exception:
        logger.exception("Erro ao desfazer captura")
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
