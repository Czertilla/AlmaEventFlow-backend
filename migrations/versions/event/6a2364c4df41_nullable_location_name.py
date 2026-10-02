"""nullable location name

Revision ID: 6a2364c4df41
Revises: 69df49b5b9a9
Create Date: 2026-09-01 00:00:00.000000

An "address-proxy" location (created via geo's location-from-address flow
when the principal didn't bother naming it, just picked an address) has no
name of its own -- matches core.models.location.LocationAORM, which every
service's local Location projection derives from.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6a2364c4df41"
down_revision: str | None = "69df49b5b9a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "location", "name", existing_type=sa.String(length=512), nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        "location", "name", existing_type=sa.String(length=512), nullable=False
    )
