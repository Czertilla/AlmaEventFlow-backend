from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import UUIDMixin
from ._base import ModuleBase

if TYPE_CHECKING:
    from .user import UserORM
    from .refresh_token import RefreshTokenORM


class SessionORM(ModuleBase, Base, UUIDMixin):
    __tablename__ = "session"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    device_info: Mapped[str | None] = mapped_column(Text, default=None)
    ip_address: Mapped[str | None] = mapped_column(String(45), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    user: Mapped["UserORM"] = relationship()
    refresh_tokens: Mapped[list["RefreshTokenORM"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
