from datetime import datetime
from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter
from geoalchemy2 import WKTElement
from sqlalchemy import func, select

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)
from core.dto.pagination import PageParams
from geo.models.address import AddressORM as Model
from geo.schema.point import Point
from geo.search import search_page, text_match


class AddressAlchemyRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model

    @staticmethod
    def dump_spot(data: dict):
        if "spot" not in data:
            return
        point = data.pop("spot")
        data["spot"] = (
            WKTElement(f"POINT({point['lon']} {point['lat']})", srid=4326)
            if point
            else None
        )

    def add_n_return(self, data, options=()):
        self.dump_spot(data)
        return super().add_n_return(data, options)

    def add_one(self, data):
        self.dump_spot(data)
        return super().add_one(data)

    def update_one(self, id, data, flush=False):
        self.dump_spot(data)
        return super().update_one(id, data, flush)

    def upsert(self, data, options=...):
        self.dump_spot(data)
        return super().upsert(data, options)

    def upsert_many(self, data, options=()):
        for item in data:
            self.dump_spot(item)
        return super().upsert_many(data, options)

    async def search(
        self,
        filter: Filter,
        pagination: PageParams,
        *,
        options=None,
        scope: list | None = None,
        near: Point | None = None,
    ) -> tuple[list[Model], int]:
        match = (
            text_match(filter.search, self.model.name_tsv, self.model.name)
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

    async def _search_near(
        self,
        filter: Filter,
        near: Point,
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
