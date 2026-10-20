from collections.abc import Iterable, Sequence
from types import CoroutineType
from typing import Any, cast
from uuid import UUID, uuid4

from fastapi_filter.contrib.sqlalchemy import Filter
from geoalchemy2 import WKTElement
from sqlalchemy import ColumnElement, Select, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

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
from geo.search import (
    TS_CONFIG,
    SearchableFilter,
    distance_m,
    search_page,
    search_ranked,
    text_match,
)


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

    def add_n_return(
        self, data: dict[str, Any], options: tuple[ExecutableOption, ...] = ()
    ) -> CoroutineType[Any, Any, Model]:
        self.dump_spot(data)
        return super().add_n_return(data, options)

    def add_one(self, data: dict[str, Any]) -> CoroutineType[Any, Any, None]:
        self.dump_spot(data)
        return super().add_one(data)

    def update_one(
        self, id: UUID, data: dict[str, Any], flush: bool = False
    ) -> CoroutineType[Any, Any, Model | None]:
        self.dump_spot(data)
        return super().update_one(id, data, flush)

    def upsert(
        self,
        data: dict[str, Any],
        options: tuple[ExecutableOption, ...] = (),
    ) -> CoroutineType[Any, Any, Model | None]:
        self.dump_spot(data)
        return super().upsert(data, options)

    async def get_by_ids(
        self, ids: Sequence[UUID], options: Sequence[ExecutableOption] = ()
    ) -> list[Model]:
        stmt = select(self.model).where(self.model.id.in_(ids)).options(*options)
        return list((await self.execute(stmt)).unique().scalars())

    async def search(
        self,
        filter: Filter,
        pagination: PageParams,
        *,
        options: Sequence[ExecutableOption] | None = None,
        scope: list[ColumnElement[bool]] | None = None,
        near: PointDTO | None = None,
    ) -> tuple[Iterable[Model], int]:
        searchable = cast("SearchableFilter", filter)
        haystack = self._haystack()
        match = (
            text_match(
                searchable.search, func.to_tsvector(TS_CONFIG, haystack), haystack
            )
            if searchable.search
            else None
        )
        if match is None:
            if near is not None:
                return await self._search_near(
                    searchable, near, pagination, options=options, scope=scope
                )
            return await super().search(
                filter, pagination, options=options, scope=scope
            )

        plain = searchable.model_copy(update={"search": None})

        def build(predicate: ColumnElement[bool]) -> Select[Any]:
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

    def _haystack(self):
        return func.concat_ws(
            " ", self.model.name, AddressORM.name, AddressORM.locality
        )

    def _joined(
        self, *, named_only: bool, city_id: int | None
    ) -> Select[tuple[Model]]:
        stmt = select(self.model).outerjoin(
            AddressORM, AddressORM.id == self.model.address_id
        )
        if named_only:
            stmt = stmt.where(self.model.name.is_not(None))
        if city_id is not None:
            stmt = stmt.where(AddressORM.city_id == city_id)
        return stmt

    async def search_ranked(
        self,
        query: str,
        limit: int,
        *,
        named_only: bool = True,
        city_id: int | None = None,
        near: PointDTO | None = None,
    ) -> list[tuple[Model, float]]:
        haystack = self._haystack()
        match = text_match(query, func.to_tsvector(TS_CONFIG, haystack), haystack)
        if match is None:
            return []

        def build(predicate: ColumnElement[bool]) -> Select[Any]:
            return self._joined(named_only=named_only, city_id=city_id).where(
                predicate
            )

        return await search_ranked(
            self,
            build,
            match,
            limit,
            tie_break=(self.model.name, self.model.id),
            options=(selectinload(self.model.address),),
            near=near,
            spot=func.coalesce(self.model.spot, AddressORM.spot),
            key=self.model.id,
        )

    async def nearest(
        self,
        near: PointDTO,
        limit: int,
        *,
        named_only: bool = True,
        city_id: int | None = None,
    ) -> list[tuple[Model, float]]:
        spot = func.coalesce(self.model.spot, AddressORM.spot)
        meters = distance_m(spot, near)
        stmt = (
            self._joined(named_only=named_only, city_id=city_id)
            .add_columns(meters.label("meters"))
            .where(spot.is_not(None))
            .order_by(meters)
            .limit(limit)
            .options(selectinload(self.model.address))
        )
        rows = (await self.execute(stmt)).unique().all()
        return [(row[0], float(row[1])) for row in rows]

    async def _search_near(
        self,
        filter: SearchableFilter,
        near: PointDTO,
        pagination: PageParams,
        *,
        options: Sequence[ExecutableOption] | None = None,
        scope: list[ColumnElement[bool]] | None = None,
    ) -> tuple[Iterable[Model], int]:
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

    async def anchored_to(self, address_id: UUID) -> list[Model]:
        stmt = (
            select(self.model)
            .where(self.model.address_id == address_id)
            .options(selectinload(self.model.address))
        )
        return list((await self.execute(stmt)).unique().scalars())

    async def find_text_only(self, name: str) -> Model | None:
        """The location that is this text and nothing else, whatever the case."""
        stmt = (
            select(self.model)
            .where(
                self.model.address_id.is_(None),
                self.model.spot.is_(None),
                func.lower(self.model.name) == name.lower(),
            )
            .options(selectinload(self.model.address))
            .limit(1)
        )
        return (await self.execute(stmt)).unique().scalars().first()

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
    ) -> tuple[Iterable[Model], int]:
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
