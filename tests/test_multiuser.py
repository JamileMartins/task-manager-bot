"""Testes da Fase C1 — multiusuário (allowlist, autorização, jobs por usuário)."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.config import _parse_chat_ids
from src.db.models import User
from src.handlers import common
from src.services import task_service


# ---------------------------------------------------------------------------
# config._parse_chat_ids
# ---------------------------------------------------------------------------

def test_parse_chat_ids_vazio():
    assert _parse_chat_ids("") == set()


def test_parse_chat_ids_csv_com_espacos():
    assert _parse_chat_ids(" 123 , 456 ,789 ") == {123, 456, 789}


def test_parse_chat_ids_ignora_partes_vazias():
    assert _parse_chat_ids("123,,456,") == {123, 456}


# ---------------------------------------------------------------------------
# is_authorized — allowlist
# ---------------------------------------------------------------------------

def _update(chat_id: int | None):
    chat = SimpleNamespace(id=chat_id) if chat_id is not None else None
    return SimpleNamespace(effective_chat=chat)


def test_is_authorized_aceita_id_na_allowlist():
    with patch.object(common, "ALLOWED_CHAT_IDS", {111, 222}):
        assert common.is_authorized(_update(111)) is True
        assert common.is_authorized(_update(222)) is True


def test_is_authorized_rejeita_id_fora_da_allowlist():
    with patch.object(common, "ALLOWED_CHAT_IDS", {111, 222}):
        assert common.is_authorized(_update(999)) is False


def test_is_authorized_rejeita_sem_chat():
    with patch.object(common, "ALLOWED_CHAT_IDS", {111}):
        assert common.is_authorized(_update(None)) is False


# ---------------------------------------------------------------------------
# get_all_user_chat_ids
# ---------------------------------------------------------------------------

@contextmanager
def _test_session(session):
    try:
        yield session
        session.flush()
    except Exception:
        session.rollback()
        raise


@pytest.fixture
def svc(db_session):
    with patch(
        "src.services.task_service.get_session",
        side_effect=lambda: _test_session(db_session),
    ):
        yield db_session


def _user(session, chat_id: int, name: str = "U") -> User:
    user = User(
        telegram_chat_id=chat_id,
        name=name,
        timezone="America/Fortaleza",
        created_at=datetime.now(timezone.utc),
    )
    session.add(user)
    session.flush()
    return user


def test_get_all_user_chat_ids_vazio(svc):
    assert task_service.get_all_user_chat_ids() == []


def test_get_all_user_chat_ids_retorna_todos(svc):
    _user(svc, 111, "A")
    _user(svc, 222, "B")
    ids = set(task_service.get_all_user_chat_ids())
    assert ids == {111, 222}
