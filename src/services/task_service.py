"""Lógica de domínio do bot Foco — sem dependência do Telegram."""
from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from src.db.models import Config, CoupleMember, Reminder, Task, TaskList, User
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


def _couple_id_for(session: Session, user_id) -> Optional[uuid.UUID]:
    """Retorna o couple_id do usuário, ou None se não estiver pareado."""
    return session.scalar(
        select(CoupleMember.couple_id).where(CoupleMember.user_id == user_id)
    )


def _visible_filter(user_id, couple_id):
    """Filtro de visibilidade de tarefas: pessoais do usuário + tarefas do casal.

    IMPORTANTE (privacidade): quando couple_id é None (usuário sem casal),
    restringe ao próprio user_id. Nunca comparar couple_id com None aqui —
    no SQLAlchemy `== None` vira `IS NULL` e vazaria tarefas pessoais alheias.
    """
    if couple_id is None:
        return Task.user_id == user_id
    return or_(Task.user_id == user_id, Task.couple_id == couple_id)


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


def get_all_user_chat_ids() -> list[int]:
    """Retorna o telegram_chat_id de todos os usuários registrados (para agendar jobs)."""
    with get_session() as session:
        return list(session.scalars(select(User.telegram_chat_id)).all())


def get_or_create_user(chat_id: int, name: str = "usuária") -> User:
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

def create_task_in_inbox(chat_id: int, title: str, user_name: str = "usuária") -> Task:
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


def create_task_in_list(chat_id: int, list_id: uuid.UUID, title: str) -> Task:
    """Cria tarefa diretamente em uma lista, sem passar pela IA (US-30)."""
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            raise ValueError("Usuário não encontrado")
        now = _now()
        task = Task(
            user_id=user.id,
            list_id=list_id,
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

_RECURRENCE_DELTA: dict[str, timedelta] = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "monthly": timedelta(days=30),
}


def _recurrence_delta(recurrence: str) -> timedelta | None:
    if recurrence in _RECURRENCE_DELTA:
        return _RECURRENCE_DELTA[recurrence]
    if recurrence.startswith("weekly:"):
        return timedelta(weeks=1)
    return None


def _recurrence_next_due(recurrence: str, base: datetime) -> datetime | None:
    """Próxima data de ocorrência ancorando weekly:N no dia da semana correto."""
    if recurrence in _RECURRENCE_DELTA:
        return base + _RECURRENCE_DELTA[recurrence]
    if recurrence.startswith("weekly:"):
        try:
            target_dow = int(recurrence.split(":")[1])
            days_ahead = (target_dow - base.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # mesmo dia → próxima semana
            return base + timedelta(days=days_ahead)
        except (ValueError, IndexError):
            return base + timedelta(weeks=1)
    return None


def _apply_med_time(dt: datetime, notes: str | None) -> datetime:
    """Aplica HH:MM de notes no fuso America/Fortaleza, preservando a data local correta."""
    if not notes:
        return dt
    parts = notes.strip().split(":")
    if len(parts) != 2 or len(parts[1]) != 2:
        return dt
    try:
        h, m = int(parts[0]), int(parts[1])
        if 0 <= h <= 23 and 0 <= m <= 59:
            tz = ZoneInfo("America/Fortaleza")
            local = dt.astimezone(tz) if dt.tzinfo else dt
            return local.replace(hour=h, minute=m, second=0, microsecond=0)
    except (ValueError, AttributeError):
        pass
    return dt


def _med_due_for_date(task: Task, day_start: datetime) -> datetime:
    """Retorna o due_at correto para a medicação em determinado dia, usando o horário em notes."""
    return _apply_med_time(day_start, task.notes)


def complete_task(task_id: str | uuid.UUID) -> list[str]:
    """Conclui a tarefa e auto-desbloqueia dependentes.

    Retorna lista de títulos das tarefas que foram desbloqueadas automaticamente.
    Retorna lista vazia se a tarefa não existia ou já estava concluída.
    """
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        task = session.get(Task, uid)
        if task is None or task.status == "concluida":
            return []
        now = _now()
        task.status = "concluida"
        task.completed_at = now
        task.last_touched_at = now

        if task.recurrence:
            base = task.due_at if task.due_at else now
            next_due = _recurrence_next_due(task.recurrence, base)
            if next_due is not None:
                next_due = _apply_med_time(next_due, task.notes)
                next_task = Task(
                    user_id=task.user_id,
                    list_id=task.list_id,
                    title=task.title,
                    notes=task.notes,
                    quadrant=task.quadrant,
                    due_at=next_due,
                    recurrence=task.recurrence,
                    estimate_min=task.estimate_min,
                    energy=task.energy,
                    status="aberta",
                    sort_order=task.sort_order,
                    created_at=now,
                    last_touched_at=now,
                )
                session.add(next_task)
                session.flush()
                _sync_reminder(session, next_task)

        # Auto-desbloquear tarefas que dependiam desta
        dependentes = session.scalars(
            select(Task).where(
                Task.blocked_by_task_id == uid,
                Task.status != "concluida",
            )
        ).all()
        unblocked_titles: list[str] = []
        for dep in dependentes:
            dep.status = "aberta"
            dep.waiting_since = None
            dep.blocker_type = None
            dep.blocker_is_external = None
            dep.blocker_note = None
            dep.blocked_by_task_id = None
            dep.last_touched_at = now
            unblocked_titles.append(dep.title)

        return unblocked_titles


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


@dataclass
class TaskGroup:
    name: str
    slug: Optional[str]
    list_id: Optional[uuid.UUID]
    tasks: list[Task]


@dataclass
class ProjetoInfo:
    name: str
    slug: Optional[str]
    open_count: int
    done_30d: int
    last_touch: Optional[datetime]


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
                Task.couple_id.is_(None),
                Task.status == "aberta",
            )
        ) or 0


