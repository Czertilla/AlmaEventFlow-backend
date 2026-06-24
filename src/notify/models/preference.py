from uuid import UUID
from sqlalchemy import Boolean, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin
from core.enum.notify import TransportTypeEnum
from ._base import ModuleBase


class PreferenceORM(ModuleBase, Base, UUIDMixin, TimestampMixin):
    """Per-transport switch for a user. A missing row means the default (email
    enabled, others disabled). ``user_id`` has no FK on ``account``."""

    __tablename__ = "preference"

    user_id: Mapped[UUID] = mapped_column(index=True)
    transport: Mapped[TransportTypeEnum] = mapped_column(
        Enum(
            TransportTypeEnum,
            name="transport_type",
            values_callable=lambda enum: [member.value for member in enum],
        )
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "transport", name="uq_preference_user_transport"
        ),
    )
