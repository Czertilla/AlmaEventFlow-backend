from typing import TYPE_CHECKING, Optional
from uuid import UUID
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.mixins.models import TimestampMixin
from core.models.organization import OrganizationPrincipalORM as Base
from ._base import ModuleBase

if TYPE_CHECKING:
    from .person import PersonORM
    from .address import AddressORM


class OrganizationORM(ModuleBase, Base, TimestampMixin):
    __tablename__ = "organization"

    acronym: Mapped[str | None] = mapped_column(String(16))

    address_id: Mapped[UUID | None] = mapped_column(ForeignKey("address.id"))

    address: Mapped[Optional["AddressORM"]] = relationship(
        foreign_keys=[address_id]
    )
    principal: Mapped[Optional["PersonORM"]] = relationship(
        foreign_keys=lambda: [OrganizationORM.principal_id],
        back_populates="principal_of",
    )

    __mapper_args__ = {
        "polymorphic_identity": "organization",
        "polymorphic_on": "type",
    }
