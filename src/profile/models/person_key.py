from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, LargeBinary, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin

from ._base import ModuleBase


class PersonKeyORM(ModuleBase, Base, TimestampMixin):
    __tablename__ = "person_key"
    __table_args__ = (Index("ix_person_key_key_ref", "key_ref"),)

    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE"), primary_key=True
    )
    wrapped_dek: Mapped[bytes | None] = mapped_column(LargeBinary)
    key_ref: Mapped[str | None] = mapped_column(String(300))
    dek_version: Mapped[int] = mapped_column(SmallInteger, default=1)
    rotated_at: Mapped[datetime | None]
    destroyed_at: Mapped[datetime | None]
