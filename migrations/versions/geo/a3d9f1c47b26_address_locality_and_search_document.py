"""address locality and search document

Revision ID: a3d9f1c47b26
Revises: 5bae7df6dd2c
Create Date: 2026-10-13 12:00:00.000000

``address.locality`` is the place line kept next to the clean ``name``
("Москва, Россия"). The text-search document now covers both: ``search_tsv``
replaces ``name_tsv`` (street weighs more than the place), so a city in the
query narrows the result. The trigram index stays on ``name``: every row of a
city shares its trigrams, so an index over the place line prunes nothing.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a3d9f1c47b26"
down_revision: str | None = "5bae7df6dd2c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEARCH_TSV = (
    "setweight(to_tsvector('russian', \"name\"), 'A') || "
    "setweight(to_tsvector('russian', \"locality\"), 'C')"
)
NAME_TSV = "to_tsvector('russian', \"name\")"


def upgrade() -> None:
    op.add_column(
        "address",
        sa.Column(
            "locality",
            sa.String(length=512),
            server_default="",
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE address AS a
        SET locality = concat_ws(
            ', ',
            btrim(c.name),
            NULLIF(btrim(r.name), btrim(c.name)),
            CASE WHEN btrim(co.name) IN (btrim(c.name), btrim(r.name))
                 THEN NULL ELSE btrim(co.name) END
        )
        FROM city AS c
        JOIN region AS r ON r.id = c.region_id
        JOIN country AS co ON co.id = r.country_id
        WHERE c.id = a.city_id
        """
    )

    op.drop_index("idx_spot_search_fts", table_name="address", postgresql_using="gin")
    op.drop_column("address", "name_tsv")
    op.add_column(
        "address",
        sa.Column(
            "search_tsv",
            postgresql.TSVECTOR(),
            sa.Computed(SEARCH_TSV, persisted=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_address_search_tsv",
        "address",
        ["search_tsv"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_address_search_tsv", table_name="address", postgresql_using="gin")
    op.drop_column("address", "search_tsv")
    op.add_column(
        "address",
        sa.Column(
            "name_tsv",
            postgresql.TSVECTOR(),
            sa.Computed(NAME_TSV, persisted=True),
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
    op.drop_column("address", "locality")
