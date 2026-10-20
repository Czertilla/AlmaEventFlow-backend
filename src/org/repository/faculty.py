from uuid import UUID

from sqlalchemy import func, select

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)
from org.models.faculty import FacultyORM as Model


class FacultyRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model

    async def find_by_name(self, name: str, university_id: UUID) -> Model | None:
        stmt = select(self.model).where(
            func.lower(self.model.name) == name.lower(),
            self.model.university_id == university_id,
        )
        return (await self.execute(stmt)).scalars().first()
