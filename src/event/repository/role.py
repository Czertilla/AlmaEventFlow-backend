from uuid import UUID

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
    SearchRepositoryMixin,
)

from event.models.role import RoleORM as Model


class RoleRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model

    async def search(self, filter, pagination, *, options=None):
        return await super().search(filter, pagination)



    async def get_from_list(self, ids: list[UUID]) -> list[Model]:
        return await self.get_many(Model.id.in_(ids), limit_=25)
