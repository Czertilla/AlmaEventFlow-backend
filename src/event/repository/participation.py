from uuid import UUID
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin, UpsertRepositoryMixin, SearchRepositoryMixin

from event.models.participation import ParticipationORM as Model


class ParticipationRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model
    conflict_index_elements = ["collective_id", "event_id"]

    async def search(self, filter, pagination, *, options=None):
        return await super().search(filter, pagination)
