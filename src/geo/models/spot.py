from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from geoalchemy2 import Geometry, WKBElement, WKTElement
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from geo.dto.point import PointDTO

if TYPE_CHECKING:
    from core.database.sqlalchemy.core import Base


def point_from_geometry(spot: WKBElement | WKTElement | None) -> PointDTO | None:
    if spot is None:
        return None
    if isinstance(spot, WKTElement):
        wkt = str(cast("Any", spot).data or "").strip()
        if wkt.upper().startswith("SRID="):
            _, wkt = wkt.split(";", 1)
            wkt = wkt.strip()
        if not wkt.upper().startswith("POINT"):
            raise ValueError(f"Expected POINT WKT, got: {wkt!r}")
    geom = cast("Any", to_shape(spot))
    if geom.geom_type != "Point":
        raise ValueError(f"Expected Point geometry, got: {geom.geom_type}")
    return PointDTO(lat=float(geom.y), lon=float(geom.x))


def spot_element(point: PointDTO | dict[str, float] | None) -> WKTElement | None:
    if not point:
        return None
    if isinstance(point, dict):
        lon, lat = point["lon"], point["lat"]
    else:
        lon, lat = point.lon, point.lat
    return WKTElement(f"POINT({lon} {lat})", srid=4326)


def spot_column():
    return mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=True))


class SpotMixin:
    @declared_attr
    def spot(cls: "Base") -> Mapped[UUID]:  # noqa: N805
        return spot_column()


class OptionalSpotMixin:
    @declared_attr
    def spot(cls: "Base") -> Mapped[WKBElement | None]:  # noqa: N805
        return spot_column()
