from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
)
from geo.models.city import CityORM as Model


class CityRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, int],
    SearchRepositoryMixin[Model],
):
    model = Model
