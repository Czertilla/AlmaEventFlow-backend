from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import UUIDMixin
from ._base import ModuleBase


if TYPE_CHECKING:
    from .participation import ParticipationORM


class RewardORM(ModuleBase, Base, UUIDMixin):
    __tablename__ = "reward"

    name: Mapped[str] = mapped_column(String(128))
    file_id: Mapped[UUID | None]
    participation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("participation.id", ondelete="SET NULL")
    )
    degree: Mapped[int | None] = mapped_column(SmallInteger)

    participation: Mapped["ParticipationORM"] = relationship(
        back_populates="rewards"
    )
