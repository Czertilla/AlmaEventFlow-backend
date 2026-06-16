from typing import TYPE_CHECKING
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin
from ._base import ModuleBase

if TYPE_CHECKING:
    from .profile import ProfileORM


class NameVariantORM(ModuleBase, Base):
    __tablename__ = "name_variant"

    id: Mapped[UUID] = mapped_column(
        ForeignKey("passport.id", ondelete="CASCADE"), primary_key=True
    )
    surname: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(128))
    patronymic: Mapped[Optional[str]] = mapped_column(String(128))
    passport: Mapped["PassportORM"] = relationship(
        back_populates="name_variant"
    )


class PassportORM(ModuleBase, Base, UUIDMixin, TimestampMixin):
    __tablename__ = "passport"

    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profile.id", ondelete="CASCADE")
    )
    number: Mapped[str] = mapped_column(String(32))
    expire_date: Mapped[date]
    is_foreign: Mapped[bool]
    issued_date: Mapped[date | None]
    issued_authority: Mapped[str | None]

    name_variant: Mapped[Optional["NameVariantORM"]] = relationship(
        back_populates="passport"
    )
    profile: Mapped["ProfileORM"] = relationship(back_populates="passports")
