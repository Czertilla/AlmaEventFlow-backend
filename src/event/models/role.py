from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import String, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import UUIDMixin
from ._base import ModuleBase

if TYPE_CHECKING:
    from .member import MemberORM


class RoleORM(ModuleBase, Base, UUIDMixin):
    __tablename__ = "role"

    collective_id: Mapped[UUID] = mapped_column(
        ForeignKey("collective.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(64))

    members: Mapped[list["MemberORM"]] = relationship(
        back_populates="roles", secondary="member_role"
    )

    __table_args__ = (
        Index("idx_collective_role", "collective_id", "name", unique=True),
    )
