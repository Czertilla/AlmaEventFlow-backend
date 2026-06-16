"""add calendar subscription and change log tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-16 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from event.enum.calendar import CalendarSubscriptionTypeEnum


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "calendar_subscription_type",
        sa.Column("id", sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    values = ", ".join(f"('{m.value}')" for m in CalendarSubscriptionTypeEnum)
    op.execute(f"INSERT INTO calendar_subscription_type (name) VALUES {values}")

    op.create_table(
        "calendar_subscription",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=True),
        sa.Column("collective_id", sa.Uuid(), nullable=True),
        sa.Column("type_id", sa.SmallInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_accessed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
        sa.ForeignKeyConstraint(
            ["type_id"], ["calendar_subscription_type.id"]
        ),
        sa.ForeignKeyConstraint(
            ["person_id"], ["person.id"], ondelete="NO ACTION"
        ),
        sa.ForeignKeyConstraint(
            ["collective_id"], ["collective.id"], ondelete="NO ACTION"
        ),
    )
    op.create_index(
        "ix_calendar_subscription_token_hash",
        "calendar_subscription",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_calendar_subscription_owner",
        "calendar_subscription",
        ["owner_user_id"],
    )

    op.create_table(
        "calendar_change_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("change_type", sa.String(length=32), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("collective_id", sa.Uuid(), nullable=False),
        sa.Column("participation_id", sa.Uuid(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("event_name", sa.String(length=128), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_calendar_change_log_collective_time",
        "calendar_change_log",
        ["collective_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_calendar_change_log_collective_time",
        table_name="calendar_change_log",
    )
    op.drop_table("calendar_change_log")

    op.drop_index(
        "ix_calendar_subscription_owner",
        table_name="calendar_subscription",
    )
    op.drop_index(
        "ix_calendar_subscription_token_hash",
        table_name="calendar_subscription",
    )
    op.drop_table("calendar_subscription")
    op.drop_table("calendar_subscription_type")
