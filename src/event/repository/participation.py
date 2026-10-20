from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)
from event.models.member import MemberORM
from event.models.participation import ParticipationORM as Model


class ParticipationRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model
    conflict_index_elements = ["collective_id", "event_id"]

    async def search(self, filter, pagination, *, options=None):
        if options is None:
            options = (selectinload(Model.collective),)
        return await super().search(filter, pagination, options=options)

    async def get_of_collective(
        self, collective_id: UUID, event_id: UUID
    ) -> Model | None:
        stmt = select(self.model).where(
            self.model.collective_id == collective_id,
            self.model.event_id == event_id,
        )
        return (await self.execute(stmt)).scalar_one_or_none()

    async def count_for_event(self, event_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.event_id == event_id)
        )
        return (await self.execute(stmt)).scalar_one()

    async def active_member_ids(self, collective_id: UUID) -> list[UUID]:
        """Members who attend by default when a collective joins an event."""
        stmt = select(MemberORM.id).where(
            MemberORM.collective_id == collective_id, MemberORM.is_active
        )
        return list((await self.execute(stmt)).scalars().all())
