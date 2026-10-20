from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from org.models.organization import OrganizationORM

if TYPE_CHECKING:
    pass


class UniversityORM(OrganizationORM):
    __tablename__ = "university"

    id: Mapped[UUID] = mapped_column(  # pyright: ignore[reportIncompatibleVariableOverride]
        ForeignKey("organization.id", ondelete="CASCADE"), primary_key=True
    )

    __mapper_args__: ClassVar[dict[str, Any]] = {
        "polymorphic_identity": "university",
        "eager_defaults": True,
    }
