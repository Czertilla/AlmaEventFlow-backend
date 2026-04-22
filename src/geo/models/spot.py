from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy.orm import Mapped, mapped_column, declared_attr
from geoalchemy2 import Geometry, WKBElement

if TYPE_CHECKING:
    from core.database.sqlalchemy.core import Base


def spot_column():
    return mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True)
    )


class SpotMixin:
    @declared_attr
    def spot(cls: "Base") -> Mapped[UUID]:
        return spot_column()


class OptionalSpotMixin:
    @declared_attr
    def spot(cls: "Base") -> Mapped[WKBElement | None]:
        return spot_column()