def find_list_by_term(chat_id: int, term: str) -> Optional[TaskList]:
    """Busca lista pelo slug (exato) ou nome (contém, sem acento). Retorna a primeira correspondência."""
    slug_term = _slugify(term)
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return None
        lists = list(session.scalars(
            select(TaskList).where(TaskList.user_id == user.id, TaskList.archived.is_(False))
        ).all())
        # Preferência: match exato de slug; depois: slug contém; depois: nome contém (sem acento)
        for lst in lists:
            if lst.slug == slug_term:
                return lst
        for lst in lists:
            if slug_term in (lst.slug or ""):
                return lst
        term_lower = term.lower()
        for lst in lists:
            if term_lower in lst.name.lower():
                return lst
        return None


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
            .where(
                Task.user_id == user.id,
                Task.list_id.is_(None),
                Task.couple_id.is_(None),
                Task.status == "aberta",
            )
            .order_by(Task.created_at)
        ).all()


def get_couple_tasks(chat_id: int) -> list[Task]:
    """Retorna as tarefas abertas/aguardando do casal do usuário (compartilhadas)."""
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return []
        couple_id = _couple_id_for(session, user.id)
        if couple_id is None:
            return []
        return list(session.scalars(
            select(Task)
            .options(selectinload(Task.task_list))
            .where(
                Task.couple_id == couple_id,
                Task.status.in_(["aberta", "aguardando"]),
            )
            .order_by(Task.quadrant.nullslast(), Task.sort_order)
        ).all())


def get_couple_task_count(chat_id: int) -> Optional[int]:
    """Contagem de tarefas abertas/aguardando do casal, ou None se sem casal."""
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return None
        couple_id = _couple_id_for(session, user.id)
        if couple_id is None:
            return None
        return session.scalar(
            select(func.count(Task.id)).where(
                Task.couple_id == couple_id,
                Task.status.in_(["aberta", "aguardando"]),
            )
        ) or 0


def has_couple(chat_id: int) -> bool:
    """True se o usuário está pareado num casal."""
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return False
        return _couple_id_for(session, user.id) is not None


def set_task_couple(task_id: str | uuid.UUID, chat_id: int, make_couple: bool) -> Optional[Task]:
    """Converte uma tarefa entre pessoal e do casal.

    make_couple=True  → vincula ao casal do usuário (sai da lista pessoal).
    make_couple=False → volta a ser pessoal (couple_id=None).
    """
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        task = session.get(Task, uid)
        if user is None or task is None:
            return None
        if make_couple:
            couple_id = _couple_id_for(session, user.id)
            if couple_id is None:
                return None
            task.couple_id = couple_id
            task.list_id = None
            if task.created_by is None:
                task.created_by = user.id
        else:
            task.couple_id = None
        task.last_touched_at = _now()
        return task


def set_task_category(task_id: str | uuid.UUID, category: Optional[str]) -> Optional[Task]:
    """Define (ou remove) a categoria de uma tarefa. Valores válidos: 'medicacao', 'agendamento', None."""
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        task = session.get(Task, uid)
        if task is None:
            return None
        task.category = category
        task.last_touched_at = _now()
        return task


def assign_couple_task(task_id: str | uuid.UUID, chat_id: int, target: str) -> Optional[Task]:
    """Define o modo/dono de uma tarefa de casal.

    target:
      "me"      → individual, de quem chamou;
      "partner" → individual, do outro membro;
      "joint"   → conjunta (precisa dos dois);
      "shared"/"none" → sem dono (qualquer um faz).
    Retorna a Task atualizada, ou None se não for tarefa de casal / inválida.
    """
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        task = session.get(Task, uid)
        if user is None or task is None or task.couple_id is None:
            return None
        if target == "me":
            task.assigned_to = user.id
            task.couple_joint = False
        elif target == "partner":
            task.assigned_to = session.scalar(
                select(CoupleMember.user_id).where(
                    CoupleMember.couple_id == task.couple_id,
                    CoupleMember.user_id != user.id,
                )
            )
            task.couple_joint = False
        elif target == "joint":
            task.assigned_to = None
            task.couple_joint = True
        else:  # "shared"/"none"
            task.assigned_to = None
            task.couple_joint = False
        task.last_touched_at = _now()
        return task


def search_tasks(chat_id: int, term: str) -> list[Task]:
    """Busca tarefas não concluídas/arquivadas por palavra-chave no título ou notas."""
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return []
        couple_id = _couple_id_for(session, user.id)
        pattern = f"%{term}%"
        return list(session.scalars(
            select(Task)
            .options(selectinload(Task.task_list))
            .where(
                _visible_filter(user.id, couple_id),
                Task.status.not_in(["concluida", "arquivada"]),
                or_(Task.title.ilike(pattern), Task.notes.ilike(pattern)),
            )
            .order_by(Task.status, Task.quadrant.nullslast(), Task.sort_order)
            .limit(20)
        ).all())


