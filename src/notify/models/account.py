from uuid import UUID
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin
from ._base import ModuleBase


class AccountORM(ModuleBase, Base, TimestampMixin, UUIDMixin):
    """Local projection of a user account. ``id`` equals the user id and comes
    from ``account.*`` events."""

    __tablename__ = "account"

    email: Mapped[str] = mapped_column(String(256))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    locale: Mapped[str | None] = mapped_column(String(16), default=None)
