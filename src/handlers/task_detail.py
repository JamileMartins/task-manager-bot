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

import re

logger = logging.getLogger(__name__)

_MOVE_TASK_KEY = "move_task_id"
_MOVE_LISTAS_KEY = "move_listas"
_HAS_COUPLE_KEY = "detail_has_couple"
_NOTE_TASK_KEY = "note_task_id"
_TITLE_TASK_KEY = "title_task_id"
_DUE_CUSTOM_KEY = "due_custom_task_id"


def _parse_date_ptbr(text: str, tz_name: str = DEFAULT_TIMEZONE) -> datetime | None:
    """Faz parse de datas em PT-BR. Exemplos aceitos:
    20/07 · 20/07/2026 · 20/07 às 14:00 · 20/07/2026 14:30
    """
    tz = pytz.timezone(tz_name)
    now = datetime.now(tz)
    text = text.strip().replace("às ", "").replace(" às", "").replace("  ", " ")

    # (dd/mm/yyyy HH:MM) ou (dd/mm/yyyy)
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(\d{1,2}):(\d{2}))?", text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        h, mi = (int(m.group(4)), int(m.group(5))) if m.group(4) else (9, 0)
        try:
            return tz.localize(datetime(y, mo, d, h, mi))
        except ValueError:
            return None

    # (dd/mm HH:MM) ou (dd/mm)
    m = re.search(r"(\d{1,2})/(\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?", text)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        h, mi = (int(m.group(3)), int(m.group(4))) if m.group(3) else (9, 0)
        year = now.year
        try:
            dt = tz.localize(datetime(year, mo, d, h, mi))
            if dt < now:
                dt = tz.localize(datetime(year + 1, mo, d, h, mi))
            return dt
        except ValueError:
            return None

    return None
_SHOW_CATEGORY_KEY = "detail_show_category"

_NOTE_TEXT = 1
_TITLE_TEXT = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_saude_task(task) -> bool:
    return bool(task.task_list and getattr(task.task_list, "slug", None) == "saude") or bool(task.category)


async def _refresh_detail(query, task_id: uuid.UUID, context: ContextTypes.DEFAULT_TYPE) -> None:
    listas = context.user_data.get(_MOVE_LISTAS_KEY, [])
    task, subtasks, dependents = await asyncio.gather(
        asyncio.to_thread(task_service.get_task_with_list, task_id),
        asyncio.to_thread(task_service.get_subtasks, task_id),
        asyncio.to_thread(task_service.get_tasks_blocked_by, task_id),
    )
    if task is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return
    blocking_task = None
    if task.blocked_by_task_id:
        blocking_task = await asyncio.to_thread(
            task_service.get_task_with_list, task.blocked_by_task_id
        )
    show_category = context.user_data.get(_SHOW_CATEGORY_KEY, _is_saude_task(task))
    await query.edit_message_text(
        textos.msg_task_detail(task, subtasks, blocking_task=blocking_task, blocked_dependents=dependents),
        reply_markup=keyboards.kb_task_detail(
            task, listas, subtasks,
            show_couple=context.user_data.get(_HAS_COUPLE_KEY, False),
            show_category=show_category,
        ),
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
        task, subtasks, dependents = await asyncio.gather(
            asyncio.to_thread(task_service.get_task_with_list, task_id),
            asyncio.to_thread(task_service.get_subtasks, task_id),
            asyncio.to_thread(task_service.get_tasks_blocked_by, task_id),
        )
        if task is None:
            await query.edit_message_text(textos.MSG_ERRO_GENERICO)
            return
        blocking_task = None
        if task.blocked_by_task_id:
            blocking_task = await asyncio.to_thread(
                task_service.get_task_with_list, task.blocked_by_task_id
            )
        show_category = _is_saude_task(task)
        context.user_data[_SHOW_CATEGORY_KEY] = show_category
        await query.edit_message_text(
            textos.msg_task_detail(task, subtasks, blocking_task=blocking_task, blocked_dependents=dependents),
            reply_markup=keyboards.kb_task_detail(
                task, listas_dicts, subtasks,
                show_couple=has_couple,
                show_category=show_category,
            ),
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
            update.effective_chat.id,
            context.bot,
            textos.msg_casal_compartilhou(actor, 1, updated.title),
            reply_markup=keyboards.kb_notif_ver_tarefa(task_id),
        )
    await _refresh_detail(query, task_id, context)


async def cb_task_remove_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pede confirmação para remover (descartar) uma tarefa — distinto de concluir."""
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    task_id = uuid.UUID(query.data.split(":")[1])
    task = await asyncio.to_thread(task_service.get_task_with_list, task_id)
    titulo = task.title if task else "essa tarefa"
    await query.edit_message_text(
        textos.msg_confirmar_remover(titulo),
        parse_mode="Markdown",
        reply_markup=keyboards.kb_confirmar_remover(task_id),
    )


async def cb_task_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove (descarta) a tarefa: status 'arquivada', sem marcar como concluída.

    Para tarefa de casal, avisa o par com mensagem neutra (não de conclusão).
    """
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    task_id = uuid.UUID(query.data.split(":")[1])
    chat_id = update.effective_chat.id
    try:
        task = await asyncio.to_thread(task_service.get_task_with_list, task_id)
        ok = await asyncio.to_thread(task_service.archive_task, task_id)
        if not ok or task is None:
            await query.edit_message_text(textos.MSG_ERRO_GENERICO)
            return
        if getattr(task, "couple_id", None) is not None:
            actor = (update.effective_user.full_name if update.effective_user else None) or "Seu par"
            await notify.notify_partner(
                chat_id, context.bot, textos.msg_casal_removeu(actor, task.title)
            )
        lists = await asyncio.to_thread(task_service.get_user_lists, chat_id)
        inbox_count = await asyncio.to_thread(task_service.get_inbox_count, chat_id)
        couple_count = await asyncio.to_thread(task_service.get_couple_task_count, chat_id)
        await query.edit_message_text(
            f"{textos.msg_tarefa_removida(task.title)}\n\n{textos.MSG_SUAS_LISTAS}",
            reply_markup=keyboards.kb_listas(lists, inbox_count, couple_count),
        )
    except Exception:
        logger.exception("Erro ao remover tarefa %s", task_id)
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)


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

