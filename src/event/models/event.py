from typing import TYPE_CHECKING
import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import (
    SmallSerialMixin,
    UUIDMixin,
    TimestampMixin,
)
from ._base import ModuleBase

if TYPE_CHECKING:
    from .location import LocationORM
    from .stage import EventStageORM
    from .organization import OrganizationORM
    from .participation import ParticipationORM
    from .link import EventLinkORM


class EventStatusORM(ModuleBase, Base, SmallSerialMixin):
    __tablename__ = "event_status"

    name: Mapped[str] = mapped_column(String(64))

    events: Mapped[list["EventORM"]] = relationship(back_populates="status")


class EventORM(ModuleBase, Base, UUIDMixin, TimestampMixin):
    __tablename__ = "event"

    name: Mapped[str] = mapped_column(String(128))
    date: Mapped[datetime.date | None]
    description: Mapped[str | None] = mapped_column(String(1024))
    location_id: Mapped[UUID | None] = mapped_column(ForeignKey("location.id"))
    status_id: Mapped[int] = mapped_column(
        ForeignKey("event_status.id"), default=0
    )
    organizer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organization.id", ondelete="SET NULL")
    )

    location: Mapped[Optional["LocationORM"]] = relationship(
        foreign_keys=[location_id]
    )
    organizer: Mapped[Optional["OrganizationORM"]] = relationship(
        foreign_keys=[organizer_id]
    )
    status: Mapped[Optional["EventStatusORM"]] = relationship(
        back_populates="events"
    )
    links: Mapped[list["EventLinkORM"]] = relationship(back_populates="event")
    stages: Mapped[list["EventStageORM"]] = relationship(back_populates="event")
    participation: Mapped[list["ParticipationORM"]] = relationship(
        back_populates="event"
    )
