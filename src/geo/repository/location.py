from typing import Any
from uuid import UUID, uuid4

from fastapi_filter.contrib.sqlalchemy import Filter
from geoalchemy2 import WKTElement
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)
from core.dto.pagination import PageParams
from geo.dto.point import PointDTO
from geo.models.address import AddressORM
from geo.models.location import LocationORM as Model
from geo.models.spot import spot_element
from geo.search import TS_CONFIG, search_page, text_match


class LocationRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model

    @staticmethod
    def dump_spot(data: dict[str, Any]):
        if "spot" not in data:
            return
        data["spot"] = spot_element(data.pop("spot"))

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

    async def search(
        self,
        filter: Filter,
        pagination: PageParams,
        *,
        options=None,
        scope: list | None = None,
        near: PointDTO | None = None,
    ) -> tuple[list[Model], int]:
        haystack = func.concat_ws(" ", self.model.name, AddressORM.name)
        match = (
            text_match(
                filter.search, func.to_tsvector(TS_CONFIG, haystack), haystack
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
            base = plain.filter(
                select(self.model)
                .outerjoin(AddressORM, AddressORM.id == self.model.address_id)
                .where(predicate)
            )
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
        near: PointDTO,
        pagination: PageParams,
        *,
        options=None,
        scope: list | None = None,
    ) -> tuple[list[Model], int]:
        """No search text -- order by distance from ``near``. An
        address-anchored location has no ``spot`` of its own, hence the
        outer join + coalesce, same as ``search_in_bbox`` below."""
        point = WKTElement(f"POINT({near.lon} {near.lat})", srid=4326)
        effective_point = func.coalesce(self.model.spot, AddressORM.spot)
        base = filter.filter(
            select(self.model)
            .outerjoin(AddressORM, AddressORM.id == self.model.address_id)
            .where(effective_point.isnot(None))
        )
        if scope:
            base = base.where(*scope)

        total = (
            await self.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        if not total:
            return [], 0

        stmt = base.order_by(effective_point.op("<->")(point)).limit(
            pagination.limit
        ).offset(pagination.offset)
        if options:
            stmt = stmt.options(*options)
        return (await self.execute(stmt)).unique().scalars(), total

    async def insert_address_proxy(self, address_id: UUID) -> UUID | None:
        stmt = (
            insert(self.model)
            .values(id=uuid4(), address_id=address_id, name=None)
            .on_conflict_do_nothing(
                index_elements=["address_id"],
                index_where=self.model.name.is_(None),
            )
            .returning(self.model.id)
        )
        return (await self.execute(stmt)).scalar_one_or_none()

    async def delete_by_address(self, address_id: UUID) -> list[UUID]:
        stmt = (
            delete(self.model)
            .where(self.model.address_id == address_id)
            .returning(self.model.id)
        )
        return list((await self.execute(stmt)).scalars())

    async def search_in_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        pagination: PageParams,
    ) -> tuple[list[Model], int]:
        """An address-anchored location has no ``spot`` of its own -- its
        effective point for map display is the linked address's ``spot``,
        hence the outer join + coalesce instead of a plain column check."""
        envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        effective_point = func.coalesce(self.model.spot, AddressORM.spot)
        base = (
            select(self.model)
            .outerjoin(AddressORM, AddressORM.id == self.model.address_id)
            .where(effective_point.op("&&")(envelope))
        )

        total = (
            await self.execute(
                select(func.count()).select_from(base.subquery())
            )
        ).scalar_one()
        if not total:
            return [], 0

        stmt = (
            base.options(selectinload(self.model.address))
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        return (await self.execute(stmt)).unique().scalars(), total
