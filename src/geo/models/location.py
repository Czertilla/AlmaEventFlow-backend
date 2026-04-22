from typing import TYPE_CHECKING, Optional
from uuid import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column

from core.database.sqlalchemy.mixins.models import TimestampMixin
from core.models.location import LocationAORM as Base
from ._base import ModuleBase

from .spot import SpotMixin

if TYPE_CHECKING:
    from .address import AddressORM


class LocationORM(ModuleBase, Base, SpotMixin, TimestampMixin):
    address_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("address.id", ondelete="SET NULL")
    )

    address: Mapped[Optional["AddressORM"]] = relationship(
        back_populates="locations"
    )
