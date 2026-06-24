from typing import Any

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import (
    BigSerialMixin,
    TimestampMixin,
)
from core.enum.notify import OutboxStatus
from ._base import ModuleBase, enum_column


class OutboxEventORM(ModuleBase, Base, BigSerialMixin, TimestampMixin):
    """Transactional outbox row. Written in the same transaction as the
    deliveries it publishes; drained in id order by the outbox publisher. The
    payload is a self-describing transport batch (``TransportBatch``), so one
    outbox row maps to exactly one Kafka message carrying many deliveries."""

    __tablename__ = "outbox_event"
    __table_args__ = (Index("ix_outbox_status_id", "status", "id"),)

    topic: Mapped[str] = mapped_column(String(256))
    payload: Mapped[dict[str, Any]] = mapped_column()
    status: Mapped[OutboxStatus] = mapped_column(
        enum_column(OutboxStatus, "outbox_status"),
        default=OutboxStatus.pending,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
