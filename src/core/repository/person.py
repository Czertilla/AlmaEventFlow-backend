from typing import TypeVar
from uuid import UUID

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
)
from core.models.person import PersonAORM

Model = TypeVar("Model", bound=PersonAORM)


class PersonBaseRepo[Model: PersonAORM](
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
):
    model: type[Model]
