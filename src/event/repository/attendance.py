from uuid import UUID
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin, UpsertRepositoryMixin

from event.models.attendance import AttendanceORM as Model


class AttendanceRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID]
):
    model = Model
    conflict_index_elements = ["id", "member_id", "participation_id"]