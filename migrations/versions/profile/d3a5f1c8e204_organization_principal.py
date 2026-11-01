"""organization principal

Revision ID: d3a5f1c8e204
Revises: b7c3e9a4d2f1
Create Date: 2026-10-27 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3a5f1c8e204"
down_revision: str | None = "b7c3e9a4d2f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organization", sa.Column("principal_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_organization_principal_id"), "organization", ["principal_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_organization_principal_id"), table_name="organization")
    op.drop_column("organization", "principal_id")
