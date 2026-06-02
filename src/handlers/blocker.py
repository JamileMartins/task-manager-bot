"""Handlers do fluxo de impedimentos (F4 — US-23, 24, 25, 26, 28)."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import timedelta

import pytz
from telegram import Update
from telegram.ext import ContextTypes

from src.config import DEFAULT_TIMEZONE
from src.handlers.common import is_authorized
from src.services import ai_service, task_service
from src.utils import keyboards, textos

logger = logging.getLogger(__name__)

_BLK_TASK_KEY = "blk_task_id"
_BLK_STEP_KEY = "blk_next_step"
_BLK_NOTE_KEY = "blk_note_task_id"   # set quando aguardando texto de nota do usuário
_BLK_DEP_TASKS_KEY = "blk_dep_tasks" # lista de tasks disponíveis para seleção de dependência


async def _offer_note(query, task_id: uuid.UUID) -> None:
    """Envia mensagem separada oferecendo o campo de nota livre."""
    await query.message.reply_text(
        textos.MSG_BLOCKER_NOTA_PEDIR,
        reply_markup=keyboards.kb_blocker_nota(task_id),
        parse_mode="Markdown",
    )


def _now_tz():
    return __import__("datetime").datetime.now(pytz.timezone(DEFAULT_TIMEZONE))


def _parse(data: str, prefix: str) -> tuple[uuid.UUID, str]:
    """Extrai task_id e resto após o prefixo."""
    rest = data[len(prefix):]
    parts = rest.split(":", 1)
    return uuid.UUID(parts[0]), (parts[1] if len(parts) > 1 else "")


# ---------------------------------------------------------------------------
# Entrada: mostrar seleção de tipo de impedimento
# ---------------------------------------------------------------------------

async def cb_blocker_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id = uuid.UUID(query.data.split(":")[1])
    context.user_data[_BLK_TASK_KEY] = str(task_id)

    task = await asyncio.to_thread(task_service.get_task_with_list, task_id)
    if task is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    await query.edit_message_text(
        textos.msg_blocker_pergunta(task.title),
        reply_markup=keyboards.kb_blocker_types(task_id),
    )


# ---------------------------------------------------------------------------
# Seleção de tipo de impedimento
# ---------------------------------------------------------------------------

async def cb_blocker_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id, blocker_type = _parse(query.data, "blk_t:")
    context.user_data[_BLK_TASK_KEY] = str(task_id)

    task = await asyncio.to_thread(task_service.get_task_with_list, task_id)
    if task is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    # Salva o tipo de impedimento
    await asyncio.to_thread(task_service.set_blocker, task_id, blocker_type)

    if blocker_type == "vaga_grande":
        await _handle_vaga_grande(query, context, task)

    elif blocker_type == "decisao_pendente":
        await query.edit_message_text(
            textos.msg_blocker_decidir(task.title),
            reply_markup=keyboards.kb_blocker_decidir(task_id),
        )

    elif blocker_type == "aversiva_energia":
        # Reduz estimativa para deixar a tarefa mais acessível (se > 30 min, divide pela metade)
        new_estimate = None
        if task.estimate_min and task.estimate_min > 30:
            new_estimate = max(15, task.estimate_min // 2)
            await asyncio.to_thread(
                task_service.update_task_attrs, task_id, energy="alta", estimate_min=new_estimate
            )
        else:
            await asyncio.to_thread(task_service.update_task_attrs, task_id, energy="alta")
        await query.edit_message_text(
            textos.msg_blocker_aversiva(new_estimate),
            parse_mode="Markdown",
        )

    elif blocker_type == "pessoa":
        await query.edit_message_text(
            textos.MSG_BLOCKER_PESSOA,
            reply_markup=keyboards.kb_blocker_pessoa(task_id),
        )

    elif blocker_type == "recurso_info":
        await query.edit_message_text(
            textos.msg_blocker_recurso(task.title),
            reply_markup=keyboards.kb_blocker_recurso(task_id),
        )

    elif blocker_type == "data_externa":
        await query.edit_message_text(
            textos.MSG_BLOCKER_DATA_QUANDO,
            reply_markup=keyboards.kb_blocker_data_externa(task_id),
        )

    elif blocker_type == "tarefa_bloqueadora":
        chat_id = update.effective_chat.id
        tasks = await asyncio.to_thread(
            task_service.get_pending_tasks_for_selection, chat_id, task_id
        )
        if not tasks:
            await query.edit_message_text(textos.MSG_BLOCKER_DEPENDE_VAZIA)
            return
        context.user_data[_BLK_DEP_TASKS_KEY] = [str(t.id) for t in tasks]
        await query.edit_message_text(
            textos.MSG_BLOCKER_DEPENDE_ESCOLHA,
            reply_markup=keyboards.kb_blocker_task_select(tasks, task_id, page=0),
        )
        return  # fluxo continua em cb_blocker_dep_pick

    elif blocker_type == "obsoleta":
        await query.edit_message_text(
            textos.MSG_BLOCKER_OBSOLETA,
            reply_markup=keyboards.kb_blocker_obsoleta(task_id),
        )


# ---------------------------------------------------------------------------
# vaga_grande — sugestão de próximo passo via IA
# ---------------------------------------------------------------------------

async def _handle_vaga_grande(query, context, task) -> None:
    await query.edit_message_text("Pensando no primeiro passo... 🧠")
    passo = await asyncio.to_thread(ai_service.suggest_next_step, task.title)
    context.user_data[_BLK_STEP_KEY] = passo
    await query.edit_message_text(
        textos.msg_blocker_vaga_sugestao(passo),
        reply_markup=keyboards.kb_blocker_next_step(task.id),
    )


async def cb_blocker_next_step_ok(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cria a subtarefa com o próximo passo sugerido."""
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id = uuid.UUID(query.data.split(":")[1])
    passo = context.user_data.get(_BLK_STEP_KEY, "Dar o primeiro passo")

    subtask = await asyncio.to_thread(task_service.create_subtask, task_id, passo)
    if subtask is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    await query.edit_message_text(
        f"Subtarefa criada ✅\n\n👉 {passo}\n\nQuando terminar, marca como concluída lá na lista."
    )


