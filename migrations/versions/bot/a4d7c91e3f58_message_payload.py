"""what a sent message showed, to tell what changed on its next edit

Revision ID: a4d7c91e3f58
Revises: 8e2f4a6c1b90
Create Date: 2026-10-06 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a4d7c91e3f58"
down_revision: str | None = "8e2f4a6c1b90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "message",
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="tg",
    )


def downgrade() -> None:
    op.drop_column("message", "payload", schema="tg")
