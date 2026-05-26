"""Rituais: resumo diário (US-15) e revisão semanal (US-16)."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timezone

import pytz
from telegram import Update
from telegram.ext import ContextTypes

from src.config import AUTHORIZED_CHAT_ID
from src.services.task_service import (
    archive_task,
    get_config,
    get_conquistas,
    get_daily_summary_tasks,
    get_due_reminders,
    get_due_waiting_tasks,
    get_overdue_unalerted_tasks,
    get_stale_tasks,
    get_stale_waiting_tasks,
    get_task_with_list,
    is_paused,
    mark_due_alerted,
    mark_reminder_sent,
    reschedule_task,
    reset_waiting_since,
    set_energia_do_dia,
    unblock_task,
)
from src.utils.keyboards import (
    kb_blocker_cobrar_date,
    kb_energia_do_dia,
    kb_lembrete,
    kb_prazo_vencido,
    kb_revisao_abertura,
    kb_revisao_espera,
    kb_revisao_reagendar,
    kb_revisao_tarefa,
)
from src.utils.textos import (
    MSG_DIARIO_VAZIO,
    MSG_ENERGIA_DO_DIA_CHECK,
    MSG_ENERGIA_DO_DIA_SALVA,
    MSG_REVISAO_ESPERAS_ABERTURA,
    MSG_REVISAO_NADA,
    msg_auto_unblock,
    msg_conquistas_diario,
    msg_diario_focos,
    msg_lembrete,
    msg_prazo_vencido,
    msg_revisao_abertura,
    msg_revisao_encerramento,
    msg_revisao_espera,
    msg_revisao_tarefa,
)

logger = logging.getLogger(__name__)

_REV_KEY = "rev"


def _rev(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> dict:
    return context.application.user_data.setdefault(chat_id, {}).setdefault(_REV_KEY, {})


def _rev_clear(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    context.application.user_data.get(chat_id, {}).pop(_REV_KEY, None)


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

async def send_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job a cada minuto: dispara lembretes vencidos (US-17) e desbloqueia tarefas aguardando por data (US-28)."""
    if is_paused(AUTHORIZED_CHAT_ID):
        return
    try:
        due = get_due_reminders()
    except Exception:
        logger.exception("Erro ao buscar lembretes vencidos")
        return

    for reminder, task, chat_id in due:
        try:
            await context.bot.send_message(
                chat_id,
                msg_lembrete(task.title),
                reply_markup=kb_lembrete(task.id),
                parse_mode="Markdown",
            )
            mark_reminder_sent(reminder.id)
        except Exception:
            logger.exception("Erro ao enviar lembrete %s", reminder.id)

    try:
        waiting = get_due_waiting_tasks()
    except Exception:
        logger.exception("Erro ao buscar tarefas aguardando vencidas")
        return

    for task, chat_id in waiting:
        try:
            unblock_task(task.id)
            await context.bot.send_message(
                chat_id,
                msg_auto_unblock(task.title),
                parse_mode="Markdown",
            )
        except Exception:
            logger.exception("Erro ao desbloquear tarefa %s por data", task.id)

    try:
        overdue = get_overdue_unalerted_tasks()
    except Exception:
        logger.exception("Erro ao buscar tarefas com prazo vencido")
        return

    for task, chat_id in overdue:
        try:
            mark_due_alerted(task.id)
            await context.bot.send_message(
                chat_id,
                msg_prazo_vencido(task.title),
                reply_markup=kb_prazo_vencido(task.id),
                parse_mode="Markdown",
            )
        except Exception:
            logger.exception("Erro ao alertar prazo vencido da tarefa %s", task.id)


