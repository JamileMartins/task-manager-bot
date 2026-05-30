from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Fortaleza")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    lists: Mapped[List[TaskList]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tasks: Mapped[List[Task]] = relationship(
        back_populates="user", cascade="all, delete-orphan", foreign_keys="Task.user_id"
    )
    config: Mapped[Optional[Config]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class TaskList(Base):
    __tablename__ = "lists"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    is_couple: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    couple_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("couples.id"), nullable=True
    )
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped[User] = relationship(back_populates="lists")
    tasks: Mapped[List[Task]] = relationship(back_populates="task_list")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    list_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("lists.id"), nullable=True)
    # Tarefa do casal: couple_id não-nulo = visível/editável pelos dois membros.
    couple_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("couples.id"), nullable=True
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quadrant: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    recurrence: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    estimate_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    energy: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="aberta")
    blocker_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    blocker_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    blocker_is_external: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    next_step: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tasks.id"), nullable=True
    )
    waiting_since: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    due_alerted: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_touched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship(back_populates="tasks", foreign_keys=[user_id])
    task_list: Mapped[Optional[TaskList]] = relationship(back_populates="tasks", foreign_keys=[list_id])
    reminders: Mapped[List[Reminder]] = relationship(back_populates="task", cascade="all, delete-orphan")


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    task: Mapped[Task] = relationship(back_populates="reminders")


class Couple(Base):
    __tablename__ = "couples"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Reservado para a sincronização futura com Google Calendar (calendário do casal).
    gcal_calendar_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    members: Mapped[List[CoupleMember]] = relationship(
        back_populates="couple", cascade="all, delete-orphan"
    )


class CoupleMember(Base):
    __tablename__ = "couple_members"

    couple_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("couples.id"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="member")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    couple: Mapped[Couple] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class Invite(Base):
    __tablename__ = "invites"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    couple_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("couples.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class Config(Base):
    __tablename__ = "config"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    daily_summary_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    weekly_review_dow: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    weekly_review_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    couple_group_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    stale_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    stale_waiting_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    energia_do_dia: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    energia_do_dia_data: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    paused_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="config")
