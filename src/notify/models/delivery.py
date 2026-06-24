from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin
from core.enum.notify import DeliveryStatus, TransportTypeEnum
from ._base import ModuleBase, enum_column


class NotificationDeliveryORM(ModuleBase, Base, UUIDMixin, TimestampMixin):
    """One delivery attempt target: a ``(recipient, transport)`` pair, plus an
    optional ``client_id`` for client-bound transports (one row per endpoint)."""

    __tablename__ = "notification_delivery"

    notification_id: Mapped[UUID] = mapped_column(
        ForeignKey("notification.id", ondelete="CASCADE"), index=True
    )
    recipient_id: Mapped[UUID] = mapped_column(
        ForeignKey("notification_recipient.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(index=True)
    transport: Mapped[TransportTypeEnum] = mapped_column(
        enum_column(TransportTypeEnum, "transport_type")
    )
    client_id: Mapped[UUID | None] = mapped_column(default=None)
    status: Mapped[DeliveryStatus] = mapped_column(
        enum_column(DeliveryStatus, "delivery_status"),
        default=DeliveryStatus.pending,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        default=None, index=True
    )
    last_error: Mapped[str | None] = mapped_column(String(1024), default=None)
    provider_message_id: Mapped[str | None] = mapped_column(
        String(256), default=None
    )
