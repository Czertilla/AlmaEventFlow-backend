from profile.models.diet import DietORM as Model

from sqlalchemy import func, select

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)


class DietRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, int],
    UpsertRepositoryMixin[Model, int],
    SearchRepositoryMixin[Model],
):
    model = Model

    async def find_by_name(self, name: str) -> Model | None:
        stmt = select(self.model).where(func.lower(self.model.name) == name.lower())
        return (await self.execute(stmt)).scalars().first()
