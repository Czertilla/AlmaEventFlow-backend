from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter
from geoalchemy2 import WKTElement
from sqlalchemy import func, or_, select

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)
from core.schema.pagination import SPageParam
from geo.models.address import AddressORM as Model


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
        pagination: SPageParam,
        *,
        options=None,
        scope: list | None = None,
    ) -> tuple[list[Model], int]:
        """Free-text ``filter.search`` bypasses the generic ILIKE-based
        search fastapi_filter would otherwise build, in favor of the
        tsvector/trigram columns already provisioned on this table
        (``name_tsv`` GIN index, ``name`` trigram GIN index) -- prefix-aware
        via ``websearch_to_tsquery``, with a trigram-similarity fallback for
        typos/partial input that doesn't tokenize into a real tsquery match.
        Falls back to the generic filter/sort behavior when there's no
        search term (plain listing, city_id filtering, etc.)."""
        if not filter.search:
            return await super().search(
                filter, pagination, options=options, scope=scope
            )

        query = filter.search
        tsquery = func.websearch_to_tsquery("simple", query)
        similarity = func.similarity(self.model.name, query)
        matches = or_(self.model.name_tsv.op("@@")(tsquery), similarity > 0.3)

        base = select(self.model).where(matches)
        city_id = getattr(filter, "city_id", None)
        if city_id is not None:
            base = base.where(self.model.city_id == city_id)
        if scope:
            base = base.where(*scope)

        total = (
            await self.execute(
                select(func.count()).select_from(base.subquery())
            )
        ).scalar_one()
        if not total:
            return [], 0

        ranked = (
            base.order_by(
                func.ts_rank(self.model.name_tsv, tsquery).desc(),
                similarity.desc(),
            )
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        if options:
            ranked = ranked.options(*options)
        return (await self.execute(ranked)).unique().scalars(), total

    async def search_in_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        pagination: SPageParam,
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
