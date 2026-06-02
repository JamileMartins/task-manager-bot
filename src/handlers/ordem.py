"""Handler /ordem — exibe cadeias de dependência em ordem de execução (v1.18.0)."""
from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.handlers.common import deny_unauthorized, is_authorized
from src.services import task_service
from src.utils import keyboards, textos

logger = logging.getLogger(__name__)


async def cmd_ordem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return

    chat_id = update.effective_chat.id
    chains = await asyncio.to_thread(task_service.get_dependency_chains, chat_id)

    if not chains:
        await msg.reply_text(textos.MSG_ORDEM_VAZIA, parse_mode="Markdown")
        return

    n_ready = sum(1 for chain in chains if chain)  # cada cadeia tem exatamente 1 "fazer agora"
    header = textos.msg_ordem_header(len(chains), n_ready)
    kb = keyboards.kb_ordem(chains)
    await msg.reply_text(header, reply_markup=kb, parse_mode="Markdown")
