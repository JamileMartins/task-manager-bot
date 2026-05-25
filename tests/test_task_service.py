"""Testes unitários de task_service sem dependência do Telegram."""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from src.db.models import Config, Task, TaskList, User
from src.services import task_service


# ---------------------------------------------------------------------------
# Patch do get_session para usar o banco de teste
# ---------------------------------------------------------------------------

@contextmanager
def _test_session(session):
    """Context manager que usa a sessão de teste sem fechar."""
    try:
        yield session
        session.flush()
    except Exception:
        session.rollback()
        raise


def make_patch(session):
    """Retorna patch que substitui get_session pela sessão de teste."""
    return patch("src.services.task_service.get_session", return_value=_test_session(session))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_user(session, chat_id: int = 12345) -> User:
    user = User(
        telegram_chat_id=chat_id,
        name="Jamile",
        timezone="America/Fortaleza",
        created_at=datetime.now(timezone.utc),
    )
    session.add(user)
    session.flush()
    return user


# ---------------------------------------------------------------------------
# Slugify
# ---------------------------------------------------------------------------

def test_slugify_basic():
    assert task_service._slugify("Trabalho") == "trabalho"


def test_slugify_com_acento():
    assert task_service._slugify("Saúde") == "saude"


def test_slugify_com_parenteses():
    assert task_service._slugify("Casa (solo)") == "casa-solo"
    assert task_service._slugify("Casa (casal)") == "casa-casal"


# ---------------------------------------------------------------------------
# Criação de listas iniciais
# ---------------------------------------------------------------------------

def test_create_initial_lists_quantidade(db_session):
    user = _create_user(db_session)
    task_service._create_initial_lists(db_session, user)
    db_session.flush()

    listas = db_session.scalars(select(TaskList).where(TaskList.user_id == user.id)).all()
    assert len(listas) == 6  # Trabalho, Projetos, Casa solo, Casa casal, Saúde, Ideias


def test_create_initial_lists_nomes(db_session):
    user = _create_user(db_session)
    task_service._create_initial_lists(db_session, user)
    db_session.flush()

    nomes = {
        lst.name
        for lst in db_session.scalars(select(TaskList).where(TaskList.user_id == user.id)).all()
    }
    assert "Trabalho" in nomes
    assert "Projetos" in nomes
    assert "Casa (casal)" in nomes


def test_create_initial_lists_casal_marcada(db_session):
    user = _create_user(db_session)
    task_service._create_initial_lists(db_session, user)
    db_session.flush()

    casal = db_session.scalar(
        select(TaskList).where(TaskList.user_id == user.id, TaskList.slug == "casa-casal")
    )
    assert casal is not None
    assert casal.is_couple is True


def test_create_initial_lists_cria_config(db_session):
    user = _create_user(db_session)
    task_service._create_initial_lists(db_session, user)
    db_session.flush()

    cfg = db_session.get(Config, user.id)
    assert cfg is not None
    assert cfg.stale_days == 7
    assert cfg.stale_waiting_days == 14


# ---------------------------------------------------------------------------
# Criação de tarefa na Inbox
# ---------------------------------------------------------------------------

def test_create_task_in_inbox(db_session):
    user = _create_user(db_session)
    task_service._create_initial_lists(db_session, user)

    with patch("src.services.task_service.get_session") as mock_gs:
        mock_gs.return_value = _test_session(db_session)
        task = task_service.create_task_in_inbox(user.telegram_chat_id, "Ligar pro dentista")

    assert task.title == "Ligar pro dentista"
    assert task.list_id is None  # Inbox
    assert task.status == "aberta"


def test_create_task_gera_usuario_na_primeira_vez(db_session):
    chat_id = 99999
    with patch("src.services.task_service.get_session") as mock_gs:
        mock_gs.return_value = _test_session(db_session)
        task = task_service.create_task_in_inbox(chat_id, "Primeira tarefa", "Novo Usuário")

    assert task.title == "Primeira tarefa"
    user = db_session.scalar(select(User).where(User.telegram_chat_id == chat_id))
    assert user is not None
    assert user.name == "Novo Usuário"


# ---------------------------------------------------------------------------
# Conclusão de tarefa
# ---------------------------------------------------------------------------

def test_complete_task_muda_status(db_session):
    user = _create_user(db_session)
    now = datetime.now(timezone.utc)
    task = Task(
        user_id=user.id,
        title="Tarefa teste",
        status="aberta",
        sort_order=0,
        created_at=now,
        last_touched_at=now,
    )
    db_session.add(task)
    db_session.flush()

    with patch("src.services.task_service.get_session") as mock_gs:
        mock_gs.return_value = _test_session(db_session)
        resultado = task_service.complete_task(task.id)

    assert resultado is True
    db_session.refresh(task)
    assert task.status == "concluida"
    assert task.completed_at is not None


def test_complete_task_inexistente_retorna_false(db_session):
    with patch("src.services.task_service.get_session") as mock_gs:
        mock_gs.return_value = _test_session(db_session)
        resultado = task_service.complete_task(uuid.uuid4())

    assert resultado is False


# ---------------------------------------------------------------------------
# Deleção de tarefa (desfazer)
# ---------------------------------------------------------------------------

def test_delete_task(db_session):
    user = _create_user(db_session)
    now = datetime.now(timezone.utc)
    task = Task(
        user_id=user.id,
        title="Tarefa a apagar",
        status="aberta",
        sort_order=0,
        created_at=now,
        last_touched_at=now,
    )
    db_session.add(task)
    db_session.flush()
    task_id = task.id

    with patch("src.services.task_service.get_session") as mock_gs:
        mock_gs.return_value = _test_session(db_session)
        resultado = task_service.delete_task(task_id)

    assert resultado is True
    assert db_session.get(Task, task_id) is None


# ---------------------------------------------------------------------------
# Criar lista
# ---------------------------------------------------------------------------

def test_create_list(db_session):
    user = _create_user(db_session)

    with patch("src.services.task_service.get_session") as mock_gs:
        mock_gs.return_value = _test_session(db_session)
        lst = task_service.create_list(user.telegram_chat_id, "Projetos Pessoais")

    assert lst is not None
    assert lst.name == "Projetos Pessoais"
    assert lst.slug == "projetos-pessoais"


# ---------------------------------------------------------------------------
# get_user_lists
# ---------------------------------------------------------------------------

def test_get_user_lists_retorna_apenas_ativas(db_session):
    user = _create_user(db_session)
    task_service._create_initial_lists(db_session, user)
    db_session.flush()

    # Arquiva uma lista
    casal = db_session.scalar(
        select(TaskList).where(TaskList.user_id == user.id, TaskList.slug == "casa-casal")
    )
    casal.archived = True
    db_session.flush()

    with patch("src.services.task_service.get_session") as mock_gs:
        mock_gs.return_value = _test_session(db_session)
        listas = task_service.get_user_lists(user.telegram_chat_id)

    slugs = [l.slug for l in listas]
    assert "casa-casal" not in slugs
    assert len(listas) == 5
