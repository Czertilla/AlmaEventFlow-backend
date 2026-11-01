from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin

from ._base import ModuleBase


class PersonFieldVisibilityORM(ModuleBase, Base, TimestampMixin):
    __tablename__ = "person_field_visibility"
    __table_args__ = (
        CheckConstraint(
            "audience IN ('private', 'context', 'all_users')",
            name="ck_person_field_visibility_audience",
        ),
    )

    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE"), primary_key=True
    )
    field_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    audience: Mapped[str] = mapped_column(String(16))


class PersonFieldVisibilityHistoryORM(ModuleBase, Base, UUIDMixin):
    __tablename__ = "person_field_visibility_history"
    __table_args__ = (
        CheckConstraint(
            "source IN ('owner', 'admin')",
            name="ck_person_field_visibility_history_source",
        ),
        Index(
            "ix_person_field_visibility_history_person_created",
            "person_id",
            "created_at",
        ),
    )

    person_id: Mapped[UUID]
    field_key: Mapped[str] = mapped_column(String(64))
    old_audience: Mapped[str | None] = mapped_column(String(16))
    new_audience: Mapped[str | None] = mapped_column(String(16))
    actor_user_id: Mapped[UUID]
    source: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
