import datetime
from collections.abc import Collection, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Row, Select, extract, select

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)
from event.models.attendance import AttendanceORM as Model
from event.models.event import EventORM, EventStatusORM, EventTypeORM
from event.models.member import MemberORM
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

    async def collective_id_of(self, attendance_id: UUID) -> UUID | None:
        stmt = (
            select(ParticipationORM.collective_id)
            .join(self.model, self.model.participation_id == ParticipationORM.id)
            .where(self.model.id == attendance_id)
        )
        return (await self.execute(stmt)).scalar_one_or_none()

    async def of_participation(self, participation_id: UUID) -> list[Model]:
        stmt = select(self.model).where(
            self.model.participation_id == participation_id
        )
        return list((await self.execute(stmt)).unique().scalars().all())

    async def of_person_in_event(
        self, person_id: UUID, event_id: UUID
    ) -> list[Model]:
        stmt = (
            select(self.model)
            .join(
                ParticipationORM,
                self.model.participation_id == ParticipationORM.id,
            )
            .join(MemberORM, MemberORM.id == self.model.member_id)
            .where(
                ParticipationORM.event_id == event_id,
                MemberORM.person_id == person_id,
            )
        )
        return list((await self.execute(stmt)).unique().scalars().all())

    def _member_scope(
        self,
        stmt: Select[Any],
        member_id: UUID,
        collective_id: UUID,
        statuses: Collection[str],
    ) -> Select[Any]:
        return (
            stmt.select_from(self.model)
            .join(ParticipationORM, ParticipationORM.id == self.model.participation_id)
            .join(EventORM, EventORM.id == ParticipationORM.event_id)
            .join(EventStatusORM, EventStatusORM.id == EventORM.status_id)
            .where(
                self.model.member_id == member_id,
                ParticipationORM.collective_id == collective_id,
                EventORM.date.is_not(None),
                EventStatusORM.name.in_(statuses),
            )
        )

    def _collective_scope(
        self, stmt: Select[Any], collective_id: UUID, statuses: Collection[str]
    ) -> Select[Any]:
        return (
            stmt.select_from(self.model)
            .join(ParticipationORM, ParticipationORM.id == self.model.participation_id)
            .join(EventORM, EventORM.id == ParticipationORM.event_id)
            .join(EventStatusORM, EventStatusORM.id == EventORM.status_id)
            .where(
                ParticipationORM.collective_id == collective_id,
                EventORM.date.is_not(None),
                EventStatusORM.name.in_(statuses),
            )
        )

    async def collective_history(
        self,
        collective_id: UUID,
        date_from: datetime.date,
        date_to: datetime.date,
        statuses: Collection[str],
    ) -> Sequence[Row[Any]]:
        stmt = self._collective_scope(
            select(
                self.model.id.label("attendance_id"),
                self.model.member_id,
                self.model.is_attended,
                self.model.is_verified,
                self.model.edited_at,
                EventORM.id.label("event_id"),
                EventORM.name.label("event_name"),
                EventORM.date,
                EventStatusORM.name.label("status"),
                EventTypeORM.name.label("type"),
            ),
            collective_id,
            statuses,
        )
        stmt = (
            stmt.outerjoin(EventTypeORM, EventTypeORM.id == EventORM.type_id)
            .where(EventORM.date.between(date_from, date_to))
            .order_by(EventORM.date.desc(), EventORM.name)
        )
        return (await self.execute(stmt)).all()

    async def collective_event_years(
        self, collective_id: UUID, statuses: Collection[str]
    ) -> list[int]:
        year = extract("year", EventORM.date)
        stmt = self._collective_scope(
            select(year).distinct(), collective_id, statuses
        ).order_by(year.desc())
        return [int(value) for value in (await self.execute(stmt)).scalars()]

    async def member_history(
        self,
        member_id: UUID,
        collective_id: UUID,
        date_from: datetime.date,
        date_to: datetime.date,
        statuses: Collection[str],
    ) -> Sequence[Row[Any]]:
        stmt = self._member_scope(
            select(
                self.model.id.label("attendance_id"),
                self.model.is_attended,
                self.model.is_verified,
                self.model.edited_at,
                self.model.comment,
                EventORM.id.label("event_id"),
                EventORM.name.label("event_name"),
                EventORM.date,
                EventStatusORM.name.label("status"),
                EventTypeORM.name.label("type"),
            ),
            member_id,
            collective_id,
            statuses,
        )
        stmt = (
            stmt.outerjoin(EventTypeORM, EventTypeORM.id == EventORM.type_id)
            .where(EventORM.date.between(date_from, date_to))
            .order_by(EventORM.date.desc(), EventORM.name)
        )
        return (await self.execute(stmt)).all()

    async def member_event_years(
        self, member_id: UUID, collective_id: UUID, statuses: Collection[str]
    ) -> list[int]:
        year = extract("year", EventORM.date)
        stmt = self._member_scope(
            select(year).distinct(), member_id, collective_id, statuses
        ).order_by(year.desc())
        return [int(value) for value in (await self.execute(stmt)).scalars()]
