"""tasks.blocked_by_task_id — dependência entre tarefas

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-02
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "tasks", "blocked_by_task_id"):
        op.add_column(
            "tasks",
            sa.Column(
                "blocked_by_task_id",
                sa.dialects.postgresql.UUID(as_uuid=True),
                sa.ForeignKey("tasks.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    op.drop_column("tasks", "blocked_by_task_id")
