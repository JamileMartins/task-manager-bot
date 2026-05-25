"""Lógica de domínio do bot Foco — sem dependência do Telegram."""
from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models import Config, Task, TaskList, User
from src.db.session import get_session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")


_INITIAL_LISTS = [
    ("Trabalho", False),
    ("Projetos", False),
    ("Casa (solo)", False),
    ("Casa (casal)", True),
    ("Saúde", False),
    ("Ideias", False),
]


# ---------------------------------------------------------------------------
# Usuário
# ---------------------------------------------------------------------------

def _create_initial_lists(session: Session, user: User) -> None:
    for i, (name, is_couple) in enumerate(_INITIAL_LISTS):
        lst = TaskList(
            user_id=user.id,
            name=name,
            slug=_slugify(name),
            is_couple=is_couple,
            sort_order=i,
        )
        session.add(lst)

    cfg = Config(
        user_id=user.id,
        stale_days=7,
        stale_waiting_days=14,
    )
    session.add(cfg)


def get_or_create_user(chat_id: int, name: str = "Jamile") -> User:
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            user = User(
                telegram_chat_id=chat_id,
                name=name,
                timezone="America/Fortaleza",
                created_at=_now(),
            )
            session.add(user)
            session.flush()
            _create_initial_lists(session, user)
        return user


# ---------------------------------------------------------------------------
# Tarefas — captura
# ---------------------------------------------------------------------------

def create_task_in_inbox(chat_id: int, title: str, user_name: str = "Jamile") -> Task:
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            user = User(
                telegram_chat_id=chat_id,
                name=user_name,
                timezone="America/Fortaleza",
                created_at=_now(),
            )
            session.add(user)
            session.flush()
            _create_initial_lists(session, user)

        now = _now()
        task = Task(
            user_id=user.id,
            list_id=None,
            title=title,
            status="aberta",
            sort_order=0,
            created_at=now,
            last_touched_at=now,
        )
        session.add(task)
        session.flush()
        return task


def delete_task(task_id: str | uuid.UUID) -> bool:
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        task = session.get(Task, uid)
        if task is None:
            return False
        session.delete(task)
        return True


# ---------------------------------------------------------------------------
# Tarefas — conclusão
# ---------------------------------------------------------------------------

def complete_task(task_id: str | uuid.UUID) -> bool:
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        task = session.get(Task, uid)
        if task is None or task.status == "concluida":
            return False
        now = _now()
        task.status = "concluida"
        task.completed_at = now
        task.last_touched_at = now
        return True


# ---------------------------------------------------------------------------
# Listas
# ---------------------------------------------------------------------------

@dataclass
class ListInfo:
    id: uuid.UUID
    name: str
    slug: str
    is_couple: bool
    open_task_count: int


def get_user_lists(chat_id: int) -> list[ListInfo]:
    """Retorna listas ativas com contagem de tarefas abertas."""
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return []

        rows = session.execute(
            select(
                TaskList.id,
                TaskList.name,
                TaskList.slug,
                TaskList.is_couple,
                func.count(Task.id).label("open_count"),
            )
            .outerjoin(
                Task,
                (Task.list_id == TaskList.id) & (Task.status == "aberta"),
            )
            .where(TaskList.user_id == user.id, TaskList.archived.is_(False))
            .group_by(TaskList.id, TaskList.name, TaskList.slug, TaskList.is_couple, TaskList.sort_order)
            .order_by(TaskList.sort_order)
        ).all()

        return [
            ListInfo(id=r.id, name=r.name, slug=r.slug, is_couple=r.is_couple, open_task_count=r.open_count)
            for r in rows
        ]


def get_inbox_count(chat_id: int) -> int:
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return 0
        return session.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user.id,
                Task.list_id.is_(None),
                Task.status == "aberta",
            )
        ) or 0


def get_tasks_for_list(list_id: uuid.UUID) -> list[Task]:
    with get_session() as session:
        return session.scalars(
            select(Task)
            .where(Task.list_id == list_id, Task.status == "aberta")
            .order_by(Task.quadrant.nullslast(), Task.sort_order)
        ).all()


def get_inbox_tasks(chat_id: int) -> list[Task]:
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return []
        return session.scalars(
            select(Task)
            .where(Task.user_id == user.id, Task.list_id.is_(None), Task.status == "aberta")
            .order_by(Task.created_at)
        ).all()


def create_list(chat_id: int, name: str) -> Optional[TaskList]:
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return None
        max_order = session.scalar(
            select(func.max(TaskList.sort_order)).where(TaskList.user_id == user.id)
        ) or 0
        lst = TaskList(
            user_id=user.id,
            name=name.strip(),
            slug=_slugify(name),
            sort_order=max_order + 1,
        )
        session.add(lst)
        session.flush()
        return lst


def rename_list(list_id: uuid.UUID, new_name: str) -> Optional[TaskList]:
    with get_session() as session:
        lst = session.get(TaskList, list_id)
        if lst is None:
            return None
        lst.name = new_name.strip()
        lst.slug = _slugify(new_name)
        return lst


def archive_list(list_id: uuid.UUID) -> Optional[str]:
    """Arquiva a lista. Retorna o nome se bem-sucedido, None se não encontrada."""
    with get_session() as session:
        lst = session.get(TaskList, list_id)
        if lst is None:
            return None
        lst.archived = True
        return lst.name
