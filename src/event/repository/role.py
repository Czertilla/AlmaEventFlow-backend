from uuid import UUID

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
)

from event.models.role import RoleORM as Model


class RoleRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
):
    model = Model

    async def get_from_list(self, ids: list[UUID]) -> list[Model]:
        return await self.get_many(Model.id.in_(ids), limit_=25)
