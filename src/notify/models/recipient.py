from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin
from ._base import ModuleBase


class NotificationRecipientORM(ModuleBase, Base, UUIDMixin, TimestampMixin):
    """A single user targeted by a notification. Parent of per-transport
    deliveries. ``user_id`` is a raw UUID with no FK on ``account``."""

    __tablename__ = "notification_recipient"
    __table_args__ = (
        UniqueConstraint(
            "notification_id",
            "user_id",
            name="uq_recipient_notification_user",
        ),
    )

    notification_id: Mapped[UUID] = mapped_column(
        ForeignKey("notification.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(index=True)
