"""Configurações do bot (/config — US-20)."""
from __future__ import annotations

import logging
from datetime import time

import pytz
from telegram import Update
from telegram.ext import ContextTypes

from src.config import AUTHORIZED_CHAT_ID
from src.services.task_service import get_config, update_config
from src.utils.keyboards import (
    kb_config,
    kb_config_daily_time,
    kb_config_review_dow,
    kb_config_review_time,
)
from src.utils.textos import msg_config_status

logger = logging.getLogger(__name__)


def _guard(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.id == AUTHORIZED_CHAT_ID)


async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _guard(update):
        return
    msg = update.effective_message
    if not msg:
        return
    cfg = get_config(update.effective_chat.id)
    await msg.reply_text(msg_config_status(cfg), reply_markup=kb_config())


async def cb_config_daily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if update.effective_message:
        await update.effective_message.edit_reply_markup(kb_config_daily_time())


async def cb_config_set_daily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """cfg_dt:{HH:MM}"""
    query = update.callback_query
    time_str = query.data.split(":", 1)[1]
    h, m = map(int, time_str.split(":"))
    t = time(hour=h, minute=m)
    chat_id = update.effective_chat.id
    update_config(chat_id, daily_summary_time=t)
    _reschedule_daily(context, chat_id, t)
    await query.answer(f"Resumo diário: {time_str} ✅")
    cfg = get_config(chat_id)
    if update.effective_message:
        await update.effective_message.edit_text(msg_config_status(cfg), reply_markup=kb_config())


async def cb_config_rev_dow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if update.effective_message:
        await update.effective_message.edit_reply_markup(kb_config_review_dow())


async def cb_config_set_dow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """cfg_rdow:{dow} — salva dia e pede horário."""
    query = update.callback_query
    dow = int(query.data.split(":", 1)[1])
    context.user_data["cfg_dow_pending"] = dow
    await query.answer()
    if update.effective_message:
        await update.effective_message.edit_reply_markup(kb_config_review_time())


async def cb_config_set_rtime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """cfg_rt:{HH:MM}"""
    query = update.callback_query
    time_str = query.data.split(":", 1)[1]
    h, m = map(int, time_str.split(":"))
    t = time(hour=h, minute=m)
    chat_id = update.effective_chat.id
    dow = context.user_data.pop("cfg_dow_pending", None)
    kwargs: dict = {"weekly_review_time": t}
    if dow is not None:
        kwargs["weekly_review_dow"] = dow
    update_config(chat_id, **kwargs)
    cfg = get_config(chat_id)
    if cfg:
        _reschedule_weekly(context, chat_id, cfg)
    await query.answer("Revisão semanal configurada ✅")
    if update.effective_message:
        await update.effective_message.edit_text(msg_config_status(cfg), reply_markup=kb_config())


async def cb_config_off_daily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    update_config(chat_id, daily_summary_time=None)
    _cancel_job(context, f"daily_{chat_id}")
    await query.answer("Resumo diário desativado")
    cfg = get_config(chat_id)
    if update.effective_message:
        await update.effective_message.edit_text(msg_config_status(cfg), reply_markup=kb_config())


async def cb_config_off_rev(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = update.effective_chat.id
    update_config(chat_id, weekly_review_time=None, weekly_review_dow=None)
    _cancel_job(context, f"weekly_{chat_id}")
    await query.answer("Revisão semanal desativada")
    cfg = get_config(chat_id)
    if update.effective_message:
        await update.effective_message.edit_text(msg_config_status(cfg), reply_markup=kb_config())


async def cb_config_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if update.effective_message:
        await update.effective_message.edit_reply_markup(kb_config())


# ---------------------------------------------------------------------------
# Helpers de agendamento
# ---------------------------------------------------------------------------

def _cancel_job(context: ContextTypes.DEFAULT_TYPE, name: str) -> None:
    for job in context.application.job_queue.get_jobs_by_name(name):
        job.schedule_removal()


def _reschedule_daily(context: ContextTypes.DEFAULT_TYPE, chat_id: int, t: time) -> None:
    from src.handlers.rituals import send_daily_summary
    _cancel_job(context, f"daily_{chat_id}")
    tz = pytz.timezone("America/Fortaleza")
    aware = time(hour=t.hour, minute=t.minute, tzinfo=tz)
    context.application.job_queue.run_daily(
        send_daily_summary,
        time=aware,
        name=f"daily_{chat_id}",
        data={"chat_id": chat_id},
    )


def _reschedule_weekly(context: ContextTypes.DEFAULT_TYPE, chat_id: int, cfg) -> None:
    from src.handlers.rituals import send_weekly_review
    _cancel_job(context, f"weekly_{chat_id}")
    if cfg.weekly_review_time is None:
        return
    tz = pytz.timezone("America/Fortaleza")
    t = cfg.weekly_review_time
    aware = time(hour=t.hour, minute=t.minute, tzinfo=tz)
    context.application.job_queue.run_daily(
        send_weekly_review,
        time=aware,
        name=f"weekly_{chat_id}",
        data={"chat_id": chat_id},
    )
