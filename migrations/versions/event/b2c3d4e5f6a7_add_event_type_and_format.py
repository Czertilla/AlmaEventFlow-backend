"""add event_type and format

Revision ID: b2c3d4e5f6a7
Revises: f3a1b2c3d4e5
Create Date: 2026-06-14 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from event.enum.type_v1 import EventTypeEnumV1
from event.enum.format import EventFormatEnumV1


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "f3a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

event_format = sa.Enum(
    EventFormatEnumV1, name="event_format"
)

def upgrade() -> None:
    op.create_table(
        "event_type",
        sa.Column("id", sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    values = ", ".join(f"('{m.value}')" for m in EventTypeEnumV1)
    op.execute(f"INSERT INTO event_type (name) VALUES {values}")
    op.add_column(
        "event",
        sa.Column("type_id", sa.SmallInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_event_type_id",
        "event",
        "event_type",
        ["type_id"],
        ["id"],
    )
    event_format.create(op.get_bind())
    op.add_column(
        "event",
        sa.Column(
            "format",
            event_format,
            nullable=False,
            server_default=EventFormatEnumV1.offline,
        ),
    )


def downgrade() -> None:
    op.drop_constraint("fk_event_type_id", "event", type_="foreignkey")
    op.drop_column("event", "type_id")
    op.drop_column("event", "format")
    op.drop_table("event_type")

    op.execute("DROP TYPE IF EXISTS event_format")
