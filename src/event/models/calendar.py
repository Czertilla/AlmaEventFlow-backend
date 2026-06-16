import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import SmallSerialMixin, UUIDMixin
from ._base import ModuleBase


class CalendarSubscriptionTypeORM(ModuleBase, Base, SmallSerialMixin):
    __tablename__ = "calendar_subscription_type"

    name: Mapped[str] = mapped_column(String(64))

    subscriptions: Mapped[list["CalendarSubscriptionORM"]] = relationship(
        back_populates="type_rel"
    )


class CalendarSubscriptionORM(ModuleBase, Base, UUIDMixin):
    __tablename__ = "calendar_subscription"

    owner_user_id: Mapped[UUID]
    person_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("person.id", ondelete="NO ACTION")
    )
    collective_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("collective.id", ondelete="NO ACTION")
    )
    type_id: Mapped[int] = mapped_column(
        ForeignKey("calendar_subscription_type.id")
    )
    title: Mapped[str] = mapped_column(String(255))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_accessed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    type_rel: Mapped[Optional["CalendarSubscriptionTypeORM"]] = relationship(
        back_populates="subscriptions"
    )

    @property
    def type(self) -> str | None:
        if self.type_rel:
            return self.type_rel.name
        return None

    __table_args__ = (
        Index("ix_calendar_subscription_owner", "owner_user_id"),
    )


class CalendarChangeLogORM(ModuleBase, Base, UUIDMixin):
    """Append-only snapshot of event removals.

    Intentionally holds no foreign keys: a row outlives the event/participation
    it describes so that principal calendars can keep emitting a cancellation
    after the source rows are physically deleted.
    """

    __tablename__ = "calendar_change_log"

    change_type: Mapped[str] = mapped_column(String(32))
    event_id: Mapped[UUID]
    collective_id: Mapped[UUID]
    participation_id: Mapped[UUID | None]
    occurred_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )

    event_name: Mapped[str] = mapped_column(String(128))
    event_date: Mapped[datetime.date | None] = mapped_column(Date)

    __table_args__ = (
        Index(
            "ix_calendar_change_log_collective_time",
            "collective_id",
            "occurred_at",
        ),
    )
