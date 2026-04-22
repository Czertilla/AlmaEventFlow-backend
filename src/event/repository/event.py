from uuid import UUID
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin, UpsertRepositoryMixin

from event.models.event import EventORM as Model, EventStatusORM


class EventRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID]
):
    model = Model


class EventStatusRepo(
    SQLAlchemyRepository[EventStatusORM],
    IDRepositoryMixin[EventStatusORM, int],
    UpsertRepositoryMixin[EventStatusORM, int],
):
    model = EventStatusORM
