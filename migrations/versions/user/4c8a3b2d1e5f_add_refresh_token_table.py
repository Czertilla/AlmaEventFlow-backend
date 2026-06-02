"""add session table

Revision ID: 4c8a3b2d1e5f
Revises: 5cf59abf283f
Create Date: 2026-05-30 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4c8a3b2d1e5f"
down_revision: Union[str, None] = "5cf59abf283f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "is_revoked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_session_token_hash"), "session", ["token_hash"], unique=True
    )
    op.create_index(
        op.f("ix_session_user_id"), "session", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_session_is_revoked"), "session", ["is_revoked"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_session_token_hash"), table_name="session")
    op.drop_index(op.f("ix_session_user_id"), table_name="session")
    op.drop_index(op.f("ix_session_is_revoked"), table_name="session")
    op.drop_table("session")
