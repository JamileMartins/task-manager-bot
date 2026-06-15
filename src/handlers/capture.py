"""Handler de captura por texto livre com classificação via IA (F1/F2)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from src.handlers.common import deny_unauthorized, is_authorized
from src.handlers import notify
from src.handlers.blocker import handle_blocker_note_text
from src.handlers.task_detail import handle_task_due_custom_text
from src.services import ai_service, task_service
from src.utils import keyboards, textos

logger = logging.getLogger(__name__)

# Chave no user_data onde ficam as tarefas pendentes de aprovação
_PENDING_KEY = "pending_capture"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pending(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any] | None:
    return context.user_data.get(_PENDING_KEY)


def _set_pending(
    context: ContextTypes.DEFAULT_TYPE,
    tasks: list[dict],
    listas: list[dict],
    has_couple: bool = False,
) -> None:
    context.user_data[_PENDING_KEY] = {
        "tasks": tasks,
        "listas": listas,
        "adj_index": 0,
        "has_couple": has_couple,
    }


def _clear_pending(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(_PENDING_KEY, None)


async def _notify_couple_created(update: Update, context: ContextTypes.DEFAULT_TYPE, saved: list) -> None:
    """Avisa o parceiro quando tarefas de casal foram criadas na captura."""
    couple_tasks = [t for t in saved if getattr(t, "couple_id", None) is not None]
    n = len(couple_tasks)
    if n == 0:
        return
    actor = (update.effective_user.full_name if update.effective_user else None) or "Seu par"
    if n == 1:
        texto = textos.msg_casal_compartilhou(actor, 1, couple_tasks[0].title)
        markup = keyboards.kb_notif_ver_tarefa(couple_tasks[0].id)
    else:
        texto = textos.msg_casal_compartilhou(actor, n)
        markup = keyboards.kb_notif_ver_casal()
    await notify.notify_partner(update.effective_chat.id, context.bot, texto, reply_markup=markup)


# ---------------------------------------------------------------------------
# Captura (entrada de texto livre)
# ---------------------------------------------------------------------------

async def process_text_capture(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> None:
    """Classifica texto como brain dump e envia resumo para aprovação.

    Reutilizado por handle_capture (texto) e handle_voice (áudio transcrito).
    """
    msg = update.effective_message
    chat_id = update.effective_chat.id
    user_name = (update.effective_user.full_name or "usuária") if update.effective_user else "usuária"

    try:
        listas_info = await asyncio.to_thread(task_service.get_user_lists, chat_id)
        if not listas_info:
            await asyncio.to_thread(task_service.get_or_create_user, chat_id, user_name)
            listas_info = await asyncio.to_thread(task_service.get_user_lists, chat_id)

        nomes_listas = [l.name for l in listas_info]
        listas_dicts = [{"name": l.name, "slug": l.slug, "id": str(l.id)} for l in listas_info]

        tarefas = await asyncio.to_thread(
            ai_service.classificar_brain_dump, text, nomes_listas
        )

        has_couple = await asyncio.to_thread(task_service.has_couple, chat_id)
        _set_pending(context, tarefas, listas_dicts, has_couple)
        await msg.reply_text(
            textos.msg_classificacao_resumo(tarefas),
            reply_markup=keyboards.kb_classificacao_resumo(),
        )
    except Exception:
        logger.exception("Erro ao classificar captura")
        try:
            await asyncio.to_thread(task_service.create_task_in_inbox, chat_id, text, user_name)
            await msg.reply_text(textos.MSG_CAPTURA_FALLBACK)
        except Exception:
            logger.exception("Erro também no fallback de captura")
            await msg.reply_text(textos.MSG_ERRO_GENERICO)


async def handle_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return

    text = (update.message.text or "").strip()
    if not text:
        return

    # Interceptores com prioridade sobre brain dump
    if await handle_blocker_note_text(update, context):
        return
    if await handle_task_due_custom_text(update, context):
        return

    await update.message.reply_chat_action(ChatAction.TYPING)
    await process_text_capture(update, context, text)


# ---------------------------------------------------------------------------
# Aprovar tudo
# ---------------------------------------------------------------------------

async def cb_approve_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    pending = _pending(context)
    if not pending:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    chat_id = update.effective_chat.id
    user_name = update.effective_user.full_name or "usuária"

    try:
        saved = await asyncio.to_thread(
            task_service.save_classified_tasks,
            chat_id,
            pending["tasks"],
            user_name,
        )
        _clear_pending(context)
        await query.edit_message_text(textos.msg_captura_salva(len(saved)))
        await _notify_couple_created(update, context, saved)
    except Exception:
        logger.exception("Erro ao salvar tarefas classificadas")
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)


# ---------------------------------------------------------------------------
# Cancelar captura
# ---------------------------------------------------------------------------

async def cb_cancel_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    _clear_pending(context)
    await query.edit_message_text(textos.MSG_CANCELADO)


# ---------------------------------------------------------------------------
# Ajustar item a item
# ---------------------------------------------------------------------------

async def cb_adjust_capture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inicia o fluxo de ajuste: mostra a primeira tarefa com seleção de lista."""
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    pending = _pending(context)
    if not pending:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    pending["adj_index"] = 0
    await _show_task_for_adjustment(query, pending)


async def cb_adj_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recebe a seleção de lista para a tarefa atual e avança para a próxima."""
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    pending = _pending(context)
    if not pending:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    # callback_data = "adj:{task_idx}:{list_idx}"  (-1 = Inbox)
    parts = query.data.split(":")
    task_idx = int(parts[1])
    list_idx = int(parts[2])

    tasks = pending["tasks"]
    listas = pending["listas"]

    if 0 <= task_idx < len(tasks):
        if list_idx == -1:  # Inbox
            tasks[task_idx]["lista_sugerida"] = None
            tasks[task_idx]["casal"] = False
        elif list_idx == -2:  # Casal
            tasks[task_idx]["lista_sugerida"] = None
            tasks[task_idx]["casal"] = True
        elif 0 <= list_idx < len(listas):
            tasks[task_idx]["lista_sugerida"] = listas[list_idx]["name"]
            tasks[task_idx]["casal"] = False

    next_idx = task_idx + 1
    pending["adj_index"] = next_idx

    if next_idx < len(tasks):
        await _show_task_for_adjustment(query, pending)
    else:
        # Todas as tarefas revisadas — salvar agora
        chat_id = update.effective_chat.id
        user_name = update.effective_user.full_name or "usuária"
        try:
            saved = await asyncio.to_thread(
                task_service.save_classified_tasks,
                chat_id,
                tasks,
                user_name,
            )
            _clear_pending(context)
            await query.edit_message_text(textos.msg_captura_salva(len(saved)))
            await _notify_couple_created(update, context, saved)
        except Exception:
            logger.exception("Erro ao salvar tarefas após ajuste")
            await query.edit_message_text(textos.MSG_ERRO_GENERICO)


async def _show_task_for_adjustment(query, pending: dict) -> None:
    idx = pending["adj_index"]
    tasks = pending["tasks"]
    listas = pending["listas"]
    task = tasks[idx]
    texto = textos.msg_ajustar_tarefa(task, idx, len(tasks))
    kb = keyboards.kb_ajustar_tarefa(idx, listas, show_couple=pending.get("has_couple", False))
    await query.edit_message_text(texto, reply_markup=kb)


# ---------------------------------------------------------------------------
# Desfazer captura única (F1 — mantido para compatibilidade)
# ---------------------------------------------------------------------------

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
