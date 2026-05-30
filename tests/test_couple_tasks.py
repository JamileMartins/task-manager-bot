"""Testes da Fase C3 — tarefas compartilhadas e privacidade (filtro de visibilidade).

O foco principal é o RNF-01: tarefa pessoal nunca pode cruzar para o parceiro.
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.db.models import Couple, CoupleMember, Task, User
from src.services import task_service
from src.utils import keyboards


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


def _user(session, chat_id: int, name: str) -> User:
    u = User(telegram_chat_id=chat_id, name=name, timezone="America/Fortaleza",
             created_at=datetime.now(timezone.utc))
    session.add(u)
    session.flush()
    return u


def _couple(session, *users) -> Couple:
    now = datetime.now(timezone.utc)
    couple = Couple(created_at=now)
    session.add(couple)
    session.flush()
    for u in users:
        session.add(CoupleMember(couple_id=couple.id, user_id=u.id, role="member", joined_at=now))
    session.flush()
    return couple


def _personal(session, user, title) -> Task:
    now = datetime.now(timezone.utc)
    t = Task(user_id=user.id, list_id=None, title=title, status="aberta",
             sort_order=0, created_at=now, last_touched_at=now)
    session.add(t)
    session.flush()
    return t


def _couple_task(session, user, couple, title) -> Task:
    now = datetime.now(timezone.utc)
    t = Task(user_id=user.id, couple_id=couple.id, created_by=user.id, list_id=None,
             title=title, status="aberta", sort_order=0, created_at=now, last_touched_at=now)
    session.add(t)
    session.flush()
    return t


# ---------------------------------------------------------------------------
# PRIVACIDADE (RNF-01) — o teste mais importante da fase
# ---------------------------------------------------------------------------

def test_pessoal_nao_vaza_entre_nao_pareados(svc):
    """Sem casal: A jamais vê tarefa pessoal de B (guarda o gotcha do IS NULL)."""
    a = _user(svc, 111, "Ana")
    b = _user(svc, 222, "Beto")
    _personal(svc, b, "segredo do Beto")

    assert task_service.search_tasks(111, "segredo") == []
    # E B continua vendo o próprio.
    assert [t.title for t in task_service.search_tasks(222, "segredo")] == ["segredo do Beto"]


def test_pessoal_nao_vaza_entre_pareados(svc):
    """Com casal: a tarefa PESSOAL de um membro não aparece para o outro."""
    a = _user(svc, 111, "Ana")
    b = _user(svc, 222, "Beto")
    _couple(svc, a, b)
    _personal(svc, b, "diario do Beto")

    assert task_service.search_tasks(111, "diario") == []


def test_tarefa_casal_visivel_para_ambos(svc):
    a = _user(svc, 111, "Ana")
    b = _user(svc, 222, "Beto")
    couple = _couple(svc, a, b)
    _couple_task(svc, a, couple, "comprar presente")

    assert [t.title for t in task_service.search_tasks(111, "presente")] == ["comprar presente"]
    assert [t.title for t in task_service.search_tasks(222, "presente")] == ["comprar presente"]


# ---------------------------------------------------------------------------
# Inbox exclui tarefas de casal
# ---------------------------------------------------------------------------

def test_inbox_exclui_tarefas_de_casal(svc):
    a = _user(svc, 111, "Ana")
    couple = _couple(svc, a)
    _personal(svc, a, "pessoal na inbox")
    _couple_task(svc, a, couple, "casal sem lista")

    inbox = task_service.get_inbox_tasks(111)
    assert [t.title for t in inbox] == ["pessoal na inbox"]
    assert task_service.get_inbox_count(111) == 1


# ---------------------------------------------------------------------------
# set_task_couple — converter pessoal <-> casal
# ---------------------------------------------------------------------------

def test_set_task_couple_torna_compartilhada(svc):
    a = _user(svc, 111, "Ana")
    b = _user(svc, 222, "Beto")
    couple = _couple(svc, a, b)
    t = _personal(svc, a, "tarefa que vira do casal")

    updated = task_service.set_task_couple(t.id, 111, make_couple=True)
    assert updated is not None
    assert updated.couple_id == couple.id
    assert updated.list_id is None
    # Agora o parceiro enxerga.
    assert "tarefa que vira do casal" in {x.title for x in task_service.get_couple_tasks(222)}


def test_set_task_couple_volta_a_ser_pessoal(svc):
    a = _user(svc, 111, "Ana")
    couple = _couple(svc, a)
    t = _couple_task(svc, a, couple, "volta a ser pessoal")

    updated = task_service.set_task_couple(t.id, 111, make_couple=False)
    assert updated.couple_id is None
    assert task_service.get_couple_tasks(111) == []


def test_set_task_couple_sem_casal_retorna_none(svc):
    a = _user(svc, 111, "Ana")
    t = _personal(svc, a, "sem casal")
    assert task_service.set_task_couple(t.id, 111, make_couple=True) is None


# ---------------------------------------------------------------------------
# save_classified_tasks com destino casal
# ---------------------------------------------------------------------------

def test_save_classified_destino_casal(svc):
    a = _user(svc, 111, "Ana")
    couple = _couple(svc, a)
    saved = task_service.save_classified_tasks(
        111, [{"titulo": "tarefa do casal", "casal": True}], "Ana"
    )
    assert saved[0].couple_id == couple.id
    assert saved[0].list_id is None
    assert saved[0].created_by == a.id


def test_save_classified_casal_ignorado_sem_par(svc):
    """Marcar casal sem estar pareado não deve setar couple_id (vira pessoal)."""
    _user(svc, 111, "Ana")
    saved = task_service.save_classified_tasks(
        111, [{"titulo": "sem par", "casal": True}], "Ana"
    )
    assert saved[0].couple_id is None


def test_has_couple(svc):
    a = _user(svc, 111, "Ana")
    assert task_service.has_couple(111) is False
    _couple(svc, a)
    assert task_service.has_couple(111) is True


# ---------------------------------------------------------------------------
# C5 — assign_couple_task (de quem é a vez)
# ---------------------------------------------------------------------------

def test_assign_para_mim(svc):
    a = _user(svc, 111, "Ana")
    b = _user(svc, 222, "Beto")
    couple = _couple(svc, a, b)
    t = _couple_task(svc, a, couple, "tarefa")
    updated = task_service.assign_couple_task(t.id, 111, "me")
    assert updated.assigned_to == a.id


def test_assign_para_o_par(svc):
    a = _user(svc, 111, "Ana")
    b = _user(svc, 222, "Beto")
    couple = _couple(svc, a, b)
    t = _couple_task(svc, a, couple, "tarefa")
    updated = task_service.assign_couple_task(t.id, 111, "partner")
    assert updated.assigned_to == b.id


def test_assign_none_limpa(svc):
    a = _user(svc, 111, "Ana")
    couple = _couple(svc, a)
    t = _couple_task(svc, a, couple, "tarefa")
    t.assigned_to = a.id
    svc.flush()
    updated = task_service.assign_couple_task(t.id, 111, "none")
    assert updated.assigned_to is None


def test_assign_em_tarefa_pessoal_retorna_none(svc):
    a = _user(svc, 111, "Ana")
    t = _personal(svc, a, "pessoal")
    assert task_service.assign_couple_task(t.id, 111, "me") is None


# ---------------------------------------------------------------------------
# Teclado do detalhe — botão pessoal <-> casal
# ---------------------------------------------------------------------------

def _kb_texts(kb):
    return [b.text for row in kb.inline_keyboard for b in row]


def test_kb_detail_mostra_tornar_do_casal_quando_pareado():
    t = Task(id=uuid.uuid4(), title="x", status="aberta", couple_id=None, list_id=None)
    texts = _kb_texts(keyboards.kb_task_detail(t, [], None, show_couple=True))
    assert any("Tornar do casal" in x for x in texts)


def test_kb_detail_oculta_botao_casal_quando_nao_pareado():
    t = Task(id=uuid.uuid4(), title="x", status="aberta", couple_id=None, list_id=None)
    texts = _kb_texts(keyboards.kb_task_detail(t, [], None, show_couple=False))
    assert not any("casal" in x.lower() for x in texts)


def test_kb_detail_mostra_tornar_pessoal_em_tarefa_do_casal():
    t = Task(id=uuid.uuid4(), title="x", status="aberta", couple_id=uuid.uuid4(), list_id=None)
    texts = _kb_texts(keyboards.kb_task_detail(t, [], None, show_couple=True))
    assert any("Tornar pessoal" in x for x in texts)