def get_medicacoes(chat_id: int) -> tuple[list[Task], list[Task], list[Task]]:
    """Retorna (daily_abertas, weekly_abertas, concluidas_hoje) da lista Saúde."""
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return [], [], []
        saude = session.scalar(
            select(TaskList).where(
                TaskList.user_id == user.id,
                TaskList.slug == "saude",
                TaskList.archived.is_(False),
            )
        )
        if saude is None:
            return [], [], []
        tz = ZoneInfo("America/Fortaleza")
        today_start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start.replace(hour=23, minute=59, second=59, microsecond=999999)
        daily = list(session.scalars(
            select(Task)
            .where(
                Task.list_id == saude.id,
                Task.category == "medicacao",
                Task.recurrence == "daily",
                Task.status == "aberta",
                or_(Task.due_at.is_(None), Task.due_at <= today_end),
            )
            .order_by(Task.sort_order, Task.created_at)
        ).all())
        weekly = list(session.scalars(
            select(Task)
            .where(
                Task.list_id == saude.id,
                Task.category == "medicacao",
                Task.recurrence.like("weekly%"),
                Task.status == "aberta",
                Task.due_at >= today_start,
                Task.due_at <= today_end,
            )
            .order_by(Task.sort_order, Task.created_at)
        ).all())
        completed_today = list(session.scalars(
            select(Task)
            .where(
                Task.list_id == saude.id,
                Task.category == "medicacao",
                Task.status == "concluida",
                Task.completed_at >= today_start,
            )
            .order_by(Task.completed_at.desc())
        ).all())
        return daily, weekly, completed_today


def create_medicacao(chat_id: int, title: str, recurrence: str, med_time: str | None = None) -> Task:
    """Cria uma medicação na lista Saúde com recorrência e horário opcional (US-32)."""
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            raise ValueError("Usuário não encontrado")
        saude = session.scalar(
            select(TaskList).where(
                TaskList.user_id == user.id,
                TaskList.slug == "saude",
                TaskList.archived.is_(False),
            )
        )
        if saude is None:
            saude = TaskList(
                user_id=user.id,
                name="Saúde",
                slug="saude",
                is_couple=False,
                sort_order=4,
            )
            session.add(saude)
            session.flush()
        now = _now()
        tz = ZoneInfo(user.timezone or "America/Fortaleza")
        now_local = now.astimezone(tz)
        if recurrence.startswith("weekly:"):
            try:
                target_dow = int(recurrence.split(":")[1])
                days_ahead = (target_dow - now_local.weekday()) % 7
                day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
                first_due = _apply_med_time(day_start + timedelta(days=days_ahead), med_time)
            except (ValueError, IndexError):
                first_due = now
        else:  # daily
            first_due = _apply_med_time(
                now_local.replace(second=0, microsecond=0), med_time
            )
            if med_time and first_due < now_local:
                first_due += timedelta(days=1)
        task = Task(
            user_id=user.id,
            list_id=saude.id,
            title=title,
            notes=med_time,
            recurrence=recurrence,
            due_at=first_due,
            category="medicacao",
            status="aberta",
            sort_order=0,
            created_at=now,
            last_touched_at=now,
        )
        session.add(task)
        session.flush()
        return task


def rollover_medications(chat_id: int) -> None:
    """Ao virar o dia, descarta medicações não tomadas e agenda a próxima ocorrência.

    Garante que o histórico do dia não acumule para o dia seguinte:
    - daily: due_at avança para hoje no horário configurado
    - weekly: due_at avança para a próxima ocorrência do dia da semana
    """
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return
        saude = session.scalar(
            select(TaskList).where(
                TaskList.user_id == user.id,
                TaskList.slug == "saude",
                TaskList.archived.is_(False),
            )
        )
        if saude is None:
            return

        tz = ZoneInfo(user.timezone or "America/Fortaleza")
        now = _now()
        today_start = now.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)

        stale = list(session.scalars(
            select(Task).where(
                Task.list_id == saude.id,
                Task.recurrence.isnot(None),
                Task.status == "aberta",
                Task.due_at.isnot(None),
                Task.due_at < today_start,
            )
        ).all())

        for task in stale:
            if task.recurrence == "daily":
                next_due = _med_due_for_date(task, today_start)
            else:
                next_due = _recurrence_next_due(task.recurrence, today_start)
            if next_due is None:
                continue
            task.due_at = next_due
            task.last_touched_at = now
            _sync_reminder(session, task)


