"""the journal of access to sensitive data and outbox notices for an account

Revision ID: c5e2a7f9b3d1
Revises: b7d4e9a1c3f6
Create Date: 2026-11-01 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c5e2a7f9b3d1"
down_revision: str | None = "b7d4e9a1c3f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIONS = (
    "read",
    "export",
    "request_created",
    "grant_approved",
    "grant_declined",
    "grant_revoked",
    "key_destroyed",
    "denied",
)
VIAS = ("self", "superuser", "grant", "none")


def upgrade() -> None:
    op.create_table(
        "sensitive_access_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("actor_person_id", sa.Uuid(), nullable=True),
        sa.Column("subject_person_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=True),
        sa.Column("grant_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("via", sa.String(length=16), nullable=False),
        sa.Column("fields", postgresql.ARRAY(sa.String(length=64)), nullable=False),
        sa.Column("outcome", sa.String(length=64), nullable=False),
        sa.Column("notified", sa.Boolean(), nullable=False),
        sa.Column("request_id_http", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "action IN (" + ", ".join(f"'{action}'" for action in ACTIONS) + ")",
            name="ck_sensitive_access_log_action",
        ),
        sa.CheckConstraint(
            "via IN (" + ", ".join(f"'{via}'" for via in VIAS) + ")",
            name="ck_sensitive_access_log_via",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sensitive_access_log_subject_created",
        "sensitive_access_log",
        ["subject_person_id", "created_at"],
    )
    op.create_index(
        "ix_sensitive_access_log_actor_created",
        "sensitive_access_log",
        ["actor_person_id", "created_at"],
    )
    op.create_index(
        "ix_sensitive_access_log_request", "sensitive_access_log", ["request_id"]
    )
    op.execute(
        "CREATE TRIGGER sensitive_access_log_rows "
        "BEFORE UPDATE OR DELETE ON sensitive_access_log "
        "FOR EACH ROW EXECUTE FUNCTION append_only_guard()"
    )
    op.execute(
        "CREATE TRIGGER sensitive_access_log_truncate "
        "BEFORE TRUNCATE ON sensitive_access_log "
        "FOR EACH STATEMENT EXECUTE FUNCTION append_only_guard()"
    )
    op.add_column("notification_outbox", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.alter_column("notification_outbox", "person_id", nullable=True)
    op.create_check_constraint(
        "ck_notification_outbox_recipient",
        "notification_outbox",
        "person_id IS NOT NULL OR user_id IS NOT NULL",
    )


def downgrade() -> None:
    op.execute("DELETE FROM notification_outbox WHERE person_id IS NULL")
    op.drop_constraint(
        "ck_notification_outbox_recipient", "notification_outbox", type_="check"
    )
    op.alter_column("notification_outbox", "person_id", nullable=False)
    op.drop_column("notification_outbox", "user_id")
    op.drop_table("sensitive_access_log")
