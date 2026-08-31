from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.mixins.models import TimestampMixin
from core.models.location import LocationAORM as Base

from ._base import ModuleBase
from .spot import OptionalSpotMixin

if TYPE_CHECKING:
    from .address import AddressORM


class LocationORM(ModuleBase, Base, OptionalSpotMixin, TimestampMixin):
    """A location is anchored to exactly one of an address (an
    ``AddressORM`` row -- possibly with no name of its own, an
    "address-proxy" location) or its own coordinates. Never both, never
    neither -- enforced by ``ck_location_address_xor_spot`` below, not just
    at the API layer."""

    address_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("address.id", ondelete="SET NULL")
    )

    address: Mapped[Optional["AddressORM"]] = relationship(
        back_populates="locations"
    )

    __table_args__ = (
        CheckConstraint(
            "(address_id IS NOT NULL) != (spot IS NOT NULL)",
            name="ck_location_address_xor_spot",
        ),
    )
