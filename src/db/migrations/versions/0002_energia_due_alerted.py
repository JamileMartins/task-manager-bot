"""energia_do_dia no Config e due_alerted no Task

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-26
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "config", "energia_do_dia"):
        op.add_column("config", sa.Column("energia_do_dia", sa.String(8), nullable=True))

    if not _has_column(bind, "config", "energia_do_dia_data"):
        op.add_column("config", sa.Column("energia_do_dia_data", sa.Date(), nullable=True))

    if not _has_column(bind, "tasks", "due_alerted"):
        op.add_column("tasks", sa.Column(
            "due_alerted", sa.Boolean(), nullable=True, server_default="false"
        ))


def downgrade() -> None:
    op.drop_column("tasks", "due_alerted")
    op.drop_column("config", "energia_do_dia_data")
    op.drop_column("config", "energia_do_dia")
