"""Lógica de domínio do bot Foco — sem dependência do Telegram."""
from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from src.db.models import Config, Reminder, Task, TaskList, User
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

        if task.recurrence and task.recurrence in _RECURRENCE_DELTA:
            delta = _RECURRENCE_DELTA[task.recurrence]
            base = task.due_at if task.due_at else now
            next_due = base + delta
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


@dataclass
class TaskGroup:
    name: str
    slug: Optional[str]
    list_id: Optional[uuid.UUID]
    tasks: list[Task]


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


def get_couple_tasks(chat_id: int) -> tuple[list[Task], int | None]:
    """Retorna (tarefas abertas da lista de casal, group_chat_id configurado)."""
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return [], None
        couple_list = session.scalar(
            select(TaskList).where(
                TaskList.user_id == user.id,
                TaskList.is_couple.is_(True),
                TaskList.archived.is_(False),
            )
        )
        tasks: list[Task] = []
        if couple_list:
            tasks = list(session.scalars(
                select(Task)
                .where(Task.list_id == couple_list.id, Task.status == "aberta")
                .order_by(Task.quadrant.nullslast(), Task.sort_order)
            ).all())
        cfg = session.scalar(select(Config).where(Config.user_id == user.id))
        group_id = cfg.couple_group_chat_id if cfg else None
        return tasks, group_id


def search_tasks(chat_id: int, term: str) -> list[Task]:
    """Busca tarefas não concluídas/arquivadas por palavra-chave no título ou notas."""
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return []
        pattern = f"%{term}%"
        return list(session.scalars(
            select(Task)
            .options(selectinload(Task.task_list))
            .where(
                Task.user_id == user.id,
                Task.status.not_in(["concluida", "arquivada"]),
                or_(Task.title.ilike(pattern), Task.notes.ilike(pattern)),
            )
            .order_by(Task.status, Task.quadrant.nullslast(), Task.sort_order)
            .limit(20)
        ).all())


def get_all_open_tasks(chat_id: int) -> list[TaskGroup]:
    """Retorna todas as tarefas abertas/aguardando agrupadas por lista (Inbox primeiro)."""
    with get_session() as session:
        user = session.scalar(select(User).where(User.telegram_chat_id == chat_id))
        if user is None:
            return []

        inbox_tasks = list(session.scalars(
            select(Task)
            .where(
                Task.user_id == user.id,
                Task.list_id.is_(None),
                Task.status.in_(["aberta", "aguardando"]),
            )
            .order_by(Task.sort_order, Task.created_at)
        ).all())

        lists = list(session.scalars(
            select(TaskList)
            .where(TaskList.user_id == user.id, TaskList.archived.is_(False))
            .order_by(TaskList.sort_order)
        ).all())

        groups: list[TaskGroup] = []
        if inbox_tasks:
            groups.append(TaskGroup(name="Inbox", slug=None, list_id=None, tasks=inbox_tasks))

        for lst in lists:
            tasks = list(session.scalars(
                select(Task)
                .where(
                    Task.list_id == lst.id,
                    Task.status.in_(["aberta", "aguardando"]),
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

        now = _now()
        saved: list[Task] = []

        for t in tarefas:
            list_name = t.get("lista_sugerida")
            list_id = lista_map.get(list_name) if list_name else None

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

        candidates = session.scalars(
            select(Task)
            .options(selectinload(Task.task_list))
            .where(
                Task.user_id == user.id,
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
    _allowed = {"quadrant", "energy", "estimate_min", "due_at", "list_id", "next_step", "recurrence"}
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
) -> Optional[Task]:
    """Salva o tipo de impedimento na tarefa."""
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
        task.last_touched_at = _now()
        return task


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
    """Desbloqueaia tarefa: volta para 'aberta' e limpa campos de bloqueio."""
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

        today_tasks = list(session.scalars(
            select(Task)
            .options(selectinload(Task.task_list))
            .where(
                Task.user_id == user.id,
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
                Task.user_id == user.id,
                Task.status == "aberta",
                Task.quadrant.in_([1, 2]),
            )
            .order_by(Task.quadrant, Task.sort_order)
            .limit(3 + len(today_ids))
        )
        focus_raw = session.scalars(q).all()
        focus_tasks = [t for t in focus_raw if t.id not in today_ids][:3]

        return today_tasks, focus_tasks


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
