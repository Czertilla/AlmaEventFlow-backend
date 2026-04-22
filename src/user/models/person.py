from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, relationship

from core.models.person import PersonAORM as Base
from ._base import ModuleBase

if TYPE_CHECKING:
    from .user import UserORM

class PersonORM(ModuleBase, Base):
    user: Mapped["UserORM"] = relationship(back_populates="person")