"""Testes do roteamento de notificação ao parceiro (Fase C4)."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from telegram.error import TelegramError

from src.handlers import notify


class FakeBot:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id, text, *args, **kwargs):
        if self.fail:
            raise TelegramError("falhou")
        self.sent.append((chat_id, text))


@pytest.fixture(autouse=True)
def _clear_registry():
    notify._bot_by_chat.clear()
    yield
    notify._bot_by_chat.clear()


@pytest.fixture
def _no_pause():
    with patch("src.handlers.notify.task_service.is_paused", return_value=False):
        yield


def _patch_partner(partner_id):
    return patch("src.handlers.notify.couple_service.partner_chat_id", return_value=partner_id)


@pytest.mark.asyncio
async def test_notifica_pelo_fallback_sem_registro(_no_pause):
    bot = FakeBot()
    with _patch_partner(222):
        ok = await notify.notify_partner(111, bot, "oi")
    assert ok is True
    assert bot.sent == [(222, "oi")]


@pytest.mark.asyncio
async def test_sem_parceiro_nao_envia(_no_pause):
    bot = FakeBot()
    with _patch_partner(None):
        ok = await notify.notify_partner(111, bot, "oi")
    assert ok is False
    assert bot.sent == []


@pytest.mark.asyncio
async def test_respeita_pausa_do_parceiro():
    bot = FakeBot()
    with _patch_partner(222), patch("src.handlers.notify.task_service.is_paused", return_value=True):
        ok = await notify.notify_partner(111, bot, "oi")
    assert ok is False
    assert bot.sent == []


@pytest.mark.asyncio
async def test_prefere_bot_registrado_do_parceiro(_no_pause):
    bot_parceiro = FakeBot()
    bot_fallback = FakeBot()
    notify.remember_bot(222, bot_parceiro)
    with _patch_partner(222):
        await notify.notify_partner(111, bot_fallback, "oi")
    assert bot_parceiro.sent == [(222, "oi")]
    assert bot_fallback.sent == []


@pytest.mark.asyncio
async def test_tenta_proximo_bot_quando_um_falha(_no_pause):
    bot_ruim = FakeBot(fail=True)
    bot_bom = FakeBot()
    notify.remember_bot(222, bot_ruim)   # preferido, mas falha
    notify.remember_bot(999, bot_bom)    # outro bot conhecido
    with _patch_partner(222):
        ok = await notify.notify_partner(111, bot_ruim, "oi")
    assert ok is True
    assert bot_bom.sent == [(222, "oi")]
