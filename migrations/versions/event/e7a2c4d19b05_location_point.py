"""location point

Revision ID: e7a2c4d19b05
Revises: d4e5f6a7b8c9
Create Date: 2026-10-17 15:00:00.000000

``location`` is a projection of geo's locations. It now also keeps where the
location is on a map (its own point, else its address's), so an announcement
can link to it. Rows made before this stay without a point until geo tells
about the location again.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7a2c4d19b05"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("location", sa.Column("lat", sa.Float(), nullable=True))
    op.add_column("location", sa.Column("lon", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("location", "lon")
    op.drop_column("location", "lat")
