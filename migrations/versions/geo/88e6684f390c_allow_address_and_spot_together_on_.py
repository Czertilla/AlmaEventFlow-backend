"""allow address and spot together on location

Revision ID: 88e6684f390c
Revises: 7c1e5a90d2b4
Create Date: 2026-09-22 00:00:00.000000

Relaxes ``ck_location_address_xor_spot`` (exactly one of address_id/spot)
to ``ck_location_address_or_spot`` (at least one) so a location can carry
its own ``spot`` alongside an ``address_id`` -- refining the location to a
specific point near/within that address instead of the address as a whole.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "88e6684f390c"
down_revision: str | None = "7c1e5a90d2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_location_address_xor_spot", "location", type_="check"
    )
    op.create_check_constraint(
        "ck_location_address_or_spot",
        "location",
        "(address_id IS NOT NULL) OR (spot IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_location_address_or_spot", "location", type_="check"
    )
    op.create_check_constraint(
        "ck_location_address_xor_spot",
        "location",
        "(address_id IS NOT NULL) != (spot IS NOT NULL)",
    )
