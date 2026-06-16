from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import ForeignKey, String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import UUIDMixin
from event.enum.link import EventLinkTypeEnumV1
from ._base import ModuleBase

if TYPE_CHECKING:
    from .event import EventORM


class EventLinkORM(ModuleBase, Base, UUIDMixin):
    __tablename__ = "event_link"

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("event.id", ondelete="CASCADE")
    )
    type: Mapped[EventLinkTypeEnumV1] = mapped_column(
        Enum(EventLinkTypeEnumV1, name="event_link_type")
    )
    name: Mapped[str | None]
    value: Mapped[str] = mapped_column(String(1024))

    event: Mapped["EventORM"] = relationship(back_populates="links")
