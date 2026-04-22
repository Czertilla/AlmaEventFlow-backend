from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import SerialMixin
from ._base import ModuleBase

if TYPE_CHECKING:
    from .profile import ProfileORM


class DietORM(ModuleBase, Base, SerialMixin):
    __tablename__ = "diet"

    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str | None] = mapped_column(String(512))

    profiles: Mapped[list["ProfileORM"]] = relationship(back_populates="diet")
