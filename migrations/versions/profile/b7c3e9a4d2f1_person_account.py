"""person account link and its history

Revision ID: b7c3e9a4d2f1
Revises: a1c0de5b7e21
Create Date: 2026-10-20 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7c3e9a4d2f1"
down_revision: str | None = "a1c0de5b7e21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "person_account",
        sa.Column("person_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["person_id"], ["person.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("person_id"),
        sa.UniqueConstraint("user_id"),
    )
    op.alter_column("person_account", "created_at", server_default=None)
    op.create_table(
        "person_account_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("old_person_id", sa.UUID(), nullable=True),
        sa.Column("new_person_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_person_account_history_user_id"),
        "person_account_history",
        ["user_id"],
    )
    op.create_index(
        op.f("ix_person_account_history_old_person_id"),
        "person_account_history",
        ["old_person_id"],
    )
    op.create_index(
        op.f("ix_person_account_history_new_person_id"),
        "person_account_history",
        ["new_person_id"],
    )
    op.execute(
        """
        CREATE FUNCTION person_account_history_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'person_account_history is append-only'
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER person_account_history_append_only "
        "BEFORE UPDATE OR DELETE ON person_account_history "
        "FOR EACH ROW EXECUTE FUNCTION person_account_history_append_only()"
    )


def downgrade() -> None:
    op.drop_table("person_account_history")
    op.execute("DROP FUNCTION person_account_history_append_only()")
    op.drop_table("person_account")
