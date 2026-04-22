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

    event: Mapped["EventORM"] = relationship(back_populates="stages")
