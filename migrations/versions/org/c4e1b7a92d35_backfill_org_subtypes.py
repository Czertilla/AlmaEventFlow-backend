"""give every typed organization its own university, faculty or collective row

Revision ID: c4e1b7a92d35
Revises: 7bd9ba436213
Create Date: 2026-10-21 10:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "c4e1b7a92d35"
down_revision: str | None = "7bd9ba436213"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BACKFILL = [
    f"INSERT INTO {table} (id) "
    f"SELECT o.id FROM organization o WHERE o.type = '{table}' "
    f"AND NOT EXISTS (SELECT 1 FROM {table} t WHERE t.id = o.id)"
    for table in ("university", "faculty", "collective")
]


def upgrade() -> None:
    for statement in BACKFILL:
        op.execute(statement)


def downgrade() -> None:
    pass
