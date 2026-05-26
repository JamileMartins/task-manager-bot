"""Handler /foco — sessão de trabalho com timer (Pomodoro configurável)."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.handlers.common import deny_unauthorized, is_authorized
from src.utils import keyboards, textos

logger = logging.getLogger(__name__)

_FOCO_KEY = "foco"
_DEFAULT_WORK = 50
_DEFAULT_BREAK = 15


def _foco(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data.setdefault(_FOCO_KEY, {})


def _cancel_jobs(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    for name in (f"foco_w_{chat_id}", f"foco_b_{chat_id}"):
        for job in context.application.job_queue.get_jobs_by_name(name):
            job.schedule_removal()


# ---------------------------------------------------------------------------
# Job callbacks (disparados pelo scheduler)
# ---------------------------------------------------------------------------

async def _job_work_done(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data
    chat_id = data["chat_id"]
    work_min = data["work_min"]
    break_min = data["break_min"]
    ciclo = data["ciclo"]

    try:
        await context.bot.send_message(
            chat_id,
            textos.msg_foco_work_done(work_min, break_min, ciclo),
            reply_markup=keyboards.kb_foco_work_done(break_min),
        )
    except Exception:
        logger.exception("Erro ao enviar notificação de foco concluído")


async def _job_break_done(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data
    chat_id = data["chat_id"]
    work_min = data["work_min"]
    break_min = data["break_min"]
    ciclo = data["ciclo"]

    try:
        await context.bot.send_message(
            chat_id,
            textos.msg_foco_break_done(ciclo),
            reply_markup=keyboards.kb_foco_break_done(work_min, break_min),
        )
    except Exception:
        logger.exception("Erro ao enviar notificação de descanso concluído")


# ---------------------------------------------------------------------------
# /foco [work_min] [break_min]
# ---------------------------------------------------------------------------

async def cmd_foco(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return

    args = context.args or []
    try:
        work_min = int(args[0]) if len(args) >= 1 else _DEFAULT_WORK
        break_min = int(args[1]) if len(args) >= 2 else _DEFAULT_BREAK
    except ValueError:
        await msg.reply_text("Uso: /foco [minutos_trabalho] [minutos_descanso]\nExemplo: /foco 25 5")
        return

    work_min = max(1, min(work_min, 240))
    break_min = max(1, min(break_min, 60))

    chat_id = update.effective_chat.id
    _cancel_jobs(context, chat_id)

    foco = _foco(context)
    foco.update({"work_min": work_min, "break_min": break_min, "ciclo": 1})

    context.application.job_queue.run_once(
        _job_work_done,
        when=work_min * 60,
        name=f"foco_w_{chat_id}",
        data={"chat_id": chat_id, "work_min": work_min, "break_min": break_min, "ciclo": 1},
    )

    await msg.reply_text(
        textos.msg_foco_iniciado(work_min),
        reply_markup=keyboards.kb_foco_cancelar(),
    )


# ---------------------------------------------------------------------------
# Callbacks dos botões
# ---------------------------------------------------------------------------

async def cb_foco_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    chat_id = update.effective_chat.id
    _cancel_jobs(context, chat_id)
    foco = context.user_data.pop(_FOCO_KEY, {})
    ciclos = foco.get("ciclo", 1)
    work_min = foco.get("work_min", _DEFAULT_WORK)
    await query.edit_message_text(textos.msg_foco_encerrado(ciclos, work_min))


async def cb_foco_descanso(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    chat_id = update.effective_chat.id
    break_min = int(query.data.split(":")[1])
    foco = _foco(context)
    work_min = foco.get("work_min", _DEFAULT_WORK)
    ciclo = foco.get("ciclo", 1)

    context.application.job_queue.run_once(
        _job_break_done,
        when=break_min * 60,
        name=f"foco_b_{chat_id}",
        data={"chat_id": chat_id, "work_min": work_min, "break_min": break_min, "ciclo": ciclo},
    )
    await query.edit_message_text(textos.msg_foco_break_iniciado(break_min))


async def cb_foco_pular(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    foco = _foco(context)
    work_min = foco.get("work_min", _DEFAULT_WORK)
    break_min = foco.get("break_min", _DEFAULT_BREAK)
    ciclo = foco.get("ciclo", 1)
    await query.edit_message_text(
        textos.msg_foco_break_done(ciclo),
        reply_markup=keyboards.kb_foco_break_done(work_min, break_min),
    )


async def cb_foco_ciclo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    chat_id = update.effective_chat.id
    parts = query.data.split(":")
    work_min = int(parts[1])
    break_min = int(parts[2])

    foco = _foco(context)
    ciclo = foco.get("ciclo", 1) + 1
    foco["ciclo"] = ciclo
    foco["work_min"] = work_min
    foco["break_min"] = break_min

    _cancel_jobs(context, chat_id)
    context.application.job_queue.run_once(
        _job_work_done,
        when=work_min * 60,
        name=f"foco_w_{chat_id}",
        data={"chat_id": chat_id, "work_min": work_min, "break_min": break_min, "ciclo": ciclo},
    )
    await query.edit_message_text(
        textos.msg_foco_iniciado(work_min),
        reply_markup=keyboards.kb_foco_cancelar(),
    )


async def cb_foco_encerrar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_authorized(update):
        return
    chat_id = update.effective_chat.id
    _cancel_jobs(context, chat_id)
    foco = context.user_data.pop(_FOCO_KEY, {})
    ciclos = foco.get("ciclo", 1)
    work_min = foco.get("work_min", _DEFAULT_WORK)
    await query.edit_message_text(textos.msg_foco_encerrado(ciclos, work_min))


async def cmd_parar_foco(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        await deny_unauthorized(update)
        return
    msg = update.effective_message
    if not msg:
        return
    chat_id = update.effective_chat.id
    _cancel_jobs(context, chat_id)
    foco = context.user_data.pop(_FOCO_KEY, {})
    if not foco:
        await msg.reply_text(textos.MSG_FOCO_NENHUM_ATIVO)
        return
    ciclos = foco.get("ciclo", 1)
    work_min = foco.get("work_min", _DEFAULT_WORK)
    await msg.reply_text(textos.msg_foco_encerrado(ciclos, work_min))
