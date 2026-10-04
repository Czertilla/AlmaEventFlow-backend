"""timestamps for event children

Revision ID: d4e5f6a7b8c9
Revises: 6a2364c4df41
Create Date: 2026-10-05 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "6a2364c4df41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("event_link", "member", "participation", "reward", "role", "event_stage")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.add_column(
            table,
            sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        )
    for table in ("event_link", "participation", "event_stage"):
        op.execute(
            f"UPDATE {table} SET created_at = event.created_at "
            f"FROM event WHERE event.id = {table}.event_id"
        )
    op.execute(
        "UPDATE reward SET created_at = participation.created_at "
        "FROM participation WHERE participation.id = reward.participation_id"
    )
    for table in TABLES:
        op.alter_column(table, "created_at", server_default=None)


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, "edited_at")
        op.drop_column(table, "created_at")