def get_all_open_tasks(chat_id: int) -> list[TaskGroup]:
    """Retorna todas as tarefas abertas/aguardando agrupadas por lista (Inbox primeiro).

    Tarefas recorrentes com due_at no futuro (próxima ocorrência já agendada) são
    omitidas — só aparecem quando chegarem na data delas.
    """
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return []

        tz = ZoneInfo("America/Fortaleza")
        today_end = datetime.now(tz).replace(hour=23, minute=59, second=59, microsecond=999999)

        # Tarefas recorrentes com due_at > hoje ficam ocultas (são ocorrências futuras)
        not_future_recurrence = or_(
            Task.recurrence.is_(None),
            Task.due_at.is_(None),
            Task.due_at <= today_end,
        )

        inbox_tasks = list(session.scalars(
            select(Task)
            .where(
                Task.user_id == user.id,
                Task.list_id.is_(None),
                Task.couple_id.is_(None),
                Task.status.in_(["aberta", "aguardando"]),
                not_future_recurrence,
            )
            .order_by(Task.sort_order, Task.created_at)
        ).all())

        couple_id = _couple_id_for(session, user.id)
        couple_tasks: list[Task] = []
        if couple_id is not None:
            couple_tasks = list(session.scalars(
                select(Task)
                .where(
                    Task.couple_id == couple_id,
                    Task.status.in_(["aberta", "aguardando"]),
                    not_future_recurrence,
                )
                .order_by(Task.quadrant.nullslast(), Task.sort_order)
            ).all())

        lists = list(session.scalars(
            select(TaskList)
            .where(TaskList.user_id == user.id, TaskList.archived.is_(False))
            .order_by(TaskList.sort_order)
        ).all())

        groups: list[TaskGroup] = []
        if inbox_tasks:
            groups.append(TaskGroup(name="Inbox", slug=None, list_id=None, tasks=inbox_tasks))
        if couple_tasks:
            groups.append(TaskGroup(name="Casa (casal)", slug="casal", list_id=None, tasks=couple_tasks))

        for lst in lists:
            tasks = list(session.scalars(
                select(Task)
                .where(
                    Task.list_id == lst.id,
                    Task.status.in_(["aberta", "aguardando"]),
                    not_future_recurrence,
                )
                .order_by(Task.quadrant.nullslast(), Task.sort_order)
            ).all())
            if tasks:
                groups.append(TaskGroup(name=lst.name, slug=lst.slug, list_id=lst.id, tasks=tasks))

        return groups


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


# ---------------------------------------------------------------------------
# Tarefas — salvar classificação da IA (F2)
# ---------------------------------------------------------------------------

def save_classified_tasks(
    chat_id: int,
    tarefas: list[dict],
    user_name: str = "usuária",
) -> list[Task]:
    """Persiste tarefas classificadas pela IA com regras de pós-processamento (spec §7).

    Impedimento externo (pessoa/recurso_info/data_externa) → status 'aguardando'.
    """
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

        lista_map: dict[str, uuid.UUID] = {
            lst.name: lst.id
            for lst in session.scalars(
                select(TaskList).where(
                    TaskList.user_id == user.id,
                    TaskList.archived.is_(False),
                )
            ).all()
        }

        couple_id = _couple_id_for(session, user.id)
        now = _now()
        saved: list[Task] = []

        for t in tarefas:
            # Destino casal: tarefa compartilhada (sem lista pessoal).
            to_couple = bool(t.get("casal")) and couple_id is not None
            list_name = t.get("lista_sugerida")
            list_id = None if to_couple else (lista_map.get(list_name) if list_name else None)

            is_external = bool(t.get("impedimento_externo"))
            status = "aguardando" if is_external else "aberta"

            prazo: Optional[datetime] = None
            if t.get("prazo_sugerido"):
                try:
                    prazo = datetime.fromisoformat(t["prazo_sugerido"])
                except ValueError:
                    pass

            task = Task(
                user_id=user.id,
                list_id=list_id,
                couple_id=couple_id if to_couple else None,
                created_by=user.id if to_couple else None,
                title=(t.get("titulo") or "")[:500],
                status=status,
                quadrant=t.get("quadrante_sugerido"),
                estimate_min=t.get("estimativa_min"),
                energy=t.get("energia"),
                blocker_type=t.get("impedimento"),
                blocker_is_external=is_external if t.get("impedimento") else None,
                next_step=t.get("proximo_passo"),
                due_at=prazo,
                waiting_since=now if is_external else None,
                sort_order=0,
                created_at=now,
                last_touched_at=now,
            )
            session.add(task)
            session.flush()
            saved.append(task)

        return saved


# ---------------------------------------------------------------------------
# Seleção "/agora" (F3 — US-12)
# ---------------------------------------------------------------------------

_ENERGY_LEVEL: dict[str, int] = {"baixa": 1, "media": 2, "alta": 3}


def get_task_with_list(task_id: str | uuid.UUID) -> Optional[Task]:
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        return session.scalar(
            select(Task).options(selectinload(Task.task_list)).where(Task.id == uid)
        )


def get_task_for_agora(
    chat_id: int,
    tempo_min: int,
    energia: str,
    excluir_ids: list[uuid.UUID] | None = None,
) -> Optional[Task]:
    """Retorna a melhor tarefa para o momento (spec §5).

    Filtra por tempo e energia, ordena por quadrante → prazo → sort_order.
    """
    nivel = _ENERGY_LEVEL.get(energia, 2)
    excluir = set(excluir_ids) if excluir_ids else set()

    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return None

        couple_id = _couple_id_for(session, user.id)
        candidates = session.scalars(
            select(Task)
            .options(selectinload(Task.task_list))
            .where(
                _visible_filter(user.id, couple_id),
                Task.status == "aberta",
                or_(Task.estimate_min <= tempo_min, Task.estimate_min.is_(None)),
            )
            .order_by(Task.quadrant.nullslast(), Task.due_at.nullslast(), Task.sort_order)
        ).all()

        for t in candidates:
            if t.id in excluir:
                continue
            if t.energy is None or _ENERGY_LEVEL.get(t.energy, 2) <= nivel:
                return t
        return None


def get_lightest_task(
    chat_id: int,
    excluir_ids: list[uuid.UUID] | None = None,
) -> Optional[Task]:
    """Fallback /agora: retorna a tarefa mais leve disponível."""
    excluir = set(excluir_ids) if excluir_ids else set()
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return None
        tasks = session.scalars(
            select(Task)
            .options(selectinload(Task.task_list))
            .where(Task.user_id == user.id, Task.status == "aberta")
            .order_by(Task.estimate_min.nullslast(), Task.quadrant.nullslast(), Task.sort_order)
        ).all()
        for t in tasks:
            if t.id not in excluir:
                return t
        return None


