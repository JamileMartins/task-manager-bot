"""tarefas compartilhadas: couple_id/created_by/assigned_to em tasks, couple_id em lists

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-30
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    bind = op.get_bind()

    # Colunas puras (sem constraint FK no nível do banco): o SQLite não suporta
    # ALTER ADD CONSTRAINT, e adicionar a FK separadamente quebraria o upgrade.
    # Os modelos ORM mantêm a ForeignKey declarada (usada para joins/relationships).
    if not _has_column(bind, "tasks", "couple_id"):
        op.add_column("tasks", sa.Column("couple_id", sa.Uuid(as_uuid=True), nullable=True))
    if not _has_column(bind, "tasks", "created_by"):
        op.add_column("tasks", sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True))
    if not _has_column(bind, "tasks", "assigned_to"):
        op.add_column("tasks", sa.Column("assigned_to", sa.Uuid(as_uuid=True), nullable=True))
    if not _has_column(bind, "lists", "couple_id"):
        op.add_column("lists", sa.Column("couple_id", sa.Uuid(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column("lists", "couple_id")
    op.drop_column("tasks", "assigned_to")
    op.drop_column("tasks", "created_by")
    op.drop_column("tasks", "couple_id")
