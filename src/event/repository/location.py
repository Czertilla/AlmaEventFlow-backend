import datetime
from uuid import UUID

from sqlalchemy import func, select

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
)
from event.models.event import EventORM
from event.models.location import LocationORM as Model
from event.models.participation import ParticipationORM


class LocationRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID]
):
    model = Model

    async def recent_for_collective(
        self, collective_id: UUID, limit: int
    ) -> list[tuple[UUID, datetime.datetime]]:
        used_at = func.max(func.coalesce(EventORM.edited_at, EventORM.created_at))
        stmt = (
            select(EventORM.location_id, used_at)
            .join(ParticipationORM, ParticipationORM.event_id == EventORM.id)
            .where(
                ParticipationORM.collective_id == collective_id,
                EventORM.location_id.is_not(None),
            )
            .group_by(EventORM.location_id)
            .order_by(used_at.desc(), EventORM.location_id)
            .limit(limit)
        )
        return [
            (location_id, used)
            for location_id, used in (await self.execute(stmt)).all()
        ]
