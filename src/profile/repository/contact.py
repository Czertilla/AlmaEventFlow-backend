from uuid import UUID
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
)

from profile.models.contact import ContactORM as Model


class ContactRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
):
    model = Model

    async def get_many_by_person(
        self, person_id: UUID, limit: int, offset: int
    ) -> tuple[Model, int]:
        criteria = Model.person_id == person_id
        return (
            await self.get_many(
                criteria,
                limit_=limit,
                offset_=offset,
            ),
            await self.count(criteria),
        )
