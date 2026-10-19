"""person account link

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


def downgrade() -> None:
    op.drop_table("person_account")
