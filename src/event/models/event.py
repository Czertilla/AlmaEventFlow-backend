from typing import TYPE_CHECKING
import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import (
    SmallSerialMixin,
    UUIDMixin,
    TimestampMixin,
)
from event.enum.format import EventFormatEnumV1
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

    events: Mapped[list["EventORM"]] = relationship(back_populates="status_rel")


class EventLevelORM(ModuleBase, Base, SmallSerialMixin):
    __tablename__ = "event_level"

    name: Mapped[str] = mapped_column(String(64))

    events: Mapped[list["EventORM"]] = relationship(back_populates="level_rel")


class EventTypeORM(ModuleBase, Base, SmallSerialMixin):
    __tablename__ = "event_type"

    name: Mapped[str] = mapped_column(String(64))

    events: Mapped[list["EventORM"]] = relationship(back_populates="type_rel")


class EventORM(ModuleBase, Base, UUIDMixin, TimestampMixin):
    __tablename__ = "event"

    name: Mapped[str] = mapped_column(String(128))
    date: Mapped[datetime.date | None]
    description: Mapped[str | None] = mapped_column(String(1024))
    location_id: Mapped[UUID | None] = mapped_column(ForeignKey("location.id"))
    status_id: Mapped[int] = mapped_column(
        ForeignKey("event_status.id"), default=1
    )
    level_id: Mapped[int | None] = mapped_column(ForeignKey("event_level.id"))
    type_id: Mapped[int | None] = mapped_column(ForeignKey("event_type.id"))
    organizer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organization.id", ondelete="SET NULL")
    )
    format: Mapped[EventFormatEnumV1] = mapped_column(
        Enum(EventFormatEnumV1, name="event_format"),
        server_default=EventFormatEnumV1.offline,
    )

    location: Mapped[Optional["LocationORM"]] = relationship(
        foreign_keys=[location_id]
    )
    organizer: Mapped[Optional["OrganizationORM"]] = relationship(
        foreign_keys=[organizer_id]
    )
    status_rel: Mapped[Optional["EventStatusORM"]] = relationship(
        back_populates="events"
    )
    level_rel: Mapped[Optional["EventLevelORM"]] = relationship(
        back_populates="events"
    )
    type_rel: Mapped[Optional["EventTypeORM"]] = relationship(
        back_populates="events"
    )

    @property
    def status(self) -> str:
        if self.status_rel:
            return self.status_rel.name
        return "draft"

    @property
    def level(self) -> str | None:
        if self.level_rel:
            return self.level_rel.name

    @property
    def type(self) -> str | None:
        if self.type_rel:
            return self.type_rel.name

    links: Mapped[list["EventLinkORM"]] = relationship(back_populates="event")
    stages: Mapped[list["EventStageORM"]] = relationship(back_populates="event")
    participations: Mapped[list["ParticipationORM"]] = relationship(
        back_populates="event"
    )
