"""one collective per group chat

Revision ID: 3c1d9b7a52e4
Revises: f584aa56dfe1
Create Date: 2026-10-06 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "3c1d9b7a52e4"
down_revision: str | None = "f584aa56dfe1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM tg.collective_chat AS chat
        USING (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY chat_id
                       ORDER BY coalesce(edited_at, created_at) DESC, id
                   ) AS position
            FROM tg.collective_chat
        ) AS ranked
        WHERE chat.id = ranked.id AND ranked.position > 1
        """
    )
    op.create_unique_constraint(
        "uq_collective_chat_chat_id",
        "collective_chat",
        ["chat_id"],
        schema="tg",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_collective_chat_chat_id",
        "collective_chat",
        schema="tg",
        type_="unique",
    )