async def send_daily_summary(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.data["chat_id"]
    if is_paused(chat_id):
        return
    today_tasks, focus_tasks = get_daily_summary_tasks(chat_id)
    stats = get_conquistas(chat_id)

    if not today_tasks and not focus_tasks:
        text = MSG_DIARIO_VAZIO
    else:
        text = msg_diario_focos(today_tasks, focus_tasks)

    if stats.get("ontem", 0) > 0:
        text = msg_conquistas_diario(stats["ontem"]) + "\n\n" + text

    await context.bot.send_message(chat_id, text)
    await context.bot.send_message(
        chat_id,
        MSG_ENERGIA_DO_DIA_CHECK,
        reply_markup=kb_energia_do_dia(),
    )


async def send_weekly_review(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.data["chat_id"]
    if is_paused(chat_id):
        return

    cfg = get_config(chat_id)
    if cfg and cfg.weekly_review_dow is not None:
        tz = pytz.timezone("America/Fortaleza")
        if datetime.now(tz).weekday() != cfg.weekly_review_dow:
            return

    stale = get_stale_tasks(chat_id)
    waiting = get_stale_waiting_tasks(chat_id)
    n_total = len(stale) + len(waiting)

    if n_total == 0:
        await context.bot.send_message(chat_id, MSG_REVISAO_NADA)
        return

    rev = _rev(context, chat_id)
    rev["stale_ids"] = [str(t.id) for t in stale]
    rev["wait_ids"] = [str(t.id) for t in waiting]
    rev["stale_idx"] = 0
    rev["wait_idx"] = 0
    rev["phase"] = "stale" if stale else "wait"
    rev["stats"] = {"reagendadas": 0, "arquivadas": 0, "destravadas": 0}

    await context.bot.send_message(
        chat_id,
        msg_revisao_abertura(n_total),
        reply_markup=kb_revisao_abertura(),
    )


# ---------------------------------------------------------------------------
# Review flow
# ---------------------------------------------------------------------------

async def _send_next_rev(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    rev = _rev(context, chat_id)
    now = datetime.now(timezone.utc)

    if rev.get("phase") == "stale":
        ids = rev.get("stale_ids", [])
        while True:
            idx = rev.get("stale_idx", 0)
            if idx >= len(ids):
                if rev.get("wait_ids"):
                    rev["phase"] = "wait"
                    await context.bot.send_message(chat_id, MSG_REVISAO_ESPERAS_ABERTURA)
                    await _send_next_rev(context, chat_id)
                else:
                    await _close_rev(context, chat_id)
                return
            task = get_task_with_list(ids[idx])
            if task is None or task.status != "aberta":
                rev["stale_idx"] = idx + 1
                continue
            touched = task.last_touched_at
            if touched.tzinfo is None:
                touched = touched.replace(tzinfo=timezone.utc)
            dias = max(0, (now - touched).days)
            await context.bot.send_message(
                chat_id,
                msg_revisao_tarefa(task, dias),
                reply_markup=kb_revisao_tarefa(task.id),
            )
            return

    elif rev.get("phase") == "wait":
        ids = rev.get("wait_ids", [])
        while True:
            idx = rev.get("wait_idx", 0)
            if idx >= len(ids):
                await _close_rev(context, chat_id)
                return
            task = get_task_with_list(ids[idx])
            if task is None or task.status != "aguardando":
                rev["wait_idx"] = idx + 1
                continue
            ws = task.waiting_since
            if ws and ws.tzinfo is None:
                ws = ws.replace(tzinfo=timezone.utc)
            dias = max(0, (now - ws).days) if ws else 0
            await context.bot.send_message(
                chat_id,
                msg_revisao_espera(task, dias),
                reply_markup=kb_revisao_espera(task.id),
            )
            return

    else:
        await _close_rev(context, chat_id)


async def _close_rev(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    stats = _rev(context, chat_id).get("stats", {})
    _rev_clear(context, chat_id)
    conquistas = await asyncio.to_thread(get_conquistas, chat_id)
    dias_ativos = conquistas.get("dias_ativos", 0)
    await context.bot.send_message(chat_id, msg_revisao_encerramento(stats, dias_ativos))


def _advance_stale(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    rev = _rev(context, chat_id)
    rev["stale_idx"] = rev.get("stale_idx", 0) + 1


def _advance_wait(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    rev = _rev(context, chat_id)
    rev["wait_idx"] = rev.get("wait_idx", 0) + 1


# ---------------------------------------------------------------------------
# Callback handlers
# ---------------------------------------------------------------------------

async def cb_rev_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return
    await msg.edit_reply_markup(None)
    await _send_next_rev(context, update.effective_chat.id)


async def cb_rev_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return
    _rev_clear(context, update.effective_chat.id)
    await msg.edit_text("Ok, revisão cancelada. Até a próxima 😊")


async def cb_rev_manter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return
    await update.callback_query.answer()
    await msg.edit_reply_markup(None)
    chat_id = update.effective_chat.id
    _advance_stale(context, chat_id)
    await _send_next_rev(context, chat_id)


async def cb_rev_arch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return
    query = update.callback_query
    task_id = query.data.split(":", 1)[1]
    archive_task(task_id)
    rev = _rev(context, update.effective_chat.id)
    rev.setdefault("stats", {})
    rev["stats"]["arquivadas"] = rev["stats"].get("arquivadas", 0) + 1
    await query.answer("Arquivada ✅")
    await msg.edit_reply_markup(None)
    chat_id = update.effective_chat.id
    _advance_stale(context, chat_id)
    await _send_next_rev(context, chat_id)


async def cb_rev_reagendar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return
    query = update.callback_query
    task_id = query.data.split(":", 1)[1]
    await query.answer()
    await msg.edit_reply_markup(kb_revisao_reagendar(task_id))


async def cb_rev_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return
    query = update.callback_query
    parts = query.data.split(":")
    task_id = parts[1]
    days = int(parts[2])
    reschedule_task(task_id, days)
    rev = _rev(context, update.effective_chat.id)
    rev.setdefault("stats", {})
    rev["stats"]["reagendadas"] = rev["stats"].get("reagendadas", 0) + 1
    await query.answer("Reagendada 📅")
    await msg.edit_reply_markup(None)
    chat_id = update.effective_chat.id
    _advance_stale(context, chat_id)
    await _send_next_rev(context, chat_id)


async def cb_rev_wait_cobrar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return
    query = update.callback_query
    task_id = query.data.split(":", 1)[1]
    await query.answer()
    await msg.edit_reply_markup(kb_blocker_cobrar_date(task_id))


async def cb_rev_wait_destravar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return
    query = update.callback_query
    task_id = query.data.split(":", 1)[1]
    unblock_task(task_id)
    rev = _rev(context, update.effective_chat.id)
    rev.setdefault("stats", {})
    rev["stats"]["destravadas"] = rev["stats"].get("destravadas", 0) + 1
    await query.answer("Destravada ✅")
    await msg.edit_reply_markup(None)
    chat_id = update.effective_chat.id
    _advance_wait(context, chat_id)
    await _send_next_rev(context, chat_id)


async def cb_rev_wait_arch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return
    query = update.callback_query
    task_id = query.data.split(":", 1)[1]
    archive_task(task_id)
    rev = _rev(context, update.effective_chat.id)
    rev.setdefault("stats", {})
    rev["stats"]["arquivadas"] = rev["stats"].get("arquivadas", 0) + 1
    await query.answer("Arquivada ✅")
    await msg.edit_reply_markup(None)
    chat_id = update.effective_chat.id
    _advance_wait(context, chat_id)
    await _send_next_rev(context, chat_id)


async def cb_rev_wait_seguir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg:
        return
    query = update.callback_query
    task_id = query.data.split(":", 1)[1]
    reset_waiting_since(task_id)
    await query.answer()
    await msg.edit_reply_markup(None)
    chat_id = update.effective_chat.id
    _advance_wait(context, chat_id)
    await _send_next_rev(context, chat_id)


# ---------------------------------------------------------------------------
# Energia do dia (Sugestão #1)
# ---------------------------------------------------------------------------

async def cb_set_energia_dia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    from src.handlers.common import is_authorized
    if not is_authorized(update):
        return
    energia = query.data.split(":")[1]
    await asyncio.to_thread(set_energia_do_dia, update.effective_chat.id, energia)
    await query.edit_message_text(MSG_ENERGIA_DO_DIA_SALVA)


# ---------------------------------------------------------------------------
# Prazo vencido (Sugestão #4)
# ---------------------------------------------------------------------------

async def cb_overdue_adiar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    from src.handlers.common import is_authorized
    if not is_authorized(update):
        return
    task_id = query.data.split(":")[1]
    await asyncio.to_thread(reschedule_task, task_id, 1)
    await query.edit_message_text("📅 Adiada para amanhã.")


async def cb_overdue_arch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    from src.handlers.common import is_authorized
    if not is_authorized(update):
        return
    task_id = query.data.split(":")[1]
    await asyncio.to_thread(archive_task, task_id)
    await query.edit_message_text("🗑️ Arquivada.")


# ---------------------------------------------------------------------------
# Job setup
# ---------------------------------------------------------------------------

def setup_jobs(app, chat_id: int) -> None:
    cfg = get_config(chat_id)
    if cfg is None:
        return
    _schedule_daily(app, chat_id, cfg)
    _schedule_weekly(app, chat_id, cfg)
    app.job_queue.run_repeating(send_reminders, interval=60, first=10, name="reminders")


def _schedule_daily(app, chat_id: int, cfg) -> None:
    if cfg.daily_summary_time is None:
        return
    tz = pytz.timezone("America/Fortaleza")
    t = time(hour=cfg.daily_summary_time.hour, minute=cfg.daily_summary_time.minute, tzinfo=tz)
    app.job_queue.run_daily(
        send_daily_summary,
        time=t,
        name=f"daily_{chat_id}",
        data={"chat_id": chat_id},
    )
    logger.info("Resumo diário agendado às %s para chat_id=%s", t, chat_id)


def _schedule_weekly(app, chat_id: int, cfg) -> None:
    if cfg.weekly_review_time is None:
        return
    tz = pytz.timezone("America/Fortaleza")
    t = time(hour=cfg.weekly_review_time.hour, minute=cfg.weekly_review_time.minute, tzinfo=tz)
    app.job_queue.run_daily(
        send_weekly_review,
        time=t,
        name=f"weekly_{chat_id}",
        data={"chat_id": chat_id},
    )
    logger.info("Revisão semanal agendada às %s para chat_id=%s", t, chat_id)

