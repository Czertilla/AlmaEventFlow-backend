from typing import Any
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    CompoundSelect,
    Float,
    Select,
    String,
    Uuid,
    desc,
    func,
    literal_column,
    or_,
    select,
    union_all,
)
from sqlalchemy.orm import aliased

from core.database.sqlalchemy.core import SQLAlchemyRepository
from geo.dto.map import MapClusterDTO, MapEntityDTO, MapQueryDTO, MapViewDTO
from geo.models.address import AddressORM
from geo.models.location import LocationORM
from geo.search import Expression
from geo.service.viewport import (
    MAX_CLUSTER_ZOOM,
    MAX_MERCATOR_LAT,
    bbox_ranges,
    world_px,
)

Feature = MapEntityDTO | MapClusterDTO


def _in_window(spot: Expression, query: MapQueryDTO) -> ColumnElement[bool]:
    return or_(
        *(
            spot.op("&&")(
                func.ST_MakeEnvelope(west, query.south, east, query.north, 4326)
            )
            for west, east in bbox_ranges(query.west, query.east)
        )
    )


class MapRepo(SQLAlchemyRepository[AddressORM]):
    model = AddressORM

    @staticmethod
    def _points(query: MapQueryDTO, *, labelled: bool) -> CompoundSelect[Any] | None:
        """An unnamed location only stands for its address, so it is left out."""
        parts: list[Select[Any]] = []
        if "address" in query.kinds:
            columns: list[Any] = [
                literal_column("'address'", String).label("kind"),
                AddressORM.id.label("id"),
                AddressORM.spot.label("spot"),
            ]
            if labelled:
                columns += [
                    AddressORM.name.label("name"),
                    AddressORM.locality.label("locality"),
                ]
            parts.append(select(*columns).where(_in_window(AddressORM.spot, query)))
        if "location" in query.kinds:
            anchor = aliased(AddressORM)
            spot = func.coalesce(LocationORM.spot, anchor.spot)
            columns = [
                literal_column("'location'", String).label("kind"),
                LocationORM.id.label("id"),
                spot.label("spot"),
            ]
            if labelled:
                columns += [
                    LocationORM.name.label("name"),
                    func.coalesce(anchor.locality, "").label("locality"),
                ]
            parts.append(
                select(*columns)
                .select_from(LocationORM)
                .outerjoin(anchor, anchor.id == LocationORM.address_id)
                .where(LocationORM.name.is_not(None), _in_window(spot, query))
            )
        return union_all(*parts) if parts else None

    async def view(self, query: MapQueryDTO) -> MapViewDTO:
        if query.zoom >= MAX_CLUSTER_ZOOM:
            return await self._places(query)
        return await self._clusters(query)

    async def _clusters(self, query: MapQueryDTO) -> MapViewDTO:
        union = self._points(query, labelled=False)
        if union is None:
            return MapViewDTO([], 0, False)
        points = union.subquery("points")
        lon: ColumnElement[float] = func.ST_X(points.c.spot, type_=Float)
        lat: ColumnElement[float] = func.ST_Y(points.c.spot, type_=Float)
        phi = func.radians(
            func.least(MAX_MERCATOR_LAT, func.greatest(-MAX_MERCATOR_LAT, lat))
        )
        scale = world_px(query.zoom) / query.radius_px
        column = func.floor((lon + 180) / 360 * scale)
        row = func.floor(
            (1 - func.ln(func.tan(phi) + 1 / func.cos(phi)) / func.pi()) / 2 * scale
        )
        count = func.count()
        any_id: ColumnElement[UUID] = func.any_value(points.c.id, type_=Uuid)
        stmt = (
            select(
                count.label("n"),
                func.count().filter(points.c.kind == "address").label("addresses"),
                func.count().filter(points.c.kind == "location").label("locations"),
                func.avg(lon).label("lon"),
                func.avg(lat).label("lat"),
                func.min(lon).label("west"),
                func.min(lat).label("south"),
                func.max(lon).label("east"),
                func.max(lat).label("north"),
                func.any_value(points.c.kind, type_=String).label("kind"),
                any_id.label("id"),
                func.sum(count).over().label("matched"),
                func.count().over().label("cells"),
            )
            .group_by(column, row)
            .order_by(desc("n"), column, row)
            .limit(query.limit)
        )
        rows = (await self.execute(stmt)).all()
        singles: dict[str, list[UUID]] = {"address": [], "location": []}
        for item in rows:
            if item.n == 1:
                singles[item.kind].append(item.id)
        labels = await self._labels(singles)
        features: list[Feature] = []
        for item in rows:
            if item.n == 1:
                name, locality = labels.get(item.id, ("", ""))
                features.append(
                    MapEntityDTO(
                        kind=item.kind,
                        id=item.id,
                        lat=float(item.lat),
                        lon=float(item.lon),
                        name=name,
                        locality=locality,
                    )
                )
            else:
                features.append(
                    MapClusterDTO(
                        lat=float(item.lat),
                        lon=float(item.lon),
                        count=item.n,
                        addresses=item.addresses,
                        locations=item.locations,
                        west=item.west,
                        south=item.south,
                        east=item.east,
                        north=item.north,
                    )
                )
        cells = rows[0].cells if rows else 0
        matched = int(rows[0].matched) if rows else 0
        return MapViewDTO(features, matched, cells > len(rows))

    async def _labels(self, ids: dict[str, list[UUID]]) -> dict[UUID, tuple[str, str]]:
        labels: dict[UUID, tuple[str, str]] = {}
        if ids["address"]:
            stmt = select(AddressORM.id, AddressORM.name, AddressORM.locality).where(
                AddressORM.id.in_(ids["address"])
            )
            for item in (await self.execute(stmt)).all():
                labels[item.id] = (item.name, item.locality)
        if ids["location"]:
            anchor = aliased(AddressORM)
            stmt = (
                select(
                    LocationORM.id,
                    LocationORM.name,
                    func.coalesce(anchor.locality, "").label("locality"),
                )
                .outerjoin(anchor, anchor.id == LocationORM.address_id)
                .where(LocationORM.id.in_(ids["location"]))
            )
            for item in (await self.execute(stmt)).all():
                labels[item.id] = (item.name or "", item.locality)
        return labels

    async def _places(self, query: MapQueryDTO) -> MapViewDTO:
        union = self._points(query, labelled=True)
        if union is None:
            return MapViewDTO([], 0, False)
        points = union.subquery("points")
        lon: ColumnElement[float] = func.ST_X(points.c.spot, type_=Float)
        lat: ColumnElement[float] = func.ST_Y(points.c.spot, type_=Float)
        stmt = (
            select(
                points.c.kind,
                points.c.id,
                points.c.name,
                points.c.locality,
                lon.label("lon"),
                lat.label("lat"),
                func.count().over().label("matched"),
            )
            .order_by(points.c.id)
            .limit(query.limit)
        )
        rows = (await self.execute(stmt)).all()
        features: list[Feature] = [
            MapEntityDTO(
                kind=item.kind,
                id=item.id,
                lat=float(item.lat),
                lon=float(item.lon),
                name=item.name,
                locality=item.locality,
            )
            for item in rows
        ]
        matched = int(rows[0].matched) if rows else 0
        return MapViewDTO(features, matched, matched > len(rows))
