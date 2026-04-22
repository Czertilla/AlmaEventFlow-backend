from uuid import UUID
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin, UpsertRepositoryMixin

from event.models.link import EventLinkORM as Model


class EventLinkRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID]
):
    model = Model
