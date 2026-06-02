from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import UUIDMixin
from event.enum.priority import Priority
from ._base import ModuleBase

if TYPE_CHECKING:
    from .collective import CollectiveORM
    from .event import EventORM
    from .reward import RewardORM


class ParticipationORM(ModuleBase, Base, UUIDMixin):
    __tablename__ = "participation"

    collective_id: Mapped[UUID] = mapped_column(
        ForeignKey("collective.id", ondelete="CASCADE")
    )
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("event.id", ondelete="CASCADE")
    )
    priority_degree: Mapped[Priority | None] = mapped_column(
        Enum(Priority, name="event_priority")
    )

    collective: Mapped["CollectiveORM"] = relationship(
        foreign_keys=[collective_id]
    )
    event: Mapped["EventORM"] = relationship(back_populates="participations")
    rewards: Mapped[list["RewardORM"]] = relationship(
        back_populates="participation",
    )

    __table_args__ = (UniqueConstraint(collective_id, event_id),)
