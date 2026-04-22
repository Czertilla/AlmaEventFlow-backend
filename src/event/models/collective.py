from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from event.models.organization import OrganizationORM as Base

if TYPE_CHECKING:
    from .member import MemberORM


class CollectiveORM(Base):
    __tablename__ = "collective"

    id: Mapped[UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), primary_key=True
    )
    is_verified: Mapped[bool] = mapped_column(default=False)

    members: Mapped[list["MemberORM"]] = relationship(
        back_populates="collective"
    )
