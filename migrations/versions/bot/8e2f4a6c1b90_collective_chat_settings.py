"""announcement settings of a collective's chat

Revision ID: 8e2f4a6c1b90
Revises: 3c1d9b7a52e4
Create Date: 2026-10-06 00:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8e2f4a6c1b90"
down_revision: str | None = "3c1d9b7a52e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "collective_chat",
        sa.Column(
            "announce_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        schema="tg",
    )
    op.add_column(
        "collective_chat",
        sa.Column(
            "silent", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        schema="tg",
    )
    op.add_column(
        "collective_chat",
        sa.Column(
            "pin_announcements",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema="tg",
    )
    op.add_column(
        "collective_chat",
        sa.Column("language", sa.String(length=8), nullable=True),
        schema="tg",
    )


def downgrade() -> None:
    for column in ("language", "pin_announcements", "silent", "announce_enabled"):
        op.drop_column("collective_chat", column, schema="tg")
