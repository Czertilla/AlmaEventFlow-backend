from uuid import UUID
from sqlalchemy.orm import selectinload
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
        # Eager-load the collective so responses can expose its name.
        if options is None:
            options = (selectinload(Model.collective),)
        return await super().search(filter, pagination, options=options)
