"""tasks.category — subcategoria dentro de lista (medicacao, agendamento)

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-31
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "tasks", "category"):
        op.add_column(
            "tasks",
            sa.Column("category", sa.String(32), nullable=True),
        )
    # Backfill: tarefas com recorrência na lista Saúde eram medicações.
    op.execute(
        """
        UPDATE tasks
        SET category = 'medicacao'
        WHERE category IS NULL
          AND recurrence IS NOT NULL
          AND list_id IN (
              SELECT id FROM lists WHERE slug = 'saude'
          )
        """
    )


def downgrade() -> None:
    op.drop_column("tasks", "category")