# ---------------------------------------------------------------------------
# Edição de atributos e ordenação (F3 — US-07, 08, 09, 10, 11)
# ---------------------------------------------------------------------------

def update_task_attrs(task_id: str | uuid.UUID, **kwargs) -> Optional[Task]:
    """Atualiza atributos de tarefa. Campos: quadrant, energy, estimate_min, due_at, list_id, next_step, recurrence."""
    _allowed = {"quadrant", "energy", "estimate_min", "due_at", "list_id", "next_step", "recurrence", "notes", "title"}
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        task = session.get(Task, uid)
        if task is None:
            return None
        for k, v in kwargs.items():
            if k in _allowed:
                setattr(task, k, v)
        task.last_touched_at = _now()
        if "due_at" in kwargs:
            _sync_reminder(session, task)
        return task


# ---------------------------------------------------------------------------
# Impedimentos (F4 — US-23, 25, 28)
# ---------------------------------------------------------------------------

def set_blocker(
    task_id: str | uuid.UUID,
    blocker_type: str,
    *,
    is_external: bool | None = None,
    note: str | None = None,
) -> Optional[Task]:
    """Salva o tipo de impedimento na tarefa, opcionalmente com nota livre."""
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    _external_types = {"pessoa", "recurso_info", "data_externa"}
    if is_external is None:
        is_external = blocker_type in _external_types
    with get_session() as session:
        task = session.get(Task, uid)
        if task is None:
            return None
        task.blocker_type = blocker_type
        task.blocker_is_external = is_external
        if note is not None:
            task.blocker_note = note.strip()[:500]
        task.last_touched_at = _now()
        return task


def set_blocker_note(task_id: str | uuid.UUID, note: str) -> Optional[Task]:
    """Salva ou atualiza a nota livre de um impedimento já registrado."""
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        task = session.get(Task, uid)
        if task is None:
            return None
        task.blocker_note = note.strip()[:500]
        task.last_touched_at = _now()
        return task


def set_blocked_by_task(
    task_id: str | uuid.UUID,
    blocking_task_id: str | uuid.UUID,
) -> Optional[Task]:
    """Vincula task_id como dependente de blocking_task_id e coloca em aguardando."""
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    blk_uid = uuid.UUID(str(blocking_task_id)) if isinstance(blocking_task_id, str) else blocking_task_id
    with get_session() as session:
        task = session.get(Task, uid)
        blocking = session.get(Task, blk_uid)
        if task is None or blocking is None:
            return None
        now = _now()
        task.blocked_by_task_id = blk_uid
        task.blocker_type = "tarefa_bloqueadora"
        task.blocker_is_external = False
        task.status = "aguardando"
        task.waiting_since = now
        task.last_touched_at = now
        return task


def get_tasks_blocked_by(task_id: str | uuid.UUID) -> list[Task]:
    """Retorna todas as tarefas pendentes que dependem de task_id."""
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        return session.scalars(
            select(Task).where(
                Task.blocked_by_task_id == uid,
                Task.status != "concluida",
            )
        ).all()


def get_pending_tasks_for_selection(
    chat_id: int,
    exclude_task_id: str | uuid.UUID,
    limit: int = 40,
) -> list[Task]:
    """Lista tarefas abertas do usuário para seleção como bloqueadora."""
    exc_uid = uuid.UUID(str(exclude_task_id)) if isinstance(exclude_task_id, str) else exclude_task_id
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return []
        return session.scalars(
            select(Task)
            .where(
                Task.user_id == user.id,
                Task.status == "aberta",
                Task.id != exc_uid,
            )
            .order_by(Task.sort_order, Task.created_at)
            .limit(limit)
        ).all()


def set_waiting(task_id: str | uuid.UUID, *, due_at: Optional[datetime] = None) -> Optional[Task]:
    """Coloca a tarefa em status 'aguardando' e registra waiting_since."""
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        task = session.get(Task, uid)
        if task is None:
            return None
        now = _now()
        task.status = "aguardando"
        task.waiting_since = now
        if due_at is not None:
            task.due_at = due_at
        task.last_touched_at = now
        return task


def reset_waiting_since(task_id: str | uuid.UUID) -> Optional[Task]:
    """Reinicia o contador de espera (waiting_since = agora). US-29 CA."""
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        task = session.get(Task, uid)
        if task is None:
            return None
        task.waiting_since = _now()
        task.last_touched_at = _now()
        return task


def unblock_task(task_id: str | uuid.UUID) -> Optional[Task]:
    """Desbloqueia a tarefa: volta para 'aberta' e limpa todos os campos de bloqueio."""
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        task = session.get(Task, uid)
        if task is None:
            return None
        task.status = "aberta"
        task.waiting_since = None
        task.blocker_type = None
        task.blocker_is_external = None
        task.blocker_note = None
        task.blocked_by_task_id = None
        task.last_touched_at = _now()
        return task


