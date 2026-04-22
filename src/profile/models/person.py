from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, relationship
from core.database.sqlalchemy.mixins.models import TimestampMixin

from core.models.person import PersonBaseORM
from ._base import ModuleBase

if TYPE_CHECKING:
    from .contact import ContactORM


class PersonORM(ModuleBase, PersonBaseORM, TimestampMixin):
    contacts: Mapped[list["ContactORM"]] = relationship(
        back_populates="person", cascade="delete-orphan, all"
    )
