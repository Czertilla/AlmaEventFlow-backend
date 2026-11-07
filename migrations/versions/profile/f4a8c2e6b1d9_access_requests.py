"""access requests of a collective's leader and the grants of their subjects

Revision ID: f4a8c2e6b1d9
Revises: c5e2a7f9b3d1
Create Date: 2026-11-03 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f4a8c2e6b1d9"
down_revision: str | None = "c5e2a7f9b3d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = ("pending", "active", "declined", "revoked")
IMMUTABLE = ("access_request", "access_request_field")


def upgrade() -> None:
    op.create_table(
        "access_request",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("grantee_person_id", sa.Uuid(), nullable=False),
        sa.Column("collective_id", sa.Uuid(), nullable=False),
        sa.Column("collective_name", sa.String(length=128), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_access_request_grantee", "access_request", ["grantee_person_id"]
    )
    op.create_table(
        "access_request_field",
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("field_key", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["request_id"], ["access_request.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("request_id", "field_key"),
    )
    op.create_table(
        "access_grant",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("subject_person_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "consent_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN (" + ", ".join(f"'{status}'" for status in STATUSES) + ")",
            name="ck_access_grant_status",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"], ["access_request.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["subject_person_id"], ["person.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "request_id", "subject_person_id", name="uq_access_grant_request_subject"
        ),
    )
    op.create_index(
        "ix_access_grant_subject_status",
        "access_grant",
        ["subject_person_id", "status"],
    )
    for table in IMMUTABLE:
        op.execute(
            f"CREATE TRIGGER {table}_rows BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION append_only_guard()"
        )
        op.execute(
            f"CREATE TRIGGER {table}_truncate BEFORE TRUNCATE ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION append_only_guard()"
        )
    op.alter_column("sensitive_access_log", "subject_person_id", nullable=True)
    op.create_check_constraint(
        "ck_sensitive_access_log_subject",
        "sensitive_access_log",
        "subject_person_id IS NOT NULL OR request_id IS NOT NULL",
    )


def downgrade() -> None:
    journal = "ALTER TABLE sensitive_access_log {} TRIGGER sensitive_access_log_rows"
    op.execute(journal.format("DISABLE"))
    op.execute("DELETE FROM sensitive_access_log WHERE subject_person_id IS NULL")
    op.execute(journal.format("ENABLE"))
    op.drop_constraint(
        "ck_sensitive_access_log_subject", "sensitive_access_log", type_="check"
    )
    op.alter_column("sensitive_access_log", "subject_person_id", nullable=False)
    op.drop_table("access_grant")
    op.drop_table("access_request_field")
    op.drop_table("access_request")
