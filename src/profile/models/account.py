from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin

from ._base import ModuleBase


class PersonAccountORM(ModuleBase, Base, TimestampMixin):
    __tablename__ = "person_account"

    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(unique=True)


class PersonAccountHistoryORM(ModuleBase, Base, UUIDMixin):
    __tablename__ = "person_account_history"

    user_id: Mapped[UUID] = mapped_column(index=True)
    old_person_id: Mapped[UUID | None] = mapped_column(index=True)
    new_person_id: Mapped[UUID | None] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[UUID | None]
    created_at: Mapped[datetime] = mapped_column(default=func.now())
