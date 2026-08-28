from profile.models.diet import DietORM as Model

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)


class DietRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, int],
    UpsertRepositoryMixin[Model, int],
    SearchRepositoryMixin[Model],
):
    model = Model
