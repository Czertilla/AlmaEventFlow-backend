from typing import TYPE_CHECKING
from sqlalchemy import Computed, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.mixins.models import (
    TimestampMixin,
    UUIDMixin as AlchemyUUIMixin,
)
from core.database.sqlalchemy.types.pydantic import PydanticJSONB
from core.models.address import AddressAORM
from geo.models.spot import OptionalSpotMixin
from sqlalchemy.dialects.postgresql import TSVECTOR
from ._base import ModuleBase

from geo.schema.address import AddressFields

if TYPE_CHECKING:
    from .city import CityORM
    from .location import LocationORM


class AddressORM(
    ModuleBase, AddressAORM, AlchemyUUIMixin, OptionalSpotMixin, TimestampMixin
):
    __tablename__ = "address"

    name_tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed("""to_tsvector('simple', "name")""", persisted=True)
    )
    city_id: Mapped[int] = mapped_column(
        ForeignKey("city.id", ondelete="CASCADE")
    )
    parsed: Mapped[AddressFields | None] = mapped_column(
        PydanticJSONB(AddressFields)
    )

    city: Mapped["CityORM"] = relationship(foreign_keys=[city_id])

    locations: Mapped[list["LocationORM"]] = relationship(
        back_populates="address"
    )

    __table_args__ = (
        Index(
            "idx_spot_search_fts",
            name_tsv,
            postgresql_using="gin",
        ),
        Index(
            "ix_spot_search_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )
