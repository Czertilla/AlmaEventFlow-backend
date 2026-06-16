import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
)
from event.enum.status import EventStatusEnumV1
from event.models.attendance import AttendanceORM
from event.models.calendar import (
    CalendarChangeLogORM,
    CalendarSubscriptionORM,
    CalendarSubscriptionTypeORM,
)
from event.models.collective import CollectiveORM
from event.models.event import EventORM, EventStatusORM
from event.models.member import MemberORM
from event.models.participation import ParticipationORM
from event.models.person import PersonORM
from event.models.stage import EventStageORM

_PARTICIPANT_STATUSES = (EventStatusEnumV1.active.value,)
_PRINCIPAL_STATUSES = (
    EventStatusEnumV1.active.value,
    EventStatusEnumV1.draft.value,
    EventStatusEnumV1.archived.value,
)

_EVENT_OPTIONS = (selectinload(EventORM.status_rel),)
_TYPE_OPTION = (selectinload(CalendarSubscriptionORM.type_rel),)


class CalendarSubscriptionRepo(
    SQLAlchemyRepository[CalendarSubscriptionORM],
    IDRepositoryMixin[CalendarSubscriptionORM, UUID],
    UpsertRepositoryMixin[CalendarSubscriptionORM, UUID],
):
    model = CalendarSubscriptionORM

    async def resolve_type_id(self, name: str) -> int:
        stmt = select(CalendarSubscriptionTypeORM.id).where(
            CalendarSubscriptionTypeORM.name == name
        )
        return (await self.execute(stmt)).scalar_one()

    async def get_loaded(
        self, subscription_id: UUID
    ) -> CalendarSubscriptionORM | None:
        return await self.get_by_id(subscription_id, options=_TYPE_OPTION)

    async def get_by_token_hash(
        self, token_hash: str
    ) -> CalendarSubscriptionORM | None:
        stmt = (
            select(self.model)
            .where(self.model.token_hash == token_hash)
            .options(*_TYPE_OPTION)
        )
        return (await self.execute(stmt)).unique().scalar_one_or_none()

    async def get_active_by_owner(
        self, owner_user_id: UUID
    ) -> list[CalendarSubscriptionORM]:
        stmt = (
            select(self.model)
            .where(
                self.model.owner_user_id == owner_user_id,
                self.model.is_active.is_(True),
            )
            .options(*_TYPE_OPTION)
            .order_by(self.model.created_at)
        )
        return (await self.execute(stmt)).unique().scalars().all()


class CalendarChangeLogRepo(
    SQLAlchemyRepository[CalendarChangeLogORM],
    IDRepositoryMixin[CalendarChangeLogORM, UUID],
):
    model = CalendarChangeLogORM

    async def get_for_collective_since(
        self, collective_id: UUID, since: datetime.datetime
    ) -> list[CalendarChangeLogORM]:
        stmt = (
            select(self.model)
            .where(
                self.model.collective_id == collective_id,
                self.model.occurred_at >= since,
            )
            .order_by(self.model.occurred_at)
        )
        return (await self.execute(stmt)).scalars().all()


class CalendarFeedRepo(SQLAlchemyRepository[EventORM]):
    """Read-only joins that resolve visible events for each subscription type.

    Attendance is reached through participation (there is no direct
    ``attendance.event_id``); participation and attendance carry no status
    column, so the presence of a row is treated as active membership.
    """

    model = EventORM

    async def personal_all(
        self,
        person_id: UUID,
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> list[tuple[EventORM, UUID]]:
        stmt = (
            select(EventORM, AttendanceORM.id)
            .join(
                ParticipationORM,
                ParticipationORM.event_id == EventORM.id,
            )
            .join(
                AttendanceORM,
                AttendanceORM.participation_id == ParticipationORM.id,
            )
            .join(MemberORM, MemberORM.id == AttendanceORM.member_id)
            .join(EventStatusORM, EventStatusORM.id == EventORM.status_id)
            .where(
                MemberORM.person_id == person_id,
                EventStatusORM.name.in_(_PARTICIPANT_STATUSES),
                EventORM.date.is_not(None),
                EventORM.date >= date_from,
                EventORM.date < date_to,
            )
            .options(*_EVENT_OPTIONS)
            .order_by(EventORM.date)
        )
        rows = (await self.execute(stmt)).unique().all()
        return [(event, attendance_id) for event, attendance_id in rows]

    async def personal_collective(
        self,
        person_id: UUID,
        collective_id: UUID,
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> list[tuple[EventORM, UUID]]:
        stmt = (
            select(EventORM, AttendanceORM.id)
            .join(
                ParticipationORM,
                ParticipationORM.event_id == EventORM.id,
            )
            .join(
                AttendanceORM,
                AttendanceORM.participation_id == ParticipationORM.id,
            )
            .join(MemberORM, MemberORM.id == AttendanceORM.member_id)
            .join(EventStatusORM, EventStatusORM.id == EventORM.status_id)
            .where(
                MemberORM.person_id == person_id,
                MemberORM.collective_id == collective_id,
                ParticipationORM.collective_id == collective_id,
                EventStatusORM.name.in_(_PARTICIPANT_STATUSES),
                EventORM.date.is_not(None),
                EventORM.date >= date_from,
                EventORM.date < date_to,
            )
            .options(*_EVENT_OPTIONS)
            .order_by(EventORM.date)
        )
        rows = (await self.execute(stmt)).unique().all()
        return [(event, attendance_id) for event, attendance_id in rows]

    async def principal_collective(
        self,
        collective_id: UUID,
        date_from: datetime.date,
        date_to: datetime.date,
        archived_since: datetime.datetime,
    ) -> list[tuple[EventORM, UUID]]:
        archived = EventStatusEnumV1.archived.value
        stmt = (
            select(EventORM, ParticipationORM.id)
            .join(
                ParticipationORM,
                ParticipationORM.event_id == EventORM.id,
            )
            .join(EventStatusORM, EventStatusORM.id == EventORM.status_id)
            .where(
                ParticipationORM.collective_id == collective_id,
                EventStatusORM.name.in_(_PRINCIPAL_STATUSES),
                (
                    (EventStatusORM.name != archived)
                    | (EventORM.edited_at >= archived_since)
                ),
                EventORM.date.is_not(None),
                EventORM.date >= date_from,
                EventORM.date < date_to,
            )
            .options(*_EVENT_OPTIONS)
            .order_by(EventORM.date)
        )
        rows = (await self.execute(stmt)).unique().all()
        return [(event, participation_id) for event, participation_id in rows]

    async def stages_for_events(
        self, event_ids: list[UUID]
    ) -> list[EventStageORM]:
        if not event_ids:
            return []
        stmt = (
            select(EventStageORM)
            .where(EventStageORM.event_id.in_(event_ids))
            .order_by(EventStageORM.event_id, EventStageORM.start_at)
        )
        return (await self.execute(stmt)).scalars().all()

    async def person_full_name(self, person_id: UUID) -> str | None:
        stmt = select(
            PersonORM.surname, PersonORM.name, PersonORM.patronymic
        ).where(PersonORM.id == person_id)
        row = (await self.execute(stmt)).first()
        if row is None:
            return None
        parts = [part for part in row if part]
        return " ".join(parts) or None

    async def member_collectives(
        self, person_id: UUID
    ) -> list[CollectiveORM]:
        stmt = (
            select(CollectiveORM)
            .join(MemberORM, MemberORM.collective_id == CollectiveORM.id)
            .where(MemberORM.person_id == person_id)
            .order_by(CollectiveORM.name)
        )
        return (await self.execute(stmt)).unique().scalars().all()

    async def member_exists(
        self, person_id: UUID, collective_id: UUID
    ) -> bool:
        return (
            await self.execute(
                select(
                    select(MemberORM.id)
                    .where(
                        MemberORM.person_id == person_id,
                        MemberORM.collective_id == collective_id,
                    )
                    .exists()
                )
            )
        ).scalar()
