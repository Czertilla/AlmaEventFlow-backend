from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from org.models.organization import OrganizationORM

if TYPE_CHECKING:
    pass


class UniversityORM(OrganizationORM):
    __tablename__ = "university"

    id: Mapped[UUID] = mapped_column(
        ForeignKey("organization.id", ondelete="CASCADE"), primary_key=True
    )

    __mapper_args__ = {
        "polymorphic_identity": "university",
    }
