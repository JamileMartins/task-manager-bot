"""Visão detalhada e edição de atributos de tarefa (US-07, 08, 09, 10, 11)."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta

import pytz
from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from src.config import DEFAULT_TIMEZONE
from src.handlers.common import deny_unauthorized, is_authorized
from src.handlers import notify
from src.services import task_service
from src.utils import keyboards, textos

logger = logging.getLogger(__name__)

_MOVE_TASK_KEY = "move_task_id"
_MOVE_LISTAS_KEY = "move_listas"
_HAS_COUPLE_KEY = "detail_has_couple"
_NOTE_TASK_KEY = "note_task_id"
_TITLE_TASK_KEY = "title_task_id"

_NOTE_TEXT = 1
_TITLE_TEXT = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _refresh_detail(query, task_id: uuid.UUID, context: ContextTypes.DEFAULT_TYPE) -> None:
    listas = context.user_data.get(_MOVE_LISTAS_KEY, [])
    task, subtasks = await asyncio.gather(
        asyncio.to_thread(task_service.get_task_with_list, task_id),
        asyncio.to_thread(task_service.get_subtasks, task_id),
    )
    if task is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return
    await query.edit_message_text(
        textos.msg_task_detail(task, subtasks),
        reply_markup=keyboards.kb_task_detail(task, listas, subtasks, show_couple=context.user_data.get(_HAS_COUPLE_KEY, False)),
    )


# ---------------------------------------------------------------------------
# Abrir detalhe
# ---------------------------------------------------------------------------

async def cb_task_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id = uuid.UUID(query.data.split(":")[1])

    listas_info = await asyncio.to_thread(
        task_service.get_user_lists, update.effective_chat.id
    )
    listas_dicts = [
        {"name": l.name, "slug": l.slug, "id": str(l.id)} for l in listas_info
    ]
    context.user_data[_MOVE_LISTAS_KEY] = listas_dicts
    context.user_data[_MOVE_TASK_KEY] = str(task_id)
    has_couple = await asyncio.to_thread(task_service.has_couple, update.effective_chat.id)
    context.user_data[_HAS_COUPLE_KEY] = has_couple

    try:
        task, subtasks = await asyncio.gather(
            asyncio.to_thread(task_service.get_task_with_list, task_id),
            asyncio.to_thread(task_service.get_subtasks, task_id),
        )
        if task is None:
            await query.edit_message_text(textos.MSG_ERRO_GENERICO)
            return
        await query.edit_message_text(
            textos.msg_task_detail(task, subtasks),
            reply_markup=keyboards.kb_task_detail(task, listas_dicts, subtasks, show_couple=has_couple),
        )
    except Exception:
        logger.exception("Erro ao abrir detalhe da tarefa %s", task_id)
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)


# ---------------------------------------------------------------------------
# Alternar pessoal <-> casal (C3)
# ---------------------------------------------------------------------------

async def cb_task_set_couple(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not is_authorized(update):
        await query.answer()
        return
    parts = query.data.split(":")
    task_id = uuid.UUID(parts[1])
    make_couple = parts[2] == "1"

    updated = await asyncio.to_thread(
        task_service.set_task_couple, task_id, update.effective_chat.id, make_couple
    )
    if updated is None:
        await query.answer("Você ainda não está num casal 💞 Use /casal_convidar.", show_alert=True)
        return
    await query.answer("💞 Agora é do casal!" if make_couple else "👤 Agora é pessoal.")
    if make_couple:
        actor = (update.effective_user.full_name if update.effective_user else None) or "Seu par"
        await notify.notify_partner(
            update.effective_chat.id, context.bot, textos.msg_casal_compartilhou(actor, 1)
        )
    await _refresh_detail(query, task_id, context)


async def cb_task_assign(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not is_authorized(update):
        await query.answer()
        return
    parts = query.data.split(":")
    task_id = uuid.UUID(parts[1])
    target = parts[2]  # "me" | "partner"

    task = await asyncio.to_thread(
        task_service.assign_couple_task, task_id, update.effective_chat.id, target
    )
    if task is None:
        await query.answer()
        return
    actor = (update.effective_user.full_name if update.effective_user else None) or "Seu par"
    if target == "partner":
        await query.answer("🤝 Passei a vez pro seu par.")
        await notify.notify_partner(
            update.effective_chat.id, context.bot, textos.msg_casal_atribuiu(actor, task.title)
        )
    elif target == "joint":
        await query.answer("💞 Conjunta — precisa dos dois.")
        await notify.notify_partner(
            update.effective_chat.id, context.bot, textos.msg_casal_marcou_conjunta(actor, task.title)
        )
    elif target == "me":
        await query.answer("🙋 Agora é com você!")
    else:  # shared
        await query.answer("🆓 Sem dono — qualquer um faz.")
    await _refresh_detail(query, task_id, context)


# ---------------------------------------------------------------------------
# Editar quadrante (US-08)
# ---------------------------------------------------------------------------

async def cb_task_set_quadrant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    _, task_id_str, q_str = query.data.split(":")
    task_id = uuid.UUID(task_id_str)
    await asyncio.to_thread(task_service.update_task_attrs, task_id, quadrant=int(q_str))
    await _refresh_detail(query, task_id, context)


# ---------------------------------------------------------------------------
# Editar energia e estimativa (US-10)
# ---------------------------------------------------------------------------

async def cb_task_set_energy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    parts = query.data.split(":")
    task_id = uuid.UUID(parts[1])
    await asyncio.to_thread(task_service.update_task_attrs, task_id, energy=parts[2])
    await _refresh_detail(query, task_id, context)


async def cb_task_set_estimate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    parts = query.data.split(":")
    task_id = uuid.UUID(parts[1])
    await asyncio.to_thread(task_service.update_task_attrs, task_id, estimate_min=int(parts[2]))
    await _refresh_detail(query, task_id, context)


# ---------------------------------------------------------------------------
# Recorrência (US-18)
# ---------------------------------------------------------------------------

async def cb_task_set_recurrence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    parts = query.data.split(":")
    task_id = uuid.UUID(parts[1])
    value = None if parts[2] == "none" else parts[2]
    await asyncio.to_thread(task_service.update_task_attrs, task_id, recurrence=value)
    await _refresh_detail(query, task_id, context)


# ---------------------------------------------------------------------------
# Definir prazo (US-09)
# ---------------------------------------------------------------------------

async def cb_task_set_due(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    parts = query.data.split(":")
    task_id = uuid.UUID(parts[1])
    when = parts[2]

    tz = pytz.timezone(DEFAULT_TIMEZONE)
    now = datetime.now(tz)
    if when == "hoje":
        due: datetime | None = now.replace(hour=23, minute=59, second=0, microsecond=0)
    elif when == "amanha":
        due = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        due = None

    await asyncio.to_thread(task_service.update_task_attrs, task_id, due_at=due)
    await _refresh_detail(query, task_id, context)


# ---------------------------------------------------------------------------
# Mover tarefa entre listas (US-07)
# ---------------------------------------------------------------------------

async def cb_task_start_move(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id_str = query.data.split(":")[1]
    context.user_data[_MOVE_TASK_KEY] = task_id_str

    listas = context.user_data.get(_MOVE_LISTAS_KEY)
    if not listas:
        listas_info = await asyncio.to_thread(
            task_service.get_user_lists, update.effective_chat.id
        )
        listas = [{"name": l.name, "slug": l.slug, "id": str(l.id)} for l in listas_info]
        context.user_data[_MOVE_LISTAS_KEY] = listas

    await query.edit_message_text(
        "Para qual lista mover?",
        reply_markup=keyboards.kb_mover_tarefa(task_id_str, listas),
    )


async def cb_task_move_to(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    list_idx = int(query.data.split(":")[1])
    task_id_str = context.user_data.get(_MOVE_TASK_KEY)
    listas = context.user_data.get(_MOVE_LISTAS_KEY, [])

    if not task_id_str:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    task_id = uuid.UUID(task_id_str)
    if list_idx == -1:
        new_list_id = None
    elif 0 <= list_idx < len(listas):
        new_list_id: uuid.UUID | None = uuid.UUID(listas[list_idx]["id"])
    else:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    try:
        await asyncio.to_thread(task_service.update_task_attrs, task_id, list_id=new_list_id)
        await _refresh_detail(query, task_id, context)
    except Exception:
        logger.exception("Erro ao mover tarefa %s", task_id)
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)


# ---------------------------------------------------------------------------
# Ordenação manual (US-11)
# ---------------------------------------------------------------------------

async def cb_task_reorder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    parts = query.data.split(":")
    direction = "up" if parts[0] == "task_up" else "down"
    task_id = uuid.UUID(parts[1])
    await asyncio.to_thread(task_service.reorder_task, task_id, direction)
    await _refresh_detail(query, task_id, context)


# ---------------------------------------------------------------------------
# Nota em tarefa (Sugestão #2)
# ---------------------------------------------------------------------------

async def cb_task_note_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return ConversationHandler.END

    task_id_str = query.data.split(":")[1]
    context.user_data[_NOTE_TASK_KEY] = task_id_str

    task = await asyncio.to_thread(task_service.get_task_with_list, uuid.UUID(task_id_str))
    if task is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return ConversationHandler.END

    await query.edit_message_text(
        textos.msg_nota_pergunta(task.title),
        reply_markup=keyboards.kb_nota(task_id_str, bool(task.notes)),
    )
    return _NOTE_TEXT


async def save_task_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update):
        return ConversationHandler.END

    task_id_str = context.user_data.get(_NOTE_TASK_KEY)
    if not task_id_str:
        return ConversationHandler.END

    note_text = update.message.text.strip()
    task_id = uuid.UUID(task_id_str)
    await asyncio.to_thread(task_service.update_task_attrs, task_id, notes=note_text)

    task, subtasks = await asyncio.gather(
        asyncio.to_thread(task_service.get_task_with_list, task_id),
        asyncio.to_thread(task_service.get_subtasks, task_id),
    )
    listas = context.user_data.get(_MOVE_LISTAS_KEY, [])
    await update.message.reply_text(textos.MSG_NOTA_SALVA)
    if task:
        await update.message.reply_text(
            textos.msg_task_detail(task, subtasks),
            reply_markup=keyboards.kb_task_detail(task, listas, subtasks, show_couple=context.user_data.get(_HAS_COUPLE_KEY, False)),
        )
    return ConversationHandler.END


async def cb_task_note_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return ConversationHandler.END

    task_id_str = query.data.split(":")[1]
    task_id = uuid.UUID(task_id_str)
    await asyncio.to_thread(task_service.update_task_attrs, task_id, notes=None)

    listas = context.user_data.get(_MOVE_LISTAS_KEY, [])
    task, subtasks = await asyncio.gather(
        asyncio.to_thread(task_service.get_task_with_list, task_id),
        asyncio.to_thread(task_service.get_subtasks, task_id),
    )
    await query.edit_message_text(
        textos.MSG_NOTA_APAGADA + ("\n\n" + textos.msg_task_detail(task, subtasks) if task else ""),
        reply_markup=keyboards.kb_task_detail(task, listas, subtasks, show_couple=context.user_data.get(_HAS_COUPLE_KEY, False)) if task else None,
    )
    return ConversationHandler.END


async def cb_task_note_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return ConversationHandler.END

    task_id_str = query.data.split(":")[1]
    task_id = uuid.UUID(task_id_str)
    await _refresh_detail(query, task_id, context)
    return ConversationHandler.END


async def _cmd_cancel_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Nota cancelada.")
    return ConversationHandler.END


note_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(cb_task_note_start, pattern=r"^task_note:[^_]")],
    states={
        _NOTE_TEXT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, save_task_note),
            CallbackQueryHandler(cb_task_note_delete, pattern=r"^task_note_del:"),
            CallbackQueryHandler(cb_task_note_cancel, pattern=r"^task_note_cancel:"),
        ],
    },
    fallbacks=[CommandHandler("cancel", _cmd_cancel_note)],
    per_message=False,
    name="note_editing",
)


# ---------------------------------------------------------------------------
# Concluir subtarefa a partir do detalhe da tarefa-pai (Sugestão #6)
# ---------------------------------------------------------------------------

async def cb_sub_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    parts = query.data.split(":")
    subtask_id = uuid.UUID(parts[1])
    parent_id = uuid.UUID(parts[2])

    await asyncio.to_thread(task_service.complete_task, subtask_id)
    await _refresh_detail(query, parent_id, context)


# ---------------------------------------------------------------------------
# Editar título de tarefa (Sugestão #9)
# ---------------------------------------------------------------------------

async def cb_task_title_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return ConversationHandler.END

    task_id_str = query.data.split(":")[1]
    context.user_data[_TITLE_TASK_KEY] = task_id_str

    task = await asyncio.to_thread(task_service.get_task_with_list, uuid.UUID(task_id_str))
    if task is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return ConversationHandler.END

    await query.edit_message_text(
        textos.msg_titulo_pergunta(task.title),
        reply_markup=keyboards.kb_cancelar(task_id_str),
    )
    return _TITLE_TEXT


async def save_task_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_authorized(update):
        return ConversationHandler.END

    task_id_str = context.user_data.get(_TITLE_TASK_KEY)
    if not task_id_str:
        return ConversationHandler.END

    novo_titulo = update.message.text.strip()[:500]
    task_id = uuid.UUID(task_id_str)
    await asyncio.to_thread(task_service.update_task_attrs, task_id, title=novo_titulo)

    task, subtasks = await asyncio.gather(
        asyncio.to_thread(task_service.get_task_with_list, task_id),
        asyncio.to_thread(task_service.get_subtasks, task_id),
    )
    listas = context.user_data.get(_MOVE_LISTAS_KEY, [])
    await update.message.reply_text(textos.MSG_TITULO_SALVO)
    if task:
        await update.message.reply_text(
            textos.msg_task_detail(task, subtasks),
            reply_markup=keyboards.kb_task_detail(task, listas, subtasks, show_couple=context.user_data.get(_HAS_COUPLE_KEY, False)),
        )
    return ConversationHandler.END


async def cb_task_title_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return ConversationHandler.END

    task_id_str = query.data.split(":")[1]
    task_id = uuid.UUID(task_id_str)
    await _refresh_detail(query, task_id, context)
    return ConversationHandler.END


async def _cmd_cancel_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Edição de título cancelada.")
    return ConversationHandler.END


title_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(cb_task_title_start, pattern=r"^task_title:")],
    states={
        _TITLE_TEXT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, save_task_title),
            CallbackQueryHandler(cb_task_title_cancel, pattern=r"^task_title_cancel:"),
        ],
    },
    fallbacks=[CommandHandler("cancel", _cmd_cancel_title)],
    per_message=False,
    name="title_editing",
)
