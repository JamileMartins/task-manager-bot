"""Handlers compartilhados: autorização, /start, /ajuda, /inbox."""
from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.config import AUTHORIZED_CHAT_ID
from src.services import task_service
from src.utils import keyboards, textos

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Autorização
# ---------------------------------------------------------------------------

def is_authorized(update: Update) -> bool:
    return update.effective_chat is not None and update.effective_chat.id == AUTHORIZED_CHAT_ID


async def deny_unauthorized(update: Update) -> None:
    if update.message:
        await update.message.reply_text(textos.MSG_NAO_AUTORIZADO)
    elif update.callback_query:
        await update.callback_query.answer(textos.MSG_NAO_AUTORIZADO, show_alert=True)


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    name = update.effective_user.full_name or "Jamile"
    await asyncio.to_thread(task_service.get_or_create_user, update.effective_chat.id, name)
    await update.message.reply_text(textos.MSG_BOAS_VINDAS)


# ---------------------------------------------------------------------------
# /ajuda
# ---------------------------------------------------------------------------

async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    await update.message.reply_text(textos.MSG_AJUDA)


# ---------------------------------------------------------------------------
# /inbox
# ---------------------------------------------------------------------------

async def cmd_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    try:
        tasks = await asyncio.to_thread(task_service.get_inbox_tasks, update.effective_chat.id)
        if not tasks:
            await update.message.reply_text(textos.MSG_INBOX_VAZIA)
            return

        lines = [textos.msg_inbox_titulo(len(tasks))]
        for i, t in enumerate(tasks, 1):
            lines.append(f"{i}. {t.title}")

        await update.message.reply_text(
            "\n".join(lines),
            reply_markup=keyboards.kb_inbox(tasks),
        )
    except Exception:
        logger.exception("Erro em /inbox")
        await update.message.reply_text(textos.MSG_ERRO_GENERICO)
