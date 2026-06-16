"""add event_level

Revision ID: f3a1b2c3d4e5
Revises: 6c46d892227b
Create Date: 2026-06-14 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from event.enum.level_v1 import EventLevelEnumV1


# revision identifiers, used by Alembic.
revision: str = "f3a1b2c3d4e5"
down_revision: Union[str, None] = "6c46d892227b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_level",
        sa.Column("id", sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    values = ", ".join(f"('{m.value}')" for m in EventLevelEnumV1)
    op.execute(f"INSERT INTO event_level (name) VALUES {values}")
    op.add_column(
        "event",
        sa.Column("level_id", sa.SmallInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_event_level_id",
        "event",
        "event_level",
        ["level_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_event_level_id", "event", type_="foreignkey")
    op.drop_column("event", "level_id")
    op.drop_table("event_level")
