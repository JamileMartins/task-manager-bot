"""entidade casal: couples, couple_members, invites

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-30
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())

    if "couples" not in existing:
        op.create_table(
            "couples",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("gcal_calendar_id", sa.Text(), nullable=True),
        )

    if "couple_members" not in existing:
        op.create_table(
            "couple_members",
            sa.Column("couple_id", sa.Uuid(as_uuid=True), sa.ForeignKey("couples.id"), primary_key=True),
            sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
            sa.Column("role", sa.String(16), nullable=False, server_default="member"),
            sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "invites" not in existing:
        op.create_table(
            "invites",
            sa.Column("code", sa.String(16), primary_key=True),
            sa.Column("couple_id", sa.Uuid(as_uuid=True), sa.ForeignKey("couples.id"), nullable=False),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("invites")
    op.drop_table("couple_members")
    op.drop_table("couples")