def create_subtask(parent_task_id: str | uuid.UUID, title: str) -> Optional[Task]:
    """Cria uma subtarefa vinculada à tarefa-pai, na mesma lista."""
    uid = uuid.UUID(str(parent_task_id)) if isinstance(parent_task_id, str) else parent_task_id
    with get_session() as session:
        parent = session.get(Task, uid)
        if parent is None:
            return None
        now = _now()
        subtask = Task(
            user_id=parent.user_id,
            list_id=parent.list_id,
            parent_task_id=parent.id,
            title=title[:500],
            status="aberta",
            quadrant=parent.quadrant,
            energy="baixa",
            estimate_min=5,
            sort_order=0,
            created_at=now,
            last_touched_at=now,
        )
        session.add(subtask)
        session.flush()
        return subtask


def get_subtasks(task_id: str | uuid.UUID) -> list[Task]:
    """Retorna subtarefas abertas de uma tarefa-pai, em ordem de criação."""
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        return list(session.scalars(
            select(Task)
            .where(
                Task.parent_task_id == uid,
                Task.status == "aberta",
            )
            .order_by(Task.sort_order, Task.created_at)
        ).all())


def create_related_task(
    parent_task_id: str | uuid.UUID,
    title: str,
    *,
    quadrant: Optional[int] = 2,
) -> Optional[Task]:
    """Cria uma tarefa relacionada (ex.: 'Decidir X') na mesma lista da tarefa-pai."""
    uid = uuid.UUID(str(parent_task_id)) if isinstance(parent_task_id, str) else parent_task_id
    with get_session() as session:
        parent = session.get(Task, uid)
        if parent is None:
            return None
        now = _now()
        task = Task(
            user_id=parent.user_id,
            list_id=parent.list_id,
            title=title[:500],
            status="aberta",
            quadrant=quadrant,
            energy="media",
            sort_order=0,
            created_at=now,
            last_touched_at=now,
        )
        session.add(task)
        session.flush()
        return task


# ---------------------------------------------------------------------------
# Config (US-20)
# ---------------------------------------------------------------------------

def get_config(chat_id: int) -> Optional[Config]:
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return None
        return session.scalar(select(Config).where(Config.user_id == user.id))


def update_config(chat_id: int, **kwargs) -> Optional[Config]:
    _allowed = {
        "daily_summary_time", "weekly_review_dow", "weekly_review_time",
        "couple_group_chat_id", "stale_days", "stale_waiting_days",
        "energia_do_dia", "energia_do_dia_data", "paused_until",
    }
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return None
        cfg = session.scalar(select(Config).where(Config.user_id == user.id))
        if cfg is None:
            cfg = Config(user_id=user.id, stale_days=7, stale_waiting_days=14)
            session.add(cfg)
            session.flush()
        for k, v in kwargs.items():
            if k in _allowed:
                setattr(cfg, k, v)
        return cfg


def set_energia_do_dia(chat_id: int, energia: str) -> None:
    """Salva a energia do dia e a data em que foi definida."""
    from datetime import date as _date
    today = _date.today()
    update_config(chat_id, energia_do_dia=energia, energia_do_dia_data=today)


def get_overdue_unalerted_tasks() -> list[tuple[Task, int]]:
    """Retorna (task, chat_id) para tarefas abertas com prazo vencido ainda não alertadas."""
    now = _now()
    with get_session() as session:
        rows = session.execute(
            select(Task, User.telegram_chat_id)
            .join(User, Task.user_id == User.id)
            .where(
                Task.status == "aberta",
                Task.due_at.is_not(None),
                Task.due_at < now,
                or_(Task.due_alerted.is_(None), Task.due_alerted.is_(False)),
            )
        ).all()
        return [(row[0], row[1]) for row in rows]


def mark_due_alerted(task_id: str | uuid.UUID) -> None:
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        task = session.get(Task, uid)
        if task:
            task.due_alerted = True


# ---------------------------------------------------------------------------
# Rituais — resumo diário e revisão semanal (US-15, US-16)
# ---------------------------------------------------------------------------

def get_daily_summary_tasks(chat_id: int) -> tuple[list[Task], list[Task]]:
    """Retorna (tarefas_com_prazo_hoje, ate_3_focos_Q1Q2)."""
    import pytz
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return [], []

        tz = pytz.timezone(user.timezone or "America/Fortaleza")
        now_local = datetime.now(tz)
        day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = now_local.replace(hour=23, minute=59, second=59, microsecond=999999)

        couple_id = _couple_id_for(session, user.id)

        today_tasks = list(session.scalars(
            select(Task)
            .options(selectinload(Task.task_list))
            .where(
                _visible_filter(user.id, couple_id),
                Task.status == "aberta",
                Task.due_at >= day_start,
                Task.due_at <= day_end,
            )
            .order_by(Task.due_at)
        ).all())

        today_ids = [t.id for t in today_tasks]

        q = (
            select(Task)
            .options(selectinload(Task.task_list))
            .where(
                _visible_filter(user.id, couple_id),
                Task.status == "aberta",
                Task.quadrant.in_([1, 2]),
            )
            .order_by(Task.quadrant, Task.sort_order)
            .limit(3 + len(today_ids))
        )
        focus_raw = session.scalars(q).all()
        focus_tasks = [t for t in focus_raw if t.id not in today_ids][:3]

        return today_tasks, focus_tasks


