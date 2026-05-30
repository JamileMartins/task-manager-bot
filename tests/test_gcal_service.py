"""Testes do motor de sincronização com Google Calendar (Fase C6).

Cobrem a lógica pura (mapeamento tarefa↔evento, escolha de calendário,
idempotência) com um cliente fake, e o no-op quando o Google está desativado.
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.db.models import Couple, Task, User
from src.services import gcal_service


class FakeClient:
    def __init__(self):
        self.upserts: list = []
        self.deletes: list = []
        self._n = 0

    def upsert_event(self, calendar_id, event_id, summary, start, end):
        self.upserts.append((calendar_id, event_id, summary, start, end))
        if event_id:
            return event_id
        self._n += 1
        return f"evt{self._n}"

    def delete_event(self, calendar_id, event_id):
        self.deletes.append((calendar_id, event_id))


def _task(**kw) -> Task:
    base = dict(
        id=uuid.uuid4(), title="Tarefa", status="aberta",
        due_at=datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc),
        estimate_min=None, gcal_event_id=None, couple_id=None,
    )
    base.update(kw)
    return Task(**base)


# ---------------------------------------------------------------------------
# sync_task — criação / atualização / remoção
# ---------------------------------------------------------------------------

def test_cria_evento_para_tarefa_aberta_com_prazo():
    c = FakeClient()
    t = _task()
    event_id = gcal_service.sync_task(t, c, "cal1")
    assert event_id == "evt1"
    assert len(c.upserts) == 1
    cal, eid, summary, start, end = c.upserts[0]
    assert cal == "cal1" and eid is None and summary == "Tarefa"
    # Duração padrão de 30 min sem estimativa.
    assert end - start == timedelta(minutes=gcal_service.DEFAULT_EVENT_MIN)


def test_usa_estimativa_como_duracao():
    c = FakeClient()
    t = _task(estimate_min=90)
    gcal_service.sync_task(t, c, "cal1")
    _, _, _, start, end = c.upserts[0]
    assert end - start == timedelta(minutes=90)


def test_atualiza_evento_existente_idempotente():
    c = FakeClient()
    t = _task(gcal_event_id="evtX")
    event_id = gcal_service.sync_task(t, c, "cal1")
    assert event_id == "evtX"  # mantém o mesmo id
    assert c.upserts[0][1] == "evtX"


def test_apaga_evento_quando_concluida():
    c = FakeClient()
    t = _task(status="concluida", gcal_event_id="evtX")
    event_id = gcal_service.sync_task(t, c, "cal1")
    assert event_id is None
    assert c.deletes == [("cal1", "evtX")]


def test_apaga_evento_quando_perde_prazo():
    c = FakeClient()
    t = _task(due_at=None, gcal_event_id="evtX")
    assert gcal_service.sync_task(t, c, "cal1") is None
    assert c.deletes == [("cal1", "evtX")]


def test_sem_calendario_nao_faz_nada():
    c = FakeClient()
    t = _task()
    assert gcal_service.sync_task(t, c, None) is None
    assert c.upserts == [] and c.deletes == []


# ---------------------------------------------------------------------------
# target_calendar_id — escolha do calendário
# ---------------------------------------------------------------------------

def _user(cal="meu_cal"):
    return User(telegram_chat_id=1, name="A", timezone="America/Fortaleza",
                created_at=datetime.now(timezone.utc), google_calendar_id=cal)


def test_calendario_pessoal_para_tarefa_pessoal():
    t = _task(couple_id=None)
    assert gcal_service.target_calendar_id(t, _user("pessoal"), None) == "pessoal"


def test_calendario_do_casal_para_tarefa_de_casal():
    cid = uuid.uuid4()
    t = _task(couple_id=cid)
    couple = Couple(id=cid, created_at=datetime.now(timezone.utc), gcal_calendar_id="cal_casal")
    assert gcal_service.target_calendar_id(t, _user("pessoal"), couple) == "cal_casal"


def test_tarefa_de_casal_sem_calendario_compartilhado_usa_pessoal():
    cid = uuid.uuid4()
    t = _task(couple_id=cid)
    couple = Couple(id=cid, created_at=datetime.now(timezone.utc), gcal_calendar_id=None)
    assert gcal_service.target_calendar_id(t, _user("pessoal"), couple) == "pessoal"


# ---------------------------------------------------------------------------
# no-op quando o Google está desativado
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
        "src.services.gcal_service.get_session",
        side_effect=lambda: _test_session(db_session),
    ):
        yield db_session


def test_sync_for_user_e_noop_sem_google(svc):
    u = User(telegram_chat_id=111, name="A", timezone="America/Fortaleza",
             created_at=datetime.now(timezone.utc))
    svc.add(u)
    svc.flush()
    t = Task(user_id=u.id, title="x", status="aberta",
             due_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
             sort_order=0, created_at=datetime.now(timezone.utc),
             last_touched_at=datetime.now(timezone.utc))
    svc.add(t)
    svc.flush()
    # Sem refresh token / credenciais → no-op silencioso.
    assert gcal_service.sync_task_for_user(t.id, 111) is None
    assert t.gcal_event_id is None
