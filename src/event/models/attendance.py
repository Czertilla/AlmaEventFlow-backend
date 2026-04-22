from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin
from ._base import ModuleBase

if TYPE_CHECKING:
    from .member import MemberORM
    from .participation import ParticipationORM


class AttendanceORM(ModuleBase, Base, UUIDMixin, TimestampMixin):
    __tablename__ = "attendance"

    member_id: Mapped[UUID] = mapped_column(
        ForeignKey("member.id", ondelete="CASCADE")
    )
    participation_id: Mapped[UUID] = mapped_column(
        ForeignKey("participation.id", ondelete="CASCADE")
    )
    is_attended: Mapped[bool | None]
    is_verified: Mapped[bool] = mapped_column(default=False)
    comment: Mapped[str | None] = mapped_column(String(512))

    member: Mapped["MemberORM"] = relationship(foreign_keys=[member_id])
    participation: Mapped["ParticipationORM"] = relationship(
        foreign_keys=[participation_id]
    )

    __table_args__ = (UniqueConstraint(member_id, participation_id),)