def get_tomorrow_tasks(chat_id: int) -> list[Task]:
    """Tarefas abertas com prazo amanhã — inclui recorrentes ainda abertas hoje."""
    from sqlalchemy import and_
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return []

        tz = ZoneInfo(user.timezone or "America/Fortaleza")
        now_local = datetime.now(tz)
        tomorrow = now_local + timedelta(days=1)
        tomorrow_dow = tomorrow.weekday()
        day_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
        today_end = now_local.replace(hour=23, minute=59, second=59, microsecond=999999)

        couple_id = _couple_id_for(session, user.id)
        tasks = list(session.scalars(
            select(Task)
            .options(selectinload(Task.task_list))
            .where(
                _visible_filter(user.id, couple_id),
                Task.status == "aberta",
                or_(
                    # Tarefas com due_at explícito amanhã
                    and_(Task.due_at >= day_start, Task.due_at <= day_end),
                    # Diárias abertas com due_at hoje ou antes (ainda não concluídas)
                    and_(Task.recurrence == "daily", Task.due_at.is_not(None),
                         Task.due_at <= today_end),
                    # Semanais com dia da semana = amanhã, ainda abertas hoje ou antes
                    and_(Task.recurrence == f"weekly:{tomorrow_dow}",
                         Task.due_at.is_not(None), Task.due_at <= today_end),
                ),
            )
            .order_by(Task.due_at, Task.quadrant.nullslast(), Task.sort_order)
        ).all())

        # Remove duplicatas (recorrente já com due_at amanhã apareceria nos dois primeiros ramos)
        seen: set[uuid.UUID] = set()
        result = []
        for t in tasks:
            if t.id not in seen:
                seen.add(t.id)
                result.append(t)
        return result


def get_stale_tasks(chat_id: int) -> list[Task]:
    """Tarefas abertas não tocadas há mais de stale_days dias."""
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return []
        cfg = session.scalar(select(Config).where(Config.user_id == user.id))
        stale_days = cfg.stale_days if cfg else 7
        cutoff = _now() - timedelta(days=stale_days)
        return list(session.scalars(
            select(Task)
            .options(selectinload(Task.task_list))
            .where(
                Task.user_id == user.id,
                Task.status == "aberta",
                Task.last_touched_at < cutoff,
            )
            .order_by(Task.last_touched_at)
        ).all())


def get_stale_waiting_tasks(chat_id: int) -> list[Task]:
    """Tarefas em 'aguardando' há mais de stale_waiting_days dias."""
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return []
        cfg = session.scalar(select(Config).where(Config.user_id == user.id))
        stale_waiting_days = cfg.stale_waiting_days if cfg else 14
        cutoff = _now() - timedelta(days=stale_waiting_days)
        return list(session.scalars(
            select(Task)
            .options(selectinload(Task.task_list))
            .where(
                Task.user_id == user.id,
                Task.status == "aguardando",
                Task.waiting_since < cutoff,
            )
            .order_by(Task.waiting_since)
        ).all())


def archive_task(task_id: str | uuid.UUID) -> bool:
    """Arquiva uma tarefa (status='arquivada')."""
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        task = session.get(Task, uid)
        if task is None:
            return False
        task.status = "arquivada"
        task.last_touched_at = _now()
        return True


def reschedule_task(task_id: str | uuid.UUID, days: int) -> Optional[Task]:
    """Adia tarefa por N dias a partir de agora."""
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        task = session.get(Task, uid)
        if task is None:
            return None
        task.due_at = _now() + timedelta(days=days)
        task.last_touched_at = _now()
        _sync_reminder(session, task)
        return task


# ---------------------------------------------------------------------------
# Lembretes (US-17)
# ---------------------------------------------------------------------------

def _sync_reminder(session: Session, task: Task) -> None:
    """Cria/atualiza/remove o lembrete único da tarefa com base em due_at."""
    existing = session.scalar(
        select(Reminder).where(Reminder.task_id == task.id, Reminder.sent.is_(False))
    )
    if task.due_at is None:
        if existing:
            session.delete(existing)
        return
    if existing:
        existing.remind_at = task.due_at
    else:
        session.add(Reminder(task_id=task.id, remind_at=task.due_at))


def get_due_reminders() -> list[tuple[Reminder, Task, int]]:
    """Retorna lembretes vencidos ainda não enviados com a tarefa e o chat_id do usuário."""
    with get_session() as session:
        rows = session.execute(
            select(Reminder, Task, User.telegram_chat_id)
            .join(Task, Task.id == Reminder.task_id)
            .join(User, User.id == Task.user_id)
            .where(Reminder.sent.is_(False), Reminder.remind_at <= _now())
        ).all()
        return [(r, t, chat_id) for r, t, chat_id in rows]


def mark_reminder_sent(reminder_id: uuid.UUID) -> None:
    with get_session() as session:
        r = session.get(Reminder, reminder_id)
        if r:
            r.sent = True


def get_due_waiting_tasks() -> list[tuple[Task, int]]:
    """Retorna tarefas 'aguardando' cuja due_at já passou (gatilho de retomada por data)."""
    with get_session() as session:
        rows = session.execute(
            select(Task, User.telegram_chat_id)
            .join(User, User.id == Task.user_id)
            .where(
                Task.status == "aguardando",
                Task.due_at.isnot(None),
                Task.due_at <= _now(),
            )
        ).all()
        return [(t, chat_id) for t, chat_id in rows]


def reorder_task(task_id: str | uuid.UUID, direction: str) -> bool:
    """Troca sort_order com a tarefa adjacente na mesma lista. direction: 'up' | 'down'."""
    uid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
    with get_session() as session:
        task = session.get(Task, uid)
        if task is None:
            return False

        base = select(Task).where(
            Task.user_id == task.user_id,
            Task.list_id == task.list_id,
            Task.status == "aberta",
        )
        if direction == "up":
            adjacent = session.scalar(
                base.where(Task.sort_order < task.sort_order).order_by(Task.sort_order.desc())
            )
        else:
            adjacent = session.scalar(
                base.where(Task.sort_order > task.sort_order).order_by(Task.sort_order)
            )
        if adjacent is None:
            return False
        task.sort_order, adjacent.sort_order = adjacent.sort_order, task.sort_order
        return True


