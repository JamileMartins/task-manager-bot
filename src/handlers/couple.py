"""Handlers de pareamento de casal (Fase C2): /casal_convidar, /casal_entrar, /casal_status."""
from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from src.handlers.common import deny_unauthorized, is_authorized
from src.services import couple_service, task_service
from src.utils import textos

logger = logging.getLogger(__name__)


async def cmd_casal_convidar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    chat_id = update.effective_chat.id
    user_name = (update.effective_user.full_name or "usuária") if update.effective_user else "usuária"
    try:
        await msg.reply_chat_action(ChatAction.TYPING)
        # Garante que o usuário exista antes de criar o convite.
        await asyncio.to_thread(task_service.get_or_create_user, chat_id, user_name)
        result = await asyncio.to_thread(couple_service.create_invite, chat_id)

        if result.status == "ok":
            await msg.reply_text(textos.msg_casal_convite(result.code), parse_mode="Markdown")
        elif result.status == "already_paired":
            await msg.reply_text(textos.MSG_CASAL_JA_PAREADO)
        else:  # no_user (não deve ocorrer após get_or_create_user)
            await msg.reply_text(textos.MSG_CASAL_PRECISA_START)
    except Exception:
        logger.exception("Erro em /casal_convidar")
        await msg.reply_text(textos.MSG_ERRO_GENERICO)


async def cmd_casal_entrar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    chat_id = update.effective_chat.id
    user_name = (update.effective_user.full_name or "usuária") if update.effective_user else "usuária"

    code = (context.args[0] if context.args else "").strip()
    if not code:
        await msg.reply_text(textos.MSG_CASAL_ENTRAR_SEM_CODIGO, parse_mode="Markdown")
        return

    try:
        await msg.reply_chat_action(ChatAction.TYPING)
        await asyncio.to_thread(task_service.get_or_create_user, chat_id, user_name)
        result = await asyncio.to_thread(couple_service.accept_invite, chat_id, code)

        if result.status == "ok":
            await msg.reply_text(textos.msg_casal_entrou_ok(result.partner_name))
            await _notify_creator(context, chat_id, user_name)
            return

        erros = {
            "invalid": textos.MSG_CASAL_CODIGO_INVALIDO,
            "expired": textos.MSG_CASAL_CODIGO_EXPIRADO,
            "used": textos.MSG_CASAL_CODIGO_USADO,
            "already_paired": textos.MSG_CASAL_ENTRAR_JA_PAREADO,
            "own_invite": textos.MSG_CASAL_ENTRAR_PROPRIO,
            "full": textos.MSG_CASAL_ENTRAR_CHEIO,
            "no_user": textos.MSG_CASAL_PRECISA_START,
        }
        await msg.reply_text(erros.get(result.status, textos.MSG_ERRO_GENERICO))
    except Exception:
        logger.exception("Erro em /casal_entrar")
        await msg.reply_text(textos.MSG_ERRO_GENERICO)


async def _notify_creator(context: ContextTypes.DEFAULT_TYPE, joiner_chat_id: int, joiner_name: str) -> None:
    """Avisa quem criou o convite que o par entrou. Tolerante a falha (parceiro
    pode estar noutro bot — a notificação cross-bot é tratada na Fase C4)."""
    try:
        partner = await asyncio.to_thread(couple_service.get_partner, joiner_chat_id)
        if partner:
            await context.bot.send_message(
                partner["chat_id"], textos.msg_casal_parceiro_entrou(joiner_name)
            )
    except Exception:
        logger.info("Não foi possível notificar o criador do convite (provável bot distinto).")


async def cmd_casal_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    chat_id = update.effective_chat.id
    try:
        partner = await asyncio.to_thread(couple_service.get_partner, chat_id)
        if partner:
            await msg.reply_text(
                textos.msg_casal_status_pareado(partner["name"]), parse_mode="Markdown"
            )
        else:
            await msg.reply_text(textos.MSG_CASAL_STATUS_SOLO)
    except Exception:
        logger.exception("Erro em /casal_status")
        await msg.reply_text(textos.MSG_ERRO_GENERICO)
