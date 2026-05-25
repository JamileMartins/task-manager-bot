"""Schema inicial: users, lists, tasks, reminders, config

Revision ID: 001
Revises:
Create Date: 2026-05-25
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="America/Fortaleza"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_chat_id"),
    )

    op.create_table(
        "lists",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("is_couple", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lists_user_id", "lists", ["user_id"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("list_id", sa.Uuid(as_uuid=True), nullable=True),
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
        sa.Column("parent_task_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("waiting_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_touched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["list_id"], ["lists.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"])
    op.create_index("ix_tasks_list_id", "tasks", ["list_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])

    op.create_table(
        "reminders",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("task_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reminders_remind_at", "reminders", ["remind_at", "sent"])

    op.create_table(
        "config",
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("daily_summary_time", sa.Time(), nullable=True),
        sa.Column("weekly_review_dow", sa.SmallInteger(), nullable=True),
        sa.Column("weekly_review_time", sa.Time(), nullable=True),
        sa.Column("couple_group_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("stale_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("stale_waiting_days", sa.Integer(), nullable=False, server_default="14"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("config")
    op.drop_table("reminders")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_list_id", table_name="tasks")
    op.drop_index("ix_tasks_user_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_lists_user_id", table_name="lists")
    op.drop_table("lists")
    op.drop_table("users")
