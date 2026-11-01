"""visibility settings, their history and the notification outbox

Revision ID: e8b2c4d6a913
Revises: d3a5f1c8e204
Create Date: 2026-10-27 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e8b2c4d6a913"
down_revision: str | None = "d3a5f1c8e204"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "person_field_visibility",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("field_key", sa.String(length=64), nullable=False),
        sa.Column("audience", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "audience IN ('private', 'context', 'all_users')",
            name="ck_person_field_visibility_audience",
        ),
        sa.ForeignKeyConstraint(["person_id"], ["person.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("person_id", "field_key"),
    )
    op.create_table(
        "person_field_visibility_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("field_key", sa.String(length=64), nullable=False),
        sa.Column("old_audience", sa.String(length=16), nullable=True),
        sa.Column("new_audience", sa.String(length=16), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source IN ('owner', 'admin')",
            name="ck_person_field_visibility_history_source",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_person_field_visibility_history_person_created",
        "person_field_visibility_history",
        ["person_id", "created_at"],
    )
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.String(length=1000), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'published', 'dead')",
            name="ck_notification_outbox_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_outbox_status_due",
        "notification_outbox",
        ["status", "next_attempt_at"],
    )
    op.execute(
        """
        CREATE FUNCTION append_only_guard() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only', TG_TABLE_NAME
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER person_field_visibility_history_rows "
        "BEFORE UPDATE OR DELETE ON person_field_visibility_history "
        "FOR EACH ROW EXECUTE FUNCTION append_only_guard()"
    )
    op.execute(
        "CREATE TRIGGER person_field_visibility_history_truncate "
        "BEFORE TRUNCATE ON person_field_visibility_history "
        "FOR EACH STATEMENT EXECUTE FUNCTION append_only_guard()"
    )


def downgrade() -> None:
    op.drop_table("notification_outbox")
    op.drop_table("person_field_visibility_history")
    op.execute("DROP FUNCTION append_only_guard()")
    op.drop_table("person_field_visibility")
