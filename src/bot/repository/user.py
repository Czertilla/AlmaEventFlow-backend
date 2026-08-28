from uuid import UUID

from bot.model.user import UserORM as Model
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
)


class UserRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
):
    model = Model
    conflict_index_elements = ["person_id"]

    async def get_by_person_id(self, person_id: UUID) -> Model | None:
        return await self.get_one(person_id=person_id)