"""Handler de mensagens de voz e áudio — transcrição via Gemini."""
from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from src.handlers.capture import process_text_capture
from src.handlers.common import deny_unauthorized, is_authorized
from src.services import ai_service
from src.utils import textos

logger = logging.getLogger(__name__)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return

    msg = update.effective_message
    if not msg:
        return

    await msg.reply_chat_action(ChatAction.TYPING)

    if msg.voice:
        tg_file = await msg.voice.get_file()
        mime_type = "audio/ogg"
    elif msg.audio:
        tg_file = await msg.audio.get_file()
        mime_type = msg.audio.mime_type or "audio/mpeg"
    else:
        return

    try:
        audio_bytes = bytes(await tg_file.download_as_bytearray())
    except Exception:
        logger.exception("Erro ao baixar áudio do Telegram")
        await msg.reply_text(textos.MSG_AUDIO_ERRO)
        return

    try:
        texto = await asyncio.wait_for(
            asyncio.to_thread(ai_service.transcrever_audio, audio_bytes, mime_type),
            timeout=120.0,
        )
    except asyncio.TimeoutError:
        logger.warning("Timeout na transcrição de áudio (120s)")
        await msg.reply_text(textos.MSG_AUDIO_ERRO)
        return
    except Exception:
        logger.exception("Erro na transcrição de áudio")
        await msg.reply_text(textos.MSG_AUDIO_ERRO)
        return

    if not texto:
        await msg.reply_text(textos.MSG_AUDIO_ERRO)
        return

    await msg.reply_text(textos.msg_audio_ouvi(texto))
    await process_text_capture(update, context, texto)
