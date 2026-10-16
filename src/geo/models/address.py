from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Computed,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.mixins.models import (
    TimestampMixin,
)
from core.database.sqlalchemy.mixins.models import (
    UUIDMixin as AlchemyUUIMixin,
)
from core.database.sqlalchemy.types.pydantic import PydanticJSONB
from core.models.address import AddressAORM
from geo.dto.address import AddressFieldsDTO
from geo.models.spot import OptionalSpotMixin

from ._base import ModuleBase

if TYPE_CHECKING:
    from .city import CityORM
    from .location import LocationORM


class AddressORM(
    ModuleBase, AddressAORM, AlchemyUUIMixin, OptionalSpotMixin, TimestampMixin
):
    __tablename__ = "address"

    locality: Mapped[str] = mapped_column(String(512), server_default="")
    """Written by ``AddressAlchemyRepo`` from the city, never by callers."""
    search_tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('russian', \"name\"), 'A') || "
            "setweight(to_tsvector('russian', \"locality\"), 'C')",
            persisted=True,
        ),
    )
    city_id: Mapped[int] = mapped_column(
        ForeignKey("city.id", ondelete="CASCADE")
    )
    parsed: Mapped[AddressFieldsDTO | None] = mapped_column(
        PydanticJSONB(AddressFieldsDTO)
    )
    source: Mapped[str | None] = mapped_column(String(32))
    """Where this row came from, e.g. ``"osm"`` -- ``NULL`` for a row created
    manually through the API. Lets a re-sync tell its own rows apart from
    ones it must never touch."""
    source_id: Mapped[str | None] = mapped_column(String(255))
    """Stable id within ``source`` -- provenance only, not used as this
    row's own id (see ``bootstrap.run._address_id``)."""
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """``NULL`` for a manually-created row, by design -- no server default,
    or it would look "synced" and become eligible for pruning. Explicit
    ``timezone=True``: ``type_annotation_map``'s ``datetime`` entry doesn't
    actually apply here (also affects ``TimestampMixin``, dormant there)."""

    city: Mapped["CityORM"] = relationship(foreign_keys=[city_id])

    locations: Mapped[list["LocationORM"]] = relationship(
        back_populates="address"
    )

    __table_args__ = (
        Index("ix_address_search_tsv", search_tsv, postgresql_using="gin"),
        Index(
            "ix_spot_search_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index("ix_address_source_sync", "source", "city_id", "synced_at"),
    )


ADDRESS_SEARCH_TEXT = AddressORM.name + " " + AddressORM.locality
"""What trigram scores rank: the address and its place line."""
