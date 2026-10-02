from typing import TypeVar
from uuid import UUID

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
)
from core.models.address import AddressAORM

Model = TypeVar("Model", bound=AddressAORM)

class AddressBaseRepo[Model: AddressAORM](
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
):
    model: type[Model]