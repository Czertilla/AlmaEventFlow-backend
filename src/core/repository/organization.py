from typing import TypeVar
from uuid import UUID

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
)
from core.models.organization import OrganizationAORM

Model = TypeVar("Model", bound=OrganizationAORM)


class OrganizationBaseRepo[Model: OrganizationAORM](
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
):
    model: type[Model]
