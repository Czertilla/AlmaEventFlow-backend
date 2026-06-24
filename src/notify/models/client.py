from typing import Any
from uuid import UUID
from sqlalchemy import Boolean, Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin
from core.enum.notify import TransportTypeEnum
from ._base import ModuleBase


class ClientORM(ModuleBase, Base, UUIDMixin, TimestampMixin):
    """Self-registered delivery endpoint. Several clients per
    ``(user_id, transport)`` are allowed (e.g. different browsers). ``endpoint``
    is the transport-natural key; ``payload`` holds transport-specific data
    (web-push ``p256dh``/``auth`` keys)."""

    __tablename__ = "client"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "transport",
            "endpoint",
            name="uq_client_user_transport_endpoint",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(index=True)
    transport: Mapped[TransportTypeEnum] = mapped_column(
        Enum(
            TransportTypeEnum,
            name="transport_type",
            values_callable=lambda enum: [member.value for member in enum],
        )
    )
    endpoint: Mapped[str] = mapped_column(String(512))
    label: Mapped[str | None] = mapped_column(String(256), default=None)
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
