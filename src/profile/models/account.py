from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin

from ._base import ModuleBase


class PersonAccountORM(ModuleBase, Base, TimestampMixin):
    __tablename__ = "person_account"

    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(unique=True)
