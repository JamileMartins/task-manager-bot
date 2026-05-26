"""schema inicial completo

Revision ID: 0001
Revises:
Create Date: 2026-05-25

Nota de deploy: se o banco de produção já tiver as tabelas criadas via
create_all(), rode antes de subir o novo código:

    alembic stamp 0001

Isso marca o banco como já estando nesta revisão sem executar o upgrade().
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())

    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False, unique=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("timezone", sa.String(64), nullable=False, server_default="America/Fortaleza"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "lists" not in existing:
        op.create_table(
            "lists",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("slug", sa.String(128), nullable=False),
            sa.Column("is_couple", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("archived", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        )

    if "tasks" not in existing:
        op.create_table(
            "tasks",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("list_id", sa.Uuid(as_uuid=True), sa.ForeignKey("lists.id"), nullable=True),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("quadrant", sa.SmallInteger(), nullable=True),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("recurrence", sa.String(16), nullable=True),
            sa.Column("estimate_min", sa.Integer(), nullable=True),
            sa.Column("energy", sa.String(16), nullable=True),
            sa.Column("status", sa.String(16), nullable=False, server_default="aberta"),
            sa.Column("blocker_type", sa.String(32), nullable=True),
            sa.Column("blocker_note", sa.Text(), nullable=True),
            sa.Column("blocker_is_external", sa.Boolean(), nullable=True),
            sa.Column("next_step", sa.Text(), nullable=True),
            sa.Column(
                "parent_task_id",
                sa.Uuid(as_uuid=True),
                sa.ForeignKey("tasks.id"),
                nullable=True,
            ),
            sa.Column("waiting_since", sa.DateTime(timezone=True), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_touched_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "reminders" not in existing:
        op.create_table(
            "reminders",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("task_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=False),
            sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("sent", sa.Boolean(), nullable=False, server_default="false"),
        )

    if "config" not in existing:
        op.create_table(
            "config",
            sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
            sa.Column("daily_summary_time", sa.Time(), nullable=True),
            sa.Column("weekly_review_dow", sa.SmallInteger(), nullable=True),
            sa.Column("weekly_review_time", sa.Time(), nullable=True),
            sa.Column("couple_group_chat_id", sa.BigInteger(), nullable=True),
            sa.Column("stale_days", sa.Integer(), nullable=False, server_default="7"),
            sa.Column("stale_waiting_days", sa.Integer(), nullable=False, server_default="14"),
        )


def downgrade() -> None:
    op.drop_table("config")
    op.drop_table("reminders")
    op.drop_table("tasks")
    op.drop_table("lists")
    op.drop_table("users")