async def cb_blocker_next_step_retry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pede nova sugestão de próximo passo à IA."""
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id = uuid.UUID(query.data.split(":")[1])
    task = await asyncio.to_thread(task_service.get_task_with_list, task_id)
    if task is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    await _handle_vaga_grande(query, context, task)


# ---------------------------------------------------------------------------
# decisao_pendente — criar tarefa "Decidir X"
# ---------------------------------------------------------------------------

async def cb_blocker_decidir_ok(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id = uuid.UUID(query.data.split(":")[1])
    task = await asyncio.to_thread(task_service.get_task_with_list, task_id)
    if task is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    nova = await asyncio.to_thread(
        task_service.create_related_task, task_id, f"Decidir: {task.title}", quadrant=2
    )
    if nova is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    await query.edit_message_text(
        f"Tarefa criada ✅\n\n👉 Decidir: {task.title}\n\nQuando decidir, volta aqui e destrava a original."
    )


# ---------------------------------------------------------------------------
# recurso_info — criar subtarefa "Obter necessário"
# ---------------------------------------------------------------------------

async def cb_blocker_recurso_ok(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id = uuid.UUID(query.data.split(":")[1])
    task = await asyncio.to_thread(task_service.get_task_with_list, task_id)
    if task is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    titulo = f"Obter o necessário para: {task.title}"
    subtask = await asyncio.to_thread(task_service.create_subtask, task_id, titulo)
    if subtask is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    await query.edit_message_text(
        f"Passo criado ✅\n\n👉 {titulo}\n\nAssim que tiver o que precisa, volta e destrava a tarefa principal."
    )


# ---------------------------------------------------------------------------
# pessoa — aguardando ou cobrança
# ---------------------------------------------------------------------------

async def cb_blocker_aguardar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id = uuid.UUID(query.data.split(":")[1])
    await asyncio.to_thread(task_service.set_waiting, task_id)
    await query.edit_message_text(textos.MSG_BLOCKER_AGUARDANDO)
    await _offer_note(query, task_id)


async def cb_blocker_cobrar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id = uuid.UUID(query.data.split(":")[1])
    context.user_data[_BLK_TASK_KEY] = str(task_id)
    await asyncio.to_thread(task_service.set_waiting, task_id)
    await query.edit_message_text(
        textos.MSG_BLOCKER_COBRAR_QUANDO,
        reply_markup=keyboards.kb_blocker_cobrar_date(task_id),
    )


async def cb_blocker_cobrar_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id, days_str = _parse(query.data, "blk_cd:")
    days = int(days_str)

    task = await asyncio.to_thread(task_service.get_task_with_list, task_id)
    if task is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    tz = pytz.timezone(DEFAULT_TIMEZONE)
    remind_at = _now_tz() + timedelta(days=days)
    remind_at = remind_at.replace(hour=9, minute=0, second=0, microsecond=0)

    titulo_cobranca = f"Cobrar: {task.title}"
    nova = await asyncio.to_thread(
        task_service.create_related_task, task_id, titulo_cobranca, quadrant=2
    )

    data_fmt = remind_at.strftime("%d/%m")
    await query.edit_message_text(textos.msg_blocker_cobrar_ok(data_fmt))
    await _offer_note(query, task_id)


# ---------------------------------------------------------------------------
# data_externa — definir data e colocar aguardando
# ---------------------------------------------------------------------------

async def cb_blocker_data_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id, days_str = _parse(query.data, "blk_dd:")
    days = int(days_str)

    tz = pytz.timezone(DEFAULT_TIMEZONE)
    due = _now_tz() + timedelta(days=days)
    due = due.replace(hour=9, minute=0, second=0, microsecond=0)

    await asyncio.to_thread(task_service.set_waiting, task_id, due_at=due)
    data_fmt = due.strftime("%d/%m")
    await query.edit_message_text(textos.msg_blocker_data_ok(data_fmt))
    await _offer_note(query, task_id)


# ---------------------------------------------------------------------------
# obsoleta — arquivar
# ---------------------------------------------------------------------------

async def cb_blocker_archive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id = uuid.UUID(query.data.split(":")[1])
    await asyncio.to_thread(task_service.complete_task, task_id)
    await query.edit_message_text(textos.MSG_BLOCKER_ARQUIVADA)


async def cb_blocker_keep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    await query.edit_message_text(textos.MSG_BLOCKER_KEEP)


# ---------------------------------------------------------------------------
# Nota livre no impedimento
# ---------------------------------------------------------------------------

async def cb_blocker_nota_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sinaliza que o próximo texto do usuário será a nota do impedimento."""
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id_str = query.data.split(":")[1]
    context.user_data[_BLK_NOTE_KEY] = task_id_str
    await query.edit_message_text(textos.MSG_BLOCKER_NOTA_MANDE)