_QUADRANT_TOOLTIP = {
    "1": "Q1 — Urgente e importante: fazer agora",
    "2": "Q2 — Importante, sem urgência: planejar",
    "3": "Q3 — Urgente, pouco importante: delegar ou fazer rápido",
    "4": "Q4 — Nem urgente nem importante: eliminar ou fazer no tempo livre",
}

async def cb_task_set_quadrant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, task_id_str, q_str = query.data.split(":")
    await query.answer(_QUADRANT_TOOLTIP.get(q_str, ""))
    if not is_authorized(update):
        return
    task_id = uuid.UUID(task_id_str)
    await asyncio.to_thread(task_service.update_task_attrs, task_id, quadrant=int(q_str))
    await _refresh_detail(query, task_id, context)


# ---------------------------------------------------------------------------
# Editar energia e estimativa (US-10)
# ---------------------------------------------------------------------------

_ENERGY_TOOLTIP = {
    "alta": "⚡ Alta — exige foco total; reserve um bom momento",
    "media": "🔋 Média — concentração normal",
    "baixa": "🪫 Baixa — dá pra fazer no piloto automático",
}

async def cb_task_set_energy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    parts = query.data.split(":")
    await query.answer(_ENERGY_TOOLTIP.get(parts[2], ""))
    if not is_authorized(update):
        return
    task_id = uuid.UUID(parts[1])
    await asyncio.to_thread(task_service.update_task_attrs, task_id, energy=parts[2])
    await _refresh_detail(query, task_id, context)


_ESTIMATE_TOOLTIP = {
    "5": "5 min — tarefa relâmpago",
    "15": "15 min — tarefa curta",
    "30": "30 min — meia hora",
    "60": "1 hora",
    "120": "2 horas ou mais",
}

async def cb_task_set_estimate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    parts = query.data.split(":")
    await query.answer(_ESTIMATE_TOOLTIP.get(parts[2], ""))
    if not is_authorized(update):
        return
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
# Prazo: presets de dias e data digitada (v1.20.0)
# ---------------------------------------------------------------------------

async def cb_task_due_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Define prazo como 'hoje + N dias' (callbacks task_dd:{id}:{days})."""
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    parts = query.data.split(":")
    task_id = uuid.UUID(parts[1])
    days = int(parts[2])
    tz = pytz.timezone(DEFAULT_TIMEZONE)
    due = (datetime.now(tz) + timedelta(days=days)).replace(hour=9, minute=0, second=0, microsecond=0)
    await asyncio.to_thread(task_service.update_task_attrs, task_id, due_at=due)
    await _refresh_detail(query, task_id, context)


async def cb_task_due_custom_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pede ao usuário que digite a data desejada."""
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    task_id_str = query.data.split(":")[1]
    context.user_data[_DUE_CUSTOM_KEY] = task_id_str
    await query.edit_message_text(
        "📅 Que data? Manda no formato:\n\n"
        "  20/07\n"
        "  20/07/2026\n"
        "  20/07 às 14:00\n"
        "  20/07/2026 14:00"
    )


