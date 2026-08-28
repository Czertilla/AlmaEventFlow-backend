"""add stage timezone

Revision ID: 69df49b5b9a9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-26 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "69df49b5b9a9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "event_stage",
        sa.Column("timezone", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("event_stage", "timezone")
