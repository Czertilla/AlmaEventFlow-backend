from uuid import UUID
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin, UpsertRepositoryMixin

from profile.models.student import (
    StudentORM as Model,
    StudentGroupORM,
    StudentDegree,
)


class StudentRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID]
):
    model = Model


class StudentGroupRepo(
    SQLAlchemyRepository[StudentGroupORM],
    IDRepositoryMixin[StudentGroupORM, int],
    UpsertRepositoryMixin[StudentGroupORM, int],
):
    model = StudentGroupORM


class StudentDegreeRepo(
    SQLAlchemyRepository[StudentDegree],
    IDRepositoryMixin[StudentDegree, int],
    UpsertRepositoryMixin[StudentDegree, int],
):
    model = StudentDegree
