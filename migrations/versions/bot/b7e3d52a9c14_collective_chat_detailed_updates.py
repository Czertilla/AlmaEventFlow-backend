"""how much an announcement's update notice says

Revision ID: b7e3d52a9c14
Revises: a4d7c91e3f58
Create Date: 2026-10-06 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7e3d52a9c14"
down_revision: str | None = "a4d7c91e3f58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "collective_chat",
        sa.Column(
            "detailed_updates",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema="tg",
    )


def downgrade() -> None:
    op.drop_column("collective_chat", "detailed_updates", schema="tg")
