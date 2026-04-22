from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from org.models.organization import OrganizationORM

if TYPE_CHECKING:
    pass


class CollectiveORM(OrganizationORM):
    __tablename__ = "collective"

    id: Mapped[UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), primary_key=True
    )
    university_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("university.id", ondelete="SET NULL")
    )

    __mapper_args__ = {
        "polymorphic_identity": "collective",
    }
