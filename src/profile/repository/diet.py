from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)

from profile.models.diet import DietORM as Model


class DietRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, int],
    UpsertRepositoryMixin[Model, int],
    SearchRepositoryMixin[Model],
):
    model = Model
