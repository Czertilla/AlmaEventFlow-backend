from uuid import UUID

from geoalchemy2 import WKTElement
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)
from core.schema.pagination import SPageParam
from geo.models.address import AddressORM
from geo.models.location import LocationORM as Model


class LocationRepo(
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

    async def search_in_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        pagination: SPageParam,
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
