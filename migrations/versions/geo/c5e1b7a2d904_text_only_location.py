"""text-only location

Revision ID: c5e1b7a2d904
Revises: a3d9f1c47b26
Create Date: 2026-10-17 12:00:00.000000

A location may rest on its name alone: the address written as plain text, the
fallback for a place nothing is known about on a map. ``ck_location_address_or_spot``
now also accepts a name. Downgrade deletes those locations: the old constraint
cannot hold them.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5e1b7a2d904"
down_revision: str | None = "a3d9f1c47b26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_location_address_or_spot", "location", type_="check")
    op.create_check_constraint(
        "ck_location_address_or_spot",
        "location",
        "(address_id IS NOT NULL) OR (spot IS NOT NULL) OR (name IS NOT NULL)",
    )


def downgrade() -> None:
    op.execute("DELETE FROM location WHERE address_id IS NULL AND spot IS NULL")
    op.drop_constraint("ck_location_address_or_spot", "location", type_="check")
    op.create_check_constraint(
        "ck_location_address_or_spot",
        "location",
        "(address_id IS NOT NULL) OR (spot IS NOT NULL)",
    )
