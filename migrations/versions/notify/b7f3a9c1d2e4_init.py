"""init

Revision ID: b7f3a9c1d2e4
Revises:
Create Date: 2026-06-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b7f3a9c1d2e4"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


transport_type = postgresql.ENUM(
    "email",
    "webpush",
    "telegram",
    "mobile",
    "realtime",
    name="transport_type",
)

notification_category = postgresql.ENUM(
    "general",
    "event",
    "attendance",
    "system",
    name="notification_category",
)

delivery_status = postgresql.ENUM(
    "pending",
    "retry_scheduled",
    "sent",
    "delivered",
    "failed",
    "skipped",
    "expired",
    "cancelled",
    name="delivery_status",
)

outbox_status = postgresql.ENUM(
    "pending",
    "published",
    "failed",
    name="outbox_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    transport_type.create(bind, checkfirst=True)
    notification_category.create(bind, checkfirst=True)
    delivery_status.create(bind, checkfirst=True)
    outbox_status.create(bind, checkfirst=True)

    op.create_table(
        "account",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=True),
        sa.Column("person_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_account_person_id"), "account", ["person_id"], unique=False
    )

    op.create_table(
        "preference",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "transport",
            postgresql.ENUM(name="transport_type", create_type=False),
            nullable=False,
        ),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "transport", name="uq_preference_user_transport"
        ),
    )
    op.create_index(
        op.f("ix_preference_user_id"), "preference", ["user_id"], unique=False
    )

    op.create_table(
        "client",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "transport",
            postgresql.ENUM(name="transport_type", create_type=False),
            nullable=False,
        ),
        sa.Column("endpoint", sa.String(length=512), nullable=False),
        sa.Column("label", sa.String(length=256), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "transport",    
            "endpoint",
            name="uq_client_user_transport_endpoint",
        ),
    )
    op.create_index(
        op.f("ix_client_user_id"), "client", ["user_id"], unique=False
    )

    op.create_table(
        "notification",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column(
            "category",
            postgresql.ENUM(name="notification_category", create_type=False),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("action_url", sa.String(length=2048), nullable=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_notification_event_id"),
    )
    op.create_index(
        op.f("ix_notification_event_id"),
        "notification",
        ["event_id"],
        unique=False,
    )

    op.create_table(
        "notification_recipient",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("notification_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["notification_id"], ["notification.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "notification_id",
            "user_id",
            name="uq_recipient_notification_user",
        ),
    )
    op.create_index(
        op.f("ix_notification_recipient_notification_id"),
        "notification_recipient",
        ["notification_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_recipient_user_id"),
        "notification_recipient",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "notification_delivery",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("notification_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "transport",
            postgresql.ENUM(name="transport_type", create_type=False),
            nullable=False,
        ),
        sa.Column("client_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="delivery_status", create_type=False),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=1024), nullable=True),
        sa.Column("provider_message_id", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["notification_id"], ["notification.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["recipient_id"],
            ["notification_recipient.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notification_delivery_notification_id"),
        "notification_delivery",
        ["notification_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_delivery_recipient_id"),
        "notification_delivery",
        ["recipient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_delivery_user_id"),
        "notification_delivery",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_delivery_status"),
        "notification_delivery",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_delivery_next_attempt_at"),
        "notification_delivery",
        ["next_attempt_at"],
        unique=False,
    )

    op.create_table(
        "outbox_event",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("topic", sa.String(length=256), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="outbox_status", create_type=False),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_outbox_status_id", "outbox_event", ["status", "id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_status_id", table_name="outbox_event")
    op.drop_table("outbox_event")
    op.drop_index(
        op.f("ix_notification_delivery_next_attempt_at"),
        table_name="notification_delivery",
    )
    op.drop_index(
        op.f("ix_notification_delivery_status"),
        table_name="notification_delivery",
    )
    op.drop_index(
        op.f("ix_notification_delivery_user_id"),
        table_name="notification_delivery",
    )
    op.drop_index(
        op.f("ix_notification_delivery_recipient_id"),
        table_name="notification_delivery",
    )
    op.drop_index(
        op.f("ix_notification_delivery_notification_id"),
        table_name="notification_delivery",
    )
    op.drop_table("notification_delivery")
    op.drop_index(
        op.f("ix_notification_recipient_user_id"),
        table_name="notification_recipient",
    )
    op.drop_index(
        op.f("ix_notification_recipient_notification_id"),
        table_name="notification_recipient",
    )
    op.drop_table("notification_recipient")
    op.drop_index(op.f("ix_notification_event_id"), table_name="notification")
    op.drop_table("notification")

    op.drop_index(op.f("ix_client_user_id"), table_name="client")
    op.drop_table("client")
    op.drop_index(op.f("ix_preference_user_id"), table_name="preference")
    op.drop_table("preference")
    op.drop_index(op.f("ix_account_person_id"), table_name="account")
    op.drop_table("account")
    bind = op.get_bind()
    outbox_status.drop(bind, checkfirst=True)
    delivery_status.drop(bind, checkfirst=True)
    notification_category.drop(bind, checkfirst=True)
    transport_type.drop(bind, checkfirst=True)
