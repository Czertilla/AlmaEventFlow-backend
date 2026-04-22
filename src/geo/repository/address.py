from uuid import UUID

from geoalchemy2 import WKTElement
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
)

from geo.models.address import AddressORM as Model


class AddressAlchemyRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
):
    model = Model

    @staticmethod
    def dump_spot(data: dict):
        point = data.pop("spot", None)
        if not point:
            return
        data["spot"] = WKTElement(
            f"POINT({point['lon']} {point['lat']})", srid=4326
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
