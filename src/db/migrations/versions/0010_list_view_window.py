"""lists.view_window — janela de tempo da lista (dia/semana/mes)

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-13
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "lists", "view_window"):
        op.add_column(
            "lists",
            sa.Column("view_window", sa.String(16), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("lists", "view_window")
