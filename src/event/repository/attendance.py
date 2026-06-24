from uuid import UUID

from sqlalchemy import exists, select ,func
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin, UpsertRepositoryMixin, SearchRepositoryMixin

from event.models.attendance import AttendanceORM as Model
from event.models.event import EventORM
from event.models.participation import ParticipationORM


class AttendanceRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model
    conflict_index_elements = ["id", "member_id", "participation_id"]

    async def search(self, filter, pagination, *, options=None):
        return await super().search(filter, pagination)
    
    async def active_event_id(self, attendance_id: UUID):
        stmt = (
            select(exists(EventORM.id).where(
                Model.id == attendance_id, EventORM.status_id == 3
            ))
            .join(
                ParticipationORM, Model.participation_id == ParticipationORM.id
            )
            .join(EventORM, EventORM.id == ParticipationORM.event_id))
        return (await self.execute(stmt)).scalar_one_or_none()