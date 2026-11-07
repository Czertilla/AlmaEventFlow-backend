from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin

from ._base import ModuleBase


class NotificationOutboxORM(ModuleBase, Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'published', 'dead')",
            name="ck_notification_outbox_status",
        ),
        CheckConstraint(
            "person_id IS NOT NULL OR user_id IS NOT NULL",
            name="ck_notification_outbox_recipient",
        ),
        Index("ix_notification_outbox_status_due", "status", "next_attempt_at"),
    )

    person_id: Mapped[UUID | None]
    user_id: Mapped[UUID | None]
    category: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(1000))
    data: Mapped[dict[str, Any]] = mapped_column()
    status: Mapped[str] = mapped_column(String(16), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime]
    published_at: Mapped[datetime | None]