async def handle_task_due_custom_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Intercepta texto quando aguardando data digitada. Retorna True se consumiu a mensagem."""
    task_id_str = context.user_data.get(_DUE_CUSTOM_KEY)
    if not task_id_str:
        return False
    text = (update.message.text or "").strip()
    if not text:
        return False
    context.user_data.pop(_DUE_CUSTOM_KEY, None)
    due = _parse_date_ptbr(text)
    if due is None:
        await update.message.reply_text(
            "Não entendi essa data 😕\n"
            "Tenta assim: 20/07, 20/07/2026 ou 20/07 às 14:00"
        )
        context.user_data[_DUE_CUSTOM_KEY] = task_id_str  # mantém estado
        return True
    task_id = uuid.UUID(task_id_str)
    await asyncio.to_thread(task_service.update_task_attrs, task_id, due_at=due)
    tz = pytz.timezone(DEFAULT_TIMEZONE)
    fmt = due.astimezone(tz).strftime("%d/%m/%Y às %H:%M")
    await update.message.reply_text(f"📅 Prazo definido para {fmt} ✅")
    return True


# ---------------------------------------------------------------------------
# Mover tarefa entre listas (US-07)
# ---------------------------------------------------------------------------

async def cb_task_start_move(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("📂 Escolha a lista destino")
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


async def _resolve_move_target(
    list_idx: int, listas: list[dict]
) -> tuple[uuid.UUID | None, str]:
    """Retorna (new_list_id, lista_nome) para o índice dado."""
    if list_idx == -1:
        return None, "Inbox"
    if 0 <= list_idx < len(listas):
        return uuid.UUID(listas[list_idx]["id"]), listas[list_idx]["name"]
    return None, ""  # índice inválido


async def _execute_move(query, task_id: uuid.UUID, new_list_id: uuid.UUID | None, context) -> None:
    """Executa o move e atualiza o detalhe. Trata BadRequest do Telegram separadamente."""
    from telegram.error import BadRequest as TelegramBadRequest
    try:
        await asyncio.to_thread(task_service.update_task_attrs, task_id, list_id=new_list_id)
        await _refresh_detail(query, task_id, context)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            # Tarefa já estava nessa lista — mostra toast e não altera a tela
            await query.answer(textos.MSG_MOVER_MESMA_LISTA, show_alert=True)
        else:
            logger.exception("Telegram BadRequest ao mover tarefa %s", task_id)
            await query.edit_message_text(textos.MSG_ERRO_GENERICO)
    except Exception:
        logger.exception("Erro ao mover tarefa %s para list_id=%s", task_id, new_list_id)
        await query.edit_message_text(
            "Não foi possível mover a tarefa 😕\n"
            "Tente novamente ou volte ao detalhe da tarefa."
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
    new_list_id, lista_nome = await _resolve_move_target(list_idx, listas)
    if list_idx != -1 and not lista_nome:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    # Verifica duplicata de nome na lista destino
    task = await asyncio.to_thread(task_service.get_task_with_list, task_id)
    if task is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    # Verifica se já está na lista destino
    current_list_id = task.list_id
    if current_list_id == new_list_id:
        await query.answer(textos.MSG_MOVER_MESMA_LISTA, show_alert=True)
        return

    duplicate = await asyncio.to_thread(
        task_service.task_title_exists_in_list, task.title, new_list_id, task_id
    )
    if duplicate:
        await query.edit_message_text(
            textos.msg_mover_duplicada(task.title, lista_nome),
            reply_markup=keyboards.kb_mover_confirmar_duplicata(task_id_str, list_idx),
            parse_mode="Markdown",
        )
        return

    await _execute_move(query, task_id, new_list_id, context)


async def cb_task_move_force(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirma a movimentação mesmo havendo duplicata de nome."""
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    parts = query.data.split(":")  # mv_force:{task_id}:{list_idx}
    task_id = uuid.UUID(parts[1])
    list_idx = int(parts[2])
    listas = context.user_data.get(_MOVE_LISTAS_KEY, [])

    new_list_id, lista_nome = await _resolve_move_target(list_idx, listas)
    if list_idx != -1 and not lista_nome:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    await _execute_move(query, task_id, new_list_id, context)


# ---------------------------------------------------------------------------
# Ordenação manual (US-11)
# ---------------------------------------------------------------------------

async def cb_task_reorder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    parts = query.data.split(":")
    direction = "up" if parts[0] == "task_up" else "down"
    tip = "⬆️ Moveu para cima na lista" if direction == "up" else "⬇️ Moveu para baixo na lista"
    await query.answer(tip)
    if not is_authorized(update):
        return
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

async def cb_task_set_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not is_authorized(update):
        await query.answer()
        return
    parts = query.data.split(":")
    task_id = uuid.UUID(parts[1])
    raw = parts[2]
    category = None if raw == "none" else raw
    await asyncio.to_thread(task_service.set_task_category, task_id, category)
    await query.answer("💊 Medicação" if category == "medicacao" else ("📅 Agendamento" if category == "agendamento" else "🏷️ Sem categoria"))
    await _refresh_detail(query, task_id, context)


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
