from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin
from core.enum.notify import NotificationCategory
from ._base import ModuleBase, enum_column


class NotificationORM(ModuleBase, Base, UUIDMixin, TimestampMixin):
    """Logical notification persisted on ingest. ``event_id`` is the
    idempotency key: a second request with the same id is ignored."""

    __tablename__ = "notification"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_notification_event_id"),
    )

    event_id: Mapped[UUID] = mapped_column(index=True)
    category: Mapped[NotificationCategory] = mapped_column(
        enum_column(NotificationCategory, "notification_category")
    )
    title: Mapped[str] = mapped_column(String(512))
    body: Mapped[str] = mapped_column(String, default="")
    action_url: Mapped[str | None] = mapped_column(String(2048), default=None)
    data: Mapped[dict[str, Any]] = mapped_column(default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(default=None)
