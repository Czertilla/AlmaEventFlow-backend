"""add planned event status

Revision ID: f4a5b6c7d8e9
Revises: e7a2c4d19b05
Create Date: 2026-11-13 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4a5b6c7d8e9"
down_revision: str | None = "e7a2c4d19b05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO event_status (name) "
        "SELECT 'planned' WHERE NOT EXISTS "
        "(SELECT 1 FROM event_status WHERE name = 'planned')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM event_status WHERE name = 'planned'")
