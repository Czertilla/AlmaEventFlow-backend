"""contact timestamps

Revision ID: a1c0de5b7e21
Revises: 60bac58e30bb
Create Date: 2026-10-05 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1c0de5b7e21"
down_revision: str | None = "60bac58e30bb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contact",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "contact",
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("contact", "created_at", server_default=None)


def downgrade() -> None:
    op.drop_column("contact", "edited_at")
    op.drop_column("contact", "created_at")
