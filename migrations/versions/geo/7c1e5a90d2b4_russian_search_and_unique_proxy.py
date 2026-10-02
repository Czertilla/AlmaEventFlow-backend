"""russian morphological search and unique address-proxy location

Revision ID: 7c1e5a90d2b4
Revises: 5abb14baa932
Create Date: 2026-09-20 00:00:00.000000

Switches address.name_tsv from the ``simple`` text-search config (no
stemming) to ``russian`` so search matches word forms, and makes the
address-proxy location (unnamed location anchored to an address) unique per
address so concurrent "pick this address" requests resolve to one row.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7c1e5a90d2b4"
down_revision: str | None = "5abb14baa932"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _recreate_name_tsv(config: str) -> None:
    op.drop_index(
        "idx_spot_search_fts", table_name="address", postgresql_using="gin"
    )
    op.drop_column("address", "name_tsv")
    op.add_column(
        "address",
        sa.Column(
            "name_tsv",
            postgresql.TSVECTOR(),
            sa.Computed(f"to_tsvector('{config}', \"name\")", persisted=True),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_spot_search_fts",
        "address",
        ["name_tsv"],
        unique=False,
        postgresql_using="gin",
    )


def upgrade() -> None:
    _recreate_name_tsv("russian")
    op.create_index(
        "uq_location_address_proxy",
        "location",
        ["address_id"],
        unique=True,
        postgresql_where=sa.text("name IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_location_address_proxy",
        table_name="location",
        postgresql_where=sa.text("name IS NULL"),
    )
    _recreate_name_tsv("simple")
