from uuid import UUID
from sqlalchemy.orm import selectinload
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin, UpsertRepositoryMixin, SearchRepositoryMixin

from event.models.event import EventORM as Model, EventStatusORM


class EventRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model

    async def search(self, filter, pagination, *, options=None):
        _options = (selectinload(Model.status_rel),)
        if options:
            _options = _options + options
        return await super().search(filter, pagination, options=_options)
    


class EventStatusRepo(
    SQLAlchemyRepository[EventStatusORM],
    IDRepositoryMixin[EventStatusORM, int],
    UpsertRepositoryMixin[EventStatusORM, int],
):
    model = EventStatusORM
