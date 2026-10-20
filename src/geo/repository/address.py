from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter
from geoalchemy2 import WKTElement
from sqlalchemy import (
    Boolean,
    ColumnElement,
    Select,
    and_,
    func,
    literal_column,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.base import ExecutableOption

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)
from core.dto.pagination import PageParams
from geo.dto.point import PointDTO
from geo.identity import AddressKey, box_around, stored_key
from geo.locality import compose_locality
from geo.models.address import ADDRESS_SEARCH_TEXT
from geo.models.address import AddressORM as Model
from geo.models.city import CityORM
from geo.models.country import CountryORM
from geo.models.region import RegionORM
from geo.models.spot import spot_element
from geo.search import (
    distance_m,
    point_element,
    search_page,
    search_ranked,
    text_match,
)


@dataclass(frozen=True, slots=True)
class Neighbour:
    id: UUID
    city_id: int
    source: str | None
    key: AddressKey
    lat: float
    lon: float


@dataclass(frozen=True, slots=True)
class Stale:
    id: UUID
    city_id: int
    name: str
    key: AddressKey
    city: str
    lat: float
    lon: float
    synced_at: datetime
    attached: bool
    """A location points at the address, so it must not be deleted."""


class AddressAlchemyRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self._localities: dict[int, str] = {}

    @staticmethod
    def dump_spot(data: dict[str, Any]):
        if "spot" not in data:
            return
        data["spot"] = spot_element(data.pop("spot"))

    async def locality_of(self, city_id: int) -> str:
        if city_id not in self._localities:
            stmt = (
                select(CityORM.name, RegionORM.name, CountryORM.name)
                .join(RegionORM, RegionORM.id == CityORM.region_id)
                .join(CountryORM, CountryORM.id == RegionORM.country_id)
                .where(CityORM.id == city_id)
            )
            row = (await self.execute(stmt)).one_or_none()
            self._localities[city_id] = compose_locality(*row) if row else ""
        return self._localities[city_id]

    async def _prepare(self, data: dict[str, Any]) -> None:
        self.dump_spot(data)
        if data.get("city_id") is not None and "locality" not in data:
            data["locality"] = await self.locality_of(data["city_id"])

    async def add_n_return(
        self, data: dict[str, Any], options: tuple[ExecutableOption, ...] = ()
    ) -> Model:
        await self._prepare(data)
        return await super().add_n_return(data, options)

    async def add_one(self, data: dict[str, Any]) -> None:
        await self._prepare(data)
        return await super().add_one(data)

    async def update_one(
        self, id: UUID, data: dict[str, Any], flush: bool = False
    ) -> Model | None:
        await self._prepare(data)
        return await super().update_one(id, data, flush)

    async def upsert(
        self, data: dict[str, Any], options: tuple[ExecutableOption, ...] = ()
    ) -> Model | None:
        await self._prepare(data)
        return await super().upsert(data, options)

    async def upsert_many(
        self,
        data: list[dict[str, Any]],
        options: tuple[ExecutableOption, ...] = (),
    ):
        for item in data:
            await self._prepare(item)
        return await super().upsert_many(data, options)

    async def search(
        self,
        filter: Filter,
        pagination: PageParams,
        *,
        options: Sequence[ExecutableOption] | None = None,
        scope: list[ColumnElement[bool]] | None = None,
        near: PointDTO | None = None,
    ) -> tuple[Iterable[Model], int]:
        match = (
            text_match(
                filter.search,
                self.model.search_tsv,
                ADDRESS_SEARCH_TEXT,
                self.model.name,
            )
            if filter.search
            else None
        )
        if match is None:
            if near is not None:
                return await self._search_near(
                    filter, near, pagination, options=options, scope=scope
                )
            return await super().search(
                filter, pagination, options=options, scope=scope
            )

        plain = filter.model_copy(update={"search": None})

        def build(predicate):
            base = plain.filter(select(self.model).where(predicate))
            return base.where(*scope) if scope else base

        return await search_page(
            self,
            build,
            match,
            pagination,
            tie_break=(self.model.name, self.model.id),
            options=options,
        )

    async def search_ranked(
        self,
        query: str,
        limit: int,
        *,
        city_id: int | None = None,
        near: PointDTO | None = None,
    ) -> list[tuple[Model, float]]:
        match = text_match(
            query, self.model.search_tsv, ADDRESS_SEARCH_TEXT, self.model.name
        )
        if match is None:
            return []

        def build(predicate: ColumnElement[bool]) -> Select[Any]:
            base = select(self.model).where(predicate)
            if city_id is not None:
                base = base.where(self.model.city_id == city_id)
            return base

        return await search_ranked(
            self,
            build,
            match,
            limit,
            tie_break=(self.model.name, self.model.id),
            near=near,
            spot=self.model.spot,
            key=self.model.id,
        )

    async def nearest(
        self, near: PointDTO, limit: int, *, city_id: int | None = None
    ) -> list[tuple[Model, float]]:
        meters = distance_m(self.model.spot, near)
        stmt = (
            select(self.model, meters.label("meters"))
            .where(self.model.spot.is_not(None))
            .order_by(self.model.spot.op("<->")(point_element(near)))
            .limit(limit)
        )
        if city_id is not None:
            stmt = stmt.where(self.model.city_id == city_id)
        return [(row[0], float(row[1])) for row in (await self.execute(stmt)).all()]

    async def save_found(
        self, rows: list[dict[str, Any]]
    ) -> tuple[list[UUID], list[UUID]]:
        """A new row is inserted, a row of the same ``source`` is refreshed, a row
        of any other source (or a manual one) keeps its data. Ids must be unique.

        Returns the ids created and the ids refreshed."""
        if not rows:
            return [], []
        for row in rows:
            await self._prepare(row)
        stmt = insert(self.model).values(rows)
        incoming = stmt.excluded
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "name": incoming["name"],
                "spot": incoming["spot"],
                "parsed": incoming["parsed"],
                "source_id": incoming["source_id"],
                "synced_at": incoming["synced_at"],
                "edited_at": func.now(),
            },
            where=self.model.source == incoming["source"],
        ).returning(
            self.model.id, literal_column("(xmax = 0)", Boolean).label("inserted")
        )
        created: list[UUID] = []
        refreshed: list[UUID] = []
        for row_id, inserted in (await self.execute(stmt)).all():
            (created if inserted else refreshed).append(row_id)
        return created, refreshed

    async def neighbours(
        self, points: Sequence[tuple[float, float]], radius_m: float
    ) -> list[Neighbour]:
        """Stored addresses in the square around any of the ``(lat, lon)`` points."""
        if not points:
            return []
        boxes = [
            self.model.spot.op("&&")(
                func.ST_MakeEnvelope(west, south, east, north, 4326)
            )
            for south, west, north, east in (
                box_around(lat, lon, radius_m) for lat, lon in points
            )
        ]
        stmt = select(
            self.model.id,
            self.model.city_id,
            self.model.source,
            self.model.name,
            self.model.parsed,
            func.ST_Y(self.model.spot),
            func.ST_X(self.model.spot),
        ).where(or_(*boxes))
        return [
            Neighbour(
                id=row[0],
                city_id=row[1],
                source=row[2],
                key=stored_key(row[3], row[4]),
                lat=float(row[5]),
                lon=float(row[6]),
            )
            for row in (await self.execute(stmt)).all()
        ]

    async def stale_found(
        self,
        source: str,
        before: datetime,
        limit: int,
        after: tuple[datetime, UUID] | None = None,
    ) -> list[Stale]:
        """Rows of ``source`` last confirmed before ``before``, oldest first."""
        stmt = (
            select(
                self.model.id,
                self.model.city_id,
                self.model.name,
                self.model.parsed,
                CityORM.name,
                func.ST_Y(self.model.spot),
                func.ST_X(self.model.spot),
                self.model.synced_at,
                self.model.locations.any(),
            )
            .join(CityORM, CityORM.id == self.model.city_id)
            .where(
                self.model.source == source,
                self.model.spot.is_not(None),
                self.model.synced_at < before,
            )
            .order_by(self.model.synced_at, self.model.id)
            .limit(limit)
        )
        if after is not None:
            seen_at, seen_id = after
            stmt = stmt.where(
                or_(
                    self.model.synced_at > seen_at,
                    and_(self.model.synced_at == seen_at, self.model.id > seen_id),
                )
            )
        return [
            Stale(
                id=row[0],
                city_id=row[1],
                name=row[2],
                key=stored_key(row[2], row[3]),
                city=row[4],
                lat=float(row[5]),
                lon=float(row[6]),
                synced_at=row[7],
                attached=bool(row[8]),
            )
            for row in (await self.execute(stmt)).all()
        ]

    async def by_ids(self, ids: list[UUID]) -> list[Model]:
        if not ids:
            return []
        stmt = select(self.model).where(self.model.id.in_(ids))
        return list((await self.execute(stmt)).unique().scalars())

    async def _search_near(
        self,
        filter: Filter,
        near: PointDTO,
        pagination: PageParams,
        *,
        options=None,
        scope: list | None = None,
    ) -> tuple[list[Model], int]:
        """No search text -- order by distance from ``near`` (KNN via the
        GiST index on ``spot``) instead of ``filter``'s default ordering."""
        point = WKTElement(f"POINT({near.lon} {near.lat})", srid=4326)
        base = filter.filter(
            select(self.model).where(self.model.spot.isnot(None))
        )
        if scope:
            base = base.where(*scope)

        total = (
            await self.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        if not total:
            return [], 0

        stmt = base.order_by(self.model.spot.op("<->")(point)).limit(
            pagination.limit
        ).offset(pagination.offset)
        if options:
            stmt = stmt.options(*options)
        return (await self.execute(stmt)).unique().scalars(), total

    async def search_in_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        pagination: PageParams,
    ) -> tuple[list[Model], int]:
        """PostGIS bounding-box (``&&``) query against ``ST_MakeEnvelope`` --
        index-only, exactly what the GIST spatial index on ``spot`` exists
        for. Rows with no ``spot`` are excluded by ordinary SQL NULL
        semantics (``&&`` against NULL is NULL, never true), no extra
        filter needed."""
        envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        base = select(self.model).where(self.model.spot.op("&&")(envelope))

        total = (
            await self.execute(
                select(func.count()).select_from(base.subquery())
            )
        ).scalar_one()
        if not total:
            return [], 0

        stmt = base.limit(pagination.limit).offset(pagination.offset)
        return (await self.execute(stmt)).unique().scalars(), total

    async def stale_deletable_ids(
        self, city_id: int, source: str, before: datetime
    ) -> list[UUID]:
        """Rows from ``source`` in ``city_id`` a sync run hasn't touched
        since ``before`` -- excluding any address a location still points
        at, so a re-sync never deletes something a user actually attached
        to an event just because it dropped out of upstream data."""
        stmt = select(self.model.id).where(
            self.model.city_id == city_id,
            self.model.source == source,
            self.model.synced_at < before,
            ~self.model.locations.any(),
        )
        return list((await self.execute(stmt)).scalars())
