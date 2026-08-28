from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import UUIDMixin

from ._base import ModuleBase

if TYPE_CHECKING:
    from .event import EventORM


class EventStageORM(ModuleBase, Base, UUIDMixin):
    __tablename__ = "event_stage"

    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("event.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(32))
    start_at: Mapped[datetime]
    end_at: Mapped[datetime | None]
    description: Mapped[str | None] = mapped_column(String(1024))
    timezone: Mapped[str | None] = mapped_column(String(64), default=None)
    """IANA zone name (e.g. ``Europe/Moscow``) of the client that created this
    stage. ``start_at``/``end_at`` are stored as absolute UTC instants (lossless
    for every consumer), but the *original* zone is otherwise unrecoverable --
    this is what lets a display that must pick one fixed zone (the Telegram
    bot's plain-text messages) show the time the creator actually meant,
    instead of the DB session's zone or the viewer's own."""

    event: Mapped["EventORM"] = relationship(back_populates="stages")
