"""encrypt the passport columns and keep a data key per person

Revision ID: b7d4e9a1c3f6
Revises: e8b2c4d6a913
Create Date: 2026-11-01 15:00:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "b7d4e9a1c3f6"
down_revision: str | None = "e8b2c4d6a913"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLAIN: tuple[tuple[str, sa.types.TypeEngine[Any], bool], ...] = (
    ("number", sa.String(length=32), False),
    ("issued_authority", sa.String(), True),
    ("issued_date", sa.Date(), True),
    ("expire_date", sa.Date(), False),
)


def _refuse_if_filled(action: str) -> None:
    filled = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM passport WHERE "
                + " OR ".join(f"{name} IS NOT NULL" for name, _, _ in PLAIN)
            )
        )
        .scalar_one()
    )
    if filled:
        raise RuntimeError(
            f"passport has {filled} rows with data: {action} would lose them. "
            "Nothing was changed; move the data by the expand, migrate, contract "
            "procedure of the runbook first."
        )


def upgrade() -> None:
    _refuse_if_filled("re-creating its columns as ciphertext")
    op.create_table(
        "person_key",
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("wrapped_dek", sa.LargeBinary(), nullable=True),
        sa.Column("key_ref", sa.String(length=300), nullable=True),
        sa.Column("dek_version", sa.SmallInteger(), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("destroyed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["person_id"], ["person.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("person_id"),
    )
    op.create_index("ix_person_key_key_ref", "person_key", ["key_ref"])
    for name, _, nullable in PLAIN:
        op.drop_column("passport", name)
        op.add_column("passport", sa.Column(name, sa.LargeBinary(), nullable=nullable))


def downgrade() -> None:
    _refuse_if_filled("returning its columns to plain text")
    for name, type_, nullable in PLAIN:
        op.drop_column("passport", name)
        op.add_column("passport", sa.Column(name, type_, nullable=nullable))
    op.drop_index("ix_person_key_key_ref", table_name="person_key")
    op.drop_table("person_key")
