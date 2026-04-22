from datetime import date
from typing import TYPE_CHECKING, Optional
from uuid import UUID
from sqlalchemy import Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin
from ._base import ModuleBase

if TYPE_CHECKING:
    from .diet import DietORM
    from .organization import OrganizationORM
    from .passport import PassportORM
    from .person import PersonORM


class ProfileORM(ModuleBase, Base, TimestampMixin):
    __tablename__ = "profile"

    id: Mapped[UUID] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE"), primary_key=True
    )
    birthdate: Mapped[date | None] = mapped_column(Date)
    workplace_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organization.id", ondelete="SET NULL")
    )
    diet_id: Mapped[int | None] = mapped_column(ForeignKey("diet.id"))

    diet: Mapped[Optional["DietORM"]] = relationship(back_populates="profiles")
    workplace: Mapped[Optional["OrganizationORM"]] = relationship(
        foreign_keys=[]
    )
    person: Mapped["PersonORM"] = relationship(foreign_keys=[id])
    passports: Mapped[list["PassportORM"]] = relationship(
        back_populates="profile"
    )
