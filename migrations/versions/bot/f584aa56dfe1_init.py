"""init

Revision ID: f584aa56dfe1
Revises:
Create Date: 2026-08-24 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f584aa56dfe1"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS tg")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "user",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("notify_client_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("person_id", name="uq_user_person_id"),
    )
    op.create_index(
        op.f("ix_user_person_id"), "user", ["person_id"], unique=False
    )

    op.create_table(
        "user",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("is_bot", sa.Boolean(), nullable=False),
        sa.Column("first_name", sa.String(length=64), nullable=False),
        sa.Column("last_name", sa.String(length=64), nullable=True),
        sa.Column("username", sa.String(length=32), nullable=True),
        sa.Column("language_code", sa.String(length=8), nullable=True),
        sa.Column("is_premium", sa.Boolean(), nullable=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_tg_user_user_id"),
        schema="tg",
    )

    op.create_table(
        "message",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("correlation_key", sa.String(length=64), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "correlation_key", "chat_id", name="uq_message_correlation_chat"
        ),
        schema="tg",
    )
    op.create_index(
        op.f("ix_tg_message_correlation_key"),
        "message",
        ["correlation_key"],
        unique=False,
        schema="tg",
    )

    op.create_table(
        "collective_chat",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("collective_id", sa.Uuid(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.BigInteger(), nullable=True),
        sa.Column("set_by_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "collective_id", name="uq_collective_chat_collective_id"
        ),
        schema="tg",
    )
    op.create_index(
        op.f("ix_tg_collective_chat_collective_id"),
        "collective_chat",
        ["collective_id"],
        unique=False,
        schema="tg",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_tg_collective_chat_collective_id"),
        table_name="collective_chat",
        schema="tg",
    )
    op.drop_table("collective_chat", schema="tg")
    op.drop_index(
        op.f("ix_tg_message_correlation_key"),
        table_name="message",
        schema="tg",
    )
    op.drop_table("message", schema="tg")
    op.drop_table("user", schema="tg")
    op.drop_index(op.f("ix_user_person_id"), table_name="user")
    op.drop_table("user")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP SCHEMA IF EXISTS tg")
