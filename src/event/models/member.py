from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import UUIDMixin
from ._base import ModuleBase

if TYPE_CHECKING:
    from .collective import CollectiveORM
    from .person import PersonORM
    from .role import RoleORM


class MemberRoleAssociation(ModuleBase, Base):
    __tablename__ = "member_role"

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("role.id", ondelete="CASCADE"), primary_key=True
    )
    member_id: Mapped[UUID] = mapped_column(
        ForeignKey("member.id", ondelete="CASCADE"), primary_key=True
    )


class MemberORM(ModuleBase, Base, UUIDMixin):
    __tablename__ = "member"
    __table_args__ = (UniqueConstraint("person_id", "collective_id"),)

    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE")
    )
    collective_id: Mapped[UUID] = mapped_column(
        ForeignKey("collective.id", ondelete="CASCADE")
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    collective: Mapped["CollectiveORM"] = relationship(back_populates="members")
    person: Mapped["PersonORM"] = relationship(foreign_keys=[person_id])
    roles: Mapped[list["RoleORM"]] = relationship(
        back_populates="members", secondary="member_role"
    )
