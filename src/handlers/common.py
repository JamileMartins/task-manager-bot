"""Handlers compartilhados: autorização, /start, /ajuda, /inbox, /ping, /reiniciar."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime

import pytz
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from src.config import AUTHORIZED_CHAT_ID, DEFAULT_TIMEZONE
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
        await update.message.reply_chat_action(ChatAction.TYPING)
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


# ---------------------------------------------------------------------------
# /ping
# ---------------------------------------------------------------------------

async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    tz = pytz.timezone(DEFAULT_TIMEZONE)
    agora = datetime.now(tz).strftime("%d/%m %H:%M")
    await update.message.reply_text(textos.msg_ping(agora))


# ---------------------------------------------------------------------------
# /reiniciar
# ---------------------------------------------------------------------------

async def cmd_reiniciar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    await update.message.reply_text(textos.MSG_REINICIANDO)
    asyncio.get_running_loop().call_later(0.5, os._exit, 0)


# ---------------------------------------------------------------------------
# Error handler global
# ---------------------------------------------------------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error_name = type(context.error).__name__
    logger.error("Exceção não tratada [%s]: %s", error_name, context.error, exc_info=context.error)

    if not isinstance(update, Update):
        return

    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id != AUTHORIZED_CHAT_ID:
        return

    aviso = f"⚠️ Erro interno: {error_name}\nVerifique os logs para detalhes."
    try:
        if update.callback_query:
            await update.callback_query.answer(aviso, show_alert=True)
        elif update.message:
            await update.message.reply_text(aviso)
    except Exception:
        pass
