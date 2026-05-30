"""Notificações ao parceiro do casal (Fase C4).

Funciona tanto no modo "um bot para os dois" quanto "um bot por pessoa":
mantém um registro chat_id -> Bot (preenchido conforme os updates chegam) e
roteia a mensagem para o bot que de fato atende o parceiro. Tolerante a falha —
nunca quebra a ação que disparou a notificação.
"""
from __future__ import annotations

import asyncio
import logging

from telegram import Bot, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from src.services import couple_service, task_service

logger = logging.getLogger(__name__)

# chat_id -> último Bot que recebeu um update daquele chat.
_bot_by_chat: dict[int, Bot] = {}


def remember_bot(chat_id: int, bot: Bot) -> None:
    _bot_by_chat[chat_id] = bot


async def track_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """TypeHandler (grupo -1): registra qual bot atende cada chat."""
    if update.effective_chat is not None:
        remember_bot(update.effective_chat.id, context.bot)


def _bots_to_try(partner_chat_id: int, fallback_bot: Bot | None) -> list[Bot]:
    """Ordem de tentativa: bot conhecido do parceiro → fallback → demais bots."""
    order: list[Bot] = []
    seen = _bot_by_chat.get(partner_chat_id)
    if seen is not None:
        order.append(seen)
    if fallback_bot is not None and fallback_bot not in order:
        order.append(fallback_bot)
    for b in _bot_by_chat.values():
        if b not in order:
            order.append(b)
    return order


async def notify_partner(actor_chat_id: int, fallback_bot: Bot | None, text: str) -> bool:
    """Envia `text` ao parceiro do casal de `actor_chat_id`. Retorna True se entregou."""
    partner_id = await asyncio.to_thread(couple_service.partner_chat_id, actor_chat_id)
    if partner_id is None:
        return False
    # Respeita o silêncio do parceiro.
    if await asyncio.to_thread(task_service.is_paused, partner_id):
        return False
    for bot in _bots_to_try(partner_id, fallback_bot):
        try:
            await bot.send_message(partner_id, text)
            return True
        except TelegramError:
            continue
    logger.info("Não foi possível notificar o parceiro %s em nenhum bot.", partner_id)
    return False
