"""Google Calendar (C6): tokens no user e mapeamento de evento no task

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-30
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "users", "google_refresh_token"):
        op.add_column("users", sa.Column("google_refresh_token", sa.Text(), nullable=True))
    if not _has_column(bind, "users", "google_calendar_id"):
        op.add_column("users", sa.Column("google_calendar_id", sa.Text(), nullable=True))
    if not _has_column(bind, "tasks", "gcal_event_id"):
        op.add_column("tasks", sa.Column("gcal_event_id", sa.String(256), nullable=True))
    if not _has_column(bind, "tasks", "gcal_synced_at"):
        op.add_column("tasks", sa.Column("gcal_synced_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "gcal_synced_at")
    op.drop_column("tasks", "gcal_event_id")
    op.drop_column("users", "google_calendar_id")
    op.drop_column("users", "google_refresh_token")
