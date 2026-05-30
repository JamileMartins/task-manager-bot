"""Testes do pareamento de casal (Fase C2) — sem dependência do Telegram."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.db.models import CoupleMember, Invite, User
from src.services import couple_service


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
        "src.services.couple_service.get_session",
        side_effect=lambda: _test_session(db_session),
    ):
        yield db_session


def _user(session, chat_id: int, name: str) -> User:
    user = User(
        telegram_chat_id=chat_id,
        name=name,
        timezone="America/Fortaleza",
        created_at=datetime.now(timezone.utc),
    )
    session.add(user)
    session.flush()
    return user


# ---------------------------------------------------------------------------
# create_invite
# ---------------------------------------------------------------------------

def test_create_invite_gera_codigo_e_casal(svc):
    _user(svc, 111, "Ana")
    result = couple_service.create_invite(111)
    assert result.status == "ok"
    assert result.code and len(result.code) == 6
    # Criou casal de 1 membro e o convite.
    assert svc.query(CoupleMember).count() == 1
    assert svc.get(Invite, result.code) is not None


def test_create_invite_sem_usuario(svc):
    result = couple_service.create_invite(999)
    assert result.status == "no_user"


def test_create_invite_reaproveita_casal_de_um_membro(svc):
    _user(svc, 111, "Ana")
    r1 = couple_service.create_invite(111)
    r2 = couple_service.create_invite(111)
    assert r1.status == r2.status == "ok"
    assert r1.code != r2.code
    # Continua sendo um único casal (1 membro), dois convites.
    assert svc.query(CoupleMember).count() == 1
    assert svc.query(Invite).count() == 2


def test_create_invite_ja_pareado(svc):
    _user(svc, 111, "Ana")
    _user(svc, 222, "Beto")
    code = couple_service.create_invite(111).code
    couple_service.accept_invite(222, code)
    # Ana já está num casal completo → não pode convidar.
    assert couple_service.create_invite(111).status == "already_paired"


# ---------------------------------------------------------------------------
# accept_invite — fluxo feliz
# ---------------------------------------------------------------------------

def test_accept_invite_vincula_os_dois(svc):
    _user(svc, 111, "Ana")
    _user(svc, 222, "Beto")
    code = couple_service.create_invite(111).code

    result = couple_service.accept_invite(222, code)
    assert result.status == "ok"
    assert result.partner_name == "Ana"
    assert svc.query(CoupleMember).count() == 2

    # get_partner resolve dos dois lados.
    assert couple_service.get_partner(111)["chat_id"] == 222
    assert couple_service.get_partner(111)["name"] == "Beto"
    assert couple_service.get_partner(222)["chat_id"] == 111
    assert couple_service.partner_chat_id(222) == 111


def test_accept_invite_normaliza_codigo(svc):
    _user(svc, 111, "Ana")
    _user(svc, 222, "Beto")
    code = couple_service.create_invite(111).code
    # minúsculas + espaços devem ser aceitos.
    assert couple_service.accept_invite(222, f"  {code.lower()} ").status == "ok"


# ---------------------------------------------------------------------------
# accept_invite — erros
# ---------------------------------------------------------------------------

def test_accept_invite_codigo_invalido(svc):
    _user(svc, 222, "Beto")
    assert couple_service.accept_invite(222, "ZZZZZZ").status == "invalid"


def test_accept_invite_proprio_codigo(svc):
    _user(svc, 111, "Ana")
    code = couple_service.create_invite(111).code
    assert couple_service.accept_invite(111, code).status == "own_invite"


def test_accept_invite_usado(svc):
    _user(svc, 111, "Ana")
    _user(svc, 222, "Beto")
    _user(svc, 333, "Cau")
    code = couple_service.create_invite(111).code
    couple_service.accept_invite(222, code)
    # Terceiro tentando o mesmo código → já usado.
    assert couple_service.accept_invite(333, code).status == "used"


def test_accept_invite_expirado(svc):
    _user(svc, 111, "Ana")
    _user(svc, 222, "Beto")
    code = couple_service.create_invite(111).code
    inv = svc.get(Invite, code)
    inv.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    svc.flush()
    assert couple_service.accept_invite(222, code).status == "expired"


def test_accept_invite_ja_pareado(svc):
    _user(svc, 111, "Ana")
    _user(svc, 222, "Beto")
    _user(svc, 333, "Cau")
    code1 = couple_service.create_invite(111).code
    couple_service.accept_invite(222, code1)
    # Beto já está num casal e tenta entrar noutro convite (de Cau).
    code2 = couple_service.create_invite(333).code
    assert couple_service.accept_invite(222, code2).status == "already_paired"


# ---------------------------------------------------------------------------
# consultas
# ---------------------------------------------------------------------------

def test_get_couple_id_e_partner_sem_casal(svc):
    _user(svc, 111, "Ana")
    assert couple_service.get_couple_id(111) is None
    assert couple_service.get_partner(111) is None
    assert couple_service.partner_chat_id(111) is None


def test_get_partner_casal_de_um_membro_e_none(svc):
    _user(svc, 111, "Ana")
    couple_service.create_invite(111)
    # Casal existe mas só tem 1 membro → sem parceiro ainda.
    assert couple_service.get_couple_id(111) is not None
    assert couple_service.get_partner(111) is None


def test_member_names_retorna_os_dois(svc):
    a = _user(svc, 111, "Ana")
    b = _user(svc, 222, "Beto")
    code = couple_service.create_invite(111).code
    couple_service.accept_invite(222, code)
    names = couple_service.member_names(111)
    assert names == {a.id: "Ana", b.id: "Beto"}


def test_member_names_sem_casal_vazio(svc):
    _user(svc, 111, "Ana")
    assert couple_service.member_names(111) == {}