# ---------------------------------------------------------------------------
# Conquistas — histórico de conclusões (Sugestão #3)
# ---------------------------------------------------------------------------

def get_conquistas(chat_id: int) -> dict:
    """Retorna estatísticas de tarefas concluídas: hoje, ontem, semana e dias_ativos."""
    from zoneinfo import ZoneInfo
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return {"hoje": 0, "ontem": 0, "semana": 0, "dias_ativos": 0}

        tz = ZoneInfo(user.timezone or "America/Fortaleza")
        now_local = datetime.now(tz)

        hoje_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        ontem_start = hoje_start - timedelta(days=1)
        semana_start = hoje_start - timedelta(days=6)

        hoje_start_utc = hoje_start.astimezone(timezone.utc)
        ontem_start_utc = ontem_start.astimezone(timezone.utc)
        semana_start_utc = semana_start.astimezone(timezone.utc)

        concluidas = list(session.scalars(
            select(Task)
            .where(
                Task.user_id == user.id,
                Task.status == "concluida",
                Task.completed_at >= semana_start_utc,
            )
        ).all())

        def _ct(t: Task) -> datetime:
            dt = t.completed_at
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

        hoje = sum(1 for t in concluidas if _ct(t) >= hoje_start_utc)
        ontem = sum(1 for t in concluidas if ontem_start_utc <= _ct(t) < hoje_start_utc)
        semana = len(concluidas)

        dias_com_conclusao: set[str] = set()
        for t in concluidas:
            dia = _ct(t).astimezone(tz).strftime("%Y-%m-%d")
            dias_com_conclusao.add(dia)

        return {
            "hoje": hoje,
            "ontem": ontem,
            "semana": semana,
            "dias_ativos": len(dias_com_conclusao),
        }


# ---------------------------------------------------------------------------
# /proximos — tarefas dos próximos N dias (Sugestão #5)
# ---------------------------------------------------------------------------

def get_upcoming_tasks(chat_id: int, days: int) -> list[Task]:
    """Tarefas abertas com prazo entre amanhã e N dias à frente."""
    import pytz
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return []
        tz = pytz.timezone(user.timezone or "America/Fortaleza")
        now_local = datetime.now(tz)
        tomorrow = now_local + timedelta(days=1)
        range_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        range_end = (now_local + timedelta(days=days)).replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
        couple_id = _couple_id_for(session, user.id)
        return list(session.scalars(
            select(Task)
            .options(selectinload(Task.task_list))
            .where(
                _visible_filter(user.id, couple_id),
                Task.status == "aberta",
                Task.due_at >= range_start,
                Task.due_at <= range_end,
            )
            .order_by(Task.due_at)
        ).all())


# ---------------------------------------------------------------------------
# /pausar / /retomar — silenciar jobs (Sugestão #7)
# ---------------------------------------------------------------------------

def is_paused(chat_id: int) -> bool:
    """Retorna True se os jobs automáticos estão pausados para este chat."""
    cfg = get_config(chat_id)
    if cfg is None or cfg.paused_until is None:
        return False
    until = cfg.paused_until
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    return until > _now()


def pause_bot(chat_id: int, days: int) -> datetime:
    """Pausa os jobs por N dias. Retorna o datetime de retomada (UTC)."""
    until = _now() + timedelta(days=days)
    update_config(chat_id, paused_until=until)
    return until


def resume_bot(chat_id: int) -> None:
    """Remove a pausa dos jobs."""
    update_config(chat_id, paused_until=None)


# ---------------------------------------------------------------------------
# /projetos — visão de progresso por lista (2e-7)
# ---------------------------------------------------------------------------

def get_projetos(chat_id: int) -> list[ProjetoInfo]:
    """Retorna progresso de cada lista ativa: tarefas abertas, concluídas (30d) e último toque."""
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return []
        cutoff_30d = _now() - timedelta(days=30)
        lists = list(session.scalars(
            select(TaskList)
            .where(TaskList.user_id == user.id, TaskList.archived.is_(False))
            .order_by(TaskList.sort_order)
        ).all())
        projetos: list[ProjetoInfo] = []
        for lst in lists:
            open_count = session.scalar(
                select(func.count(Task.id)).where(
                    Task.list_id == lst.id,
                    Task.status == "aberta",
                    Task.parent_task_id.is_(None),
                )
            ) or 0
            done_30d = session.scalar(
                select(func.count(Task.id)).where(
                    Task.list_id == lst.id,
                    Task.status == "concluida",
                    Task.completed_at >= cutoff_30d,
                    Task.parent_task_id.is_(None),
                )
            ) or 0
            last_touch = session.scalar(
                select(func.max(Task.last_touched_at)).where(
                    Task.list_id == lst.id,
                    Task.status == "aberta",
                )
            )
            if open_count > 0 or done_30d > 0:
                projetos.append(ProjetoInfo(
                    name=lst.name,
                    slug=lst.slug,
                    open_count=open_count,
                    done_30d=done_30d,
                    last_touch=last_touch,
                ))
        return projetos
