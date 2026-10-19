from profile.models.contact import ContactORM as Model
from uuid import UUID

from sqlalchemy import select

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)


class ContactRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model

    async def by_person(self, person_id: UUID) -> list[Model]:
        stmt = (
            select(self.model)
            .where(self.model.person_id == person_id)
            .order_by(self.model.created_at, self.model.id)
        )
        return list((await self.execute(stmt)).scalars().all())
