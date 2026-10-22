from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin

from ._base import ModuleBase


class UserSettingsORM(ModuleBase, Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_settings"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), unique=True
    )
    data: Mapped[dict[str, Any]] = mapped_column(default=dict)
    revision: Mapped[int] = mapped_column(default=0)
