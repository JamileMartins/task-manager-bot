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
    msg = update.effective_message
    if not msg:
        return
    name = (update.effective_user.full_name if update.effective_user else None) or "usuária"
    await asyncio.to_thread(task_service.get_or_create_user, update.effective_chat.id, name)
    await msg.reply_text(textos.MSG_BOAS_VINDAS)


# ---------------------------------------------------------------------------
# /ajuda
# ---------------------------------------------------------------------------

async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    await msg.reply_text(textos.MSG_AJUDA)


# ---------------------------------------------------------------------------
# /inbox
# ---------------------------------------------------------------------------

async def cmd_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
        tasks = await asyncio.to_thread(task_service.get_inbox_tasks, update.effective_chat.id)
        if not tasks:
            await msg.reply_text(textos.MSG_INBOX_VAZIA)
            return

        lines = [textos.msg_inbox_titulo(len(tasks))]
        for i, t in enumerate(tasks, 1):
            lines.append(f"{i}. {t.title}")

        await msg.reply_text(
            "\n".join(lines),
            reply_markup=keyboards.kb_inbox(tasks),
        )
    except Exception:
        logger.exception("Erro em /inbox")
        await msg.reply_text(textos.MSG_ERRO_GENERICO)


# ---------------------------------------------------------------------------
# /ping
# ---------------------------------------------------------------------------

async def cmd_quadrantes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    await msg.reply_text(textos.MSG_GUIA_QUADRANTES)


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    tz = pytz.timezone(DEFAULT_TIMEZONE)
    agora = datetime.now(tz).strftime("%d/%m %H:%M")
    await msg.reply_text(textos.msg_ping(agora))


# ---------------------------------------------------------------------------
# /hoje e /amanha
# ---------------------------------------------------------------------------

async def cmd_hoje(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
        chat_id = update.effective_chat.id
        today_tasks, focus_tasks = await asyncio.to_thread(
            task_service.get_daily_summary_tasks, chat_id
        )
        if not today_tasks and not focus_tasks:
            await msg.reply_text(textos.MSG_HOJE_VAZIO)
        else:
            await msg.reply_text(textos.msg_hoje(today_tasks, focus_tasks))
    except Exception:
        logger.exception("Erro em /hoje")
        await msg.reply_text(textos.MSG_ERRO_GENERICO)


async def cmd_amanha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
        chat_id = update.effective_chat.id
        tasks = await asyncio.to_thread(task_service.get_tomorrow_tasks, chat_id)
        if not tasks:
            await msg.reply_text(textos.MSG_AMANHA_VAZIO)
        else:
            await msg.reply_text(textos.msg_amanha(tasks))
    except Exception:
        logger.exception("Erro em /amanha")
        await msg.reply_text(textos.MSG_ERRO_GENERICO)


# ---------------------------------------------------------------------------
# /conquistas (Sugestão #3)
# ---------------------------------------------------------------------------

async def cmd_conquistas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
        stats = await asyncio.to_thread(task_service.get_conquistas, update.effective_chat.id)
        await msg.reply_text(textos.msg_conquistas(stats))
    except Exception:
        logger.exception("Erro em /conquistas")
        await msg.reply_text(textos.MSG_ERRO_GENERICO)


# ---------------------------------------------------------------------------
# /reiniciar
# ---------------------------------------------------------------------------

async def cmd_reiniciar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    await msg.reply_text(textos.MSG_REINICIANDO)
    asyncio.get_running_loop().call_later(0.5, os._exit, 0)


# ---------------------------------------------------------------------------
# /casal (US-19)
# ---------------------------------------------------------------------------

async def cmd_casal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
        chat_id = update.effective_chat.id
        tasks, group_id = await asyncio.to_thread(task_service.get_couple_tasks, chat_id)
        if not tasks:
            await msg.reply_text(textos.MSG_CASAL_VAZIA)
            return
        texto = textos.msg_casal(tasks)
        if group_id:
            await context.bot.send_message(group_id, texto)
            await msg.reply_text(textos.MSG_CASAL_ENVIADO)
        else:
            await msg.reply_text(texto + "\n\n" + textos.MSG_CASAL_SEM_GRUPO)
    except Exception:
        logger.exception("Erro em /casal")
        await msg.reply_text(textos.MSG_ERRO_GENERICO)


async def cmd_setgrupo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra o grupo atual como grupo do casal (chamado de dentro de um grupo)."""
    if not update.effective_chat:
        return
    if update.effective_chat.type not in ("group", "supergroup"):
        msg = update.effective_message
        if msg:
            await msg.reply_text(textos.MSG_SETGRUPO_APENAS_GRUPO)
        return
    group_chat_id = update.effective_chat.id
    await asyncio.to_thread(task_service.update_config, AUTHORIZED_CHAT_ID, couple_group_chat_id=group_chat_id)
    msg = update.effective_message
    if msg:
        await msg.reply_text(textos.MSG_SETGRUPO_OK)


# ---------------------------------------------------------------------------
# /tudo (US-31)
# ---------------------------------------------------------------------------

async def cmd_tudo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
        chat_id = update.effective_chat.id
        groups = await asyncio.to_thread(task_service.get_all_open_tasks, chat_id)

        if not groups:
            await msg.reply_text(textos.MSG_TUDO_VAZIA)
            return

        total = sum(len(g.tasks) for g in groups)
        limit = 5 if total > 30 else None

        for group in groups:
            tasks = group.tasks[:limit] if limit else group.tasks
            emoji = "📥" if group.slug is None else textos.lista_emoji(group.slug)
            texto = textos.msg_tudo_header(group.name, emoji, len(tasks), len(group.tasks))
            await msg.reply_text(texto, reply_markup=keyboards.kb_tudo_group(tasks))
    except Exception:
        logger.exception("Erro em /tudo")
        await msg.reply_text(textos.MSG_ERRO_GENERICO)


# ---------------------------------------------------------------------------
# /buscar (US-22)
# ---------------------------------------------------------------------------

async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    term = " ".join(context.args).strip() if context.args else ""
    if not term:
        await msg.reply_text(textos.MSG_BUSCA_SEM_TERMO)
        return
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
        tasks = await asyncio.to_thread(task_service.search_tasks, update.effective_chat.id, term)
        if not tasks:
            await msg.reply_text(textos.MSG_BUSCA_VAZIA)
            return
        await msg.reply_text(
            textos.msg_busca(tasks, term),
            reply_markup=keyboards.kb_tasks(tasks),
        )
    except Exception:
        logger.exception("Erro em /buscar")
        await msg.reply_text(textos.MSG_ERRO_GENERICO)


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