async def cb_blocker_nota_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Usuária optou por não adicionar nota."""
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    context.user_data.pop(_BLK_NOTE_KEY, None)
    await query.edit_message_text("Ok, sem nota ✅")


async def handle_blocker_note_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Intercepta texto livre quando há nota de bloqueio pendente.

    Retorna True se o texto foi consumido como nota (handler de captura deve parar).
    """
    task_id_str = context.user_data.get(_BLK_NOTE_KEY)
    if not task_id_str:
        return False

    note = (update.message.text or "").strip()
    if not note:
        return False

    context.user_data.pop(_BLK_NOTE_KEY, None)
    await asyncio.to_thread(task_service.set_blocker_note, task_id_str, note)
    await update.message.reply_text(textos.MSG_BLOCKER_NOTA_SALVA)
    return True


# ---------------------------------------------------------------------------
# Dependência de tarefa (tarefa_bloqueadora)
# ---------------------------------------------------------------------------

async def cb_blocker_dep_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Usuária escolheu a tarefa que bloqueia a atual."""
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    # blk_dep:{blocked_task_id}:{blocking_task_id}
    parts = query.data.split(":")
    blocked_id = uuid.UUID(parts[1])
    blocking_id = uuid.UUID(parts[2])

    blocking_task = await asyncio.to_thread(task_service.get_task_with_list, blocking_id)
    if blocking_task is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    await asyncio.to_thread(task_service.set_blocked_by_task, blocked_id, blocking_id)
    context.user_data.pop(_BLK_DEP_TASKS_KEY, None)

    await query.edit_message_text(
        textos.msg_blocker_depende_ok(blocking_task.title),
        parse_mode="Markdown",
    )


async def cb_blocker_dep_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Paginação na lista de seleção de tarefa bloqueadora."""
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    # blk_tp:{blocked_task_id}:{page}
    parts = query.data.split(":")
    blocked_id = uuid.UUID(parts[1])
    page = int(parts[2])

    chat_id = update.effective_chat.id
    tasks = await asyncio.to_thread(
        task_service.get_pending_tasks_for_selection, chat_id, blocked_id
    )
    if not tasks:
        await query.edit_message_text(textos.MSG_BLOCKER_DEPENDE_VAZIA)
        return

    await query.edit_message_reply_markup(
        reply_markup=keyboards.kb_blocker_task_select(tasks, blocked_id, page=page),
    )


# ---------------------------------------------------------------------------
# Desbloquear (US-28)
# ---------------------------------------------------------------------------

async def cb_unblock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return

    task_id = uuid.UUID(query.data.split(":")[1])
    task = await asyncio.to_thread(task_service.unblock_task, task_id)
    if task is None:
        await query.edit_message_text(textos.MSG_ERRO_GENERICO)
        return

    await query.edit_message_text(textos.MSG_UNBLOCK_OK)
