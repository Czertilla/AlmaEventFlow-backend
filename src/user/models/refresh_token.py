from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import UUIDMixin
from ._base import ModuleBase

if TYPE_CHECKING:
    from .session import SessionORM
    from .user import UserORM


class RefreshTokenORM(ModuleBase, Base, UUIDMixin):
    __tablename__ = "refresh_token"

    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("session.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_used: Mapped[bool] = mapped_column(default=False)
    is_revoked: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    user: Mapped["UserORM"] = relationship()
    session: Mapped["SessionORM"] = relationship(back_populates="refresh_tokens")
