"""paused_until no Config — modo pausa

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-26
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "config", "paused_until"):
        op.add_column("config", sa.Column(
            "paused_until", sa.DateTime(timezone=True), nullable=True
        ))


def downgrade() -> None:
    op.drop_column("config", "paused_until")
