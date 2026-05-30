"""modo conjunto de tarefa de casal: tasks.couple_joint

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-30
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "tasks", "couple_joint"):
        op.add_column(
            "tasks",
            sa.Column("couple_joint", sa.Boolean(), nullable=True, server_default=sa.false()),
        )


def downgrade() -> None:
    op.drop_column("tasks", "couple_joint")
