import datetime
from collections.abc import Collection, Sequence
from typing import Any, Literal, NamedTuple
from uuid import UUID

from sqlalchemy import ColumnElement, Row, Select, and_, func, or_, select, true

from core.database.sqlalchemy.core import SQLAlchemyRepository
from event.dto.feed import EventFilterViewDTO, EventKeyDTO
from event.dto.member_profile import ProfileViewerDTO
from event.dto.role import RolePreviewDTO
from event.models.attendance import AttendanceORM
from event.models.collective import CollectiveORM
from event.models.event import (
    EventLevelORM,
    EventORM,
    EventStatusORM,
    EventTypeORM,
)
from event.models.location import LocationORM
from event.models.member import MemberORM, MemberRoleAssociation
from event.models.participation import ParticipationORM
from event.models.person import PersonORM
from event.models.role import RoleORM
from event.models.stage import EventStageORM

Side = Literal["past", "future"]


class AttendanceCounts(NamedTuple):
    attended: int
    total: int
    latest: datetime.datetime | None


PENDING_LIMIT = 100
MARKED = or_(
    AttendanceORM.edited_at.is_not(None), AttendanceORM.is_verified.is_(True)
)


class ViewRepo(SQLAlchemyRepository[EventORM]):
    model = EventORM

    @staticmethod
    def _visible(viewer: ProfileViewerDTO) -> ColumnElement[bool]:
        """Everyone sees active events; a draft or an archived one is for the
        leaders of the collectives taking part in it."""
        active = EventStatusORM.name == "active"
        if viewer.is_superuser:
            return true()
        if viewer.person_id is None:
            return active
        led = (
            select(ParticipationORM.event_id)
            .join(
                CollectiveORM,
                CollectiveORM.id == ParticipationORM.collective_id,
            )
            .where(CollectiveORM.principal_id == viewer.person_id)
        )
        return or_(active, EventORM.id.in_(led))

    @staticmethod
    def _events(
        viewer: ProfileViewerDTO | None,
        filters: EventFilterViewDTO | None,
        *,
        templates: bool = False,
    ) -> Select[Any]:
        stmt = (
            select(
                EventORM.id,
                EventORM.name,
                EventORM.date,
                EventORM.format,
                EventORM.location_id,
                EventORM.created_at,
                EventORM.edited_at,
                EventStatusORM.name.label("status"),
                EventLevelORM.name.label("level"),
                EventTypeORM.name.label("type"),
            )
            .select_from(EventORM)
            .join(EventStatusORM, EventStatusORM.id == EventORM.status_id)
            .outerjoin(EventLevelORM, EventLevelORM.id == EventORM.level_id)
            .outerjoin(EventTypeORM, EventTypeORM.id == EventORM.type_id)
        )
        if not templates:
            stmt = stmt.where(EventStatusORM.name != "template")
        if viewer is not None:
            stmt = stmt.where(ViewRepo._visible(viewer))
        if filters is None:
            return stmt
        if filters.statuses:
            stmt = stmt.where(
                EventStatusORM.name.in_([s.value for s in filters.statuses])
            )
        if filters.types:
            stmt = stmt.where(
                EventTypeORM.name.in_([t.value for t in filters.types])
            )
        if filters.levels:
            stmt = stmt.where(
                EventLevelORM.name.in_([v.value for v in filters.levels])
            )
        if filters.formats:
            stmt = stmt.where(EventORM.format.in_(filters.formats))
        if filters.collective_ids:
            stmt = stmt.where(
                EventORM.id.in_(
                    select(ParticipationORM.event_id).where(
                        ParticipationORM.collective_id.in_(
                            filters.collective_ids
                        )
                    )
                )
            )
        if filters.date_from is not None:
            stmt = stmt.where(EventORM.date >= filters.date_from)
        if filters.date_to is not None:
            stmt = stmt.where(EventORM.date <= filters.date_to)
        return stmt

    async def window(
        self,
        viewer: ProfileViewerDTO | None,
        filters: EventFilterViewDTO,
        *,
        side: Side,
        boundary: datetime.date | None,
        after: EventKeyDTO | None,
        limit: int,
    ) -> Sequence[Row[Any]]:
        """One side of the date order, next to ``after`` (exclusive) or to ``boundary``
        (the future side includes it, the past side does not); ``limit`` + 1 rows,
        so the caller can tell whether more are left."""
        stmt = self._events(viewer, filters).where(EventORM.date.is_not(None))
        if side == "future":
            if after is not None:
                stmt = stmt.where(
                    or_(
                        EventORM.date > after.date,
                        and_(
                            EventORM.date == after.date, EventORM.id > after.id
                        ),
                    )
                )
            elif boundary is not None:
                stmt = stmt.where(EventORM.date >= boundary)
            stmt = stmt.order_by(EventORM.date.asc(), EventORM.id.asc())
        else:
            if after is not None:
                stmt = stmt.where(
                    or_(
                        EventORM.date < after.date,
                        and_(
                            EventORM.date == after.date, EventORM.id < after.id
                        ),
                    )
                )
            elif boundary is not None:
                stmt = stmt.where(EventORM.date < boundary)
            stmt = stmt.order_by(EventORM.date.desc(), EventORM.id.desc())
        return (await self.execute(stmt.limit(limit + 1))).all()

    async def by_ids(
        self,
        viewer: ProfileViewerDTO | None,
        event_ids: Collection[UUID],
        *,
        templates: bool = False,
    ) -> Sequence[Row[Any]]:
        if not event_ids:
            return []
        stmt = self._events(viewer, None, templates=templates).where(
            EventORM.id.in_(event_ids)
        )
        return (await self.execute(stmt)).all()

    async def collective_events(
        self, collective_id: UUID, limit: int
    ) -> Sequence[Row[Any]]:
        """Every event of the collective, a template too, the latest first;
        ``limit`` + 1 rows."""
        filters = EventFilterViewDTO(collective_ids=[collective_id])
        stmt = (
            self._events(None, filters, templates=True)
            .order_by(EventORM.date.desc().nulls_first(), EventORM.id.desc())
            .limit(limit + 1)
        )
        return (await self.execute(stmt)).all()

    async def event_details(self, event_id: UUID) -> Row[Any]:
        stmt = select(EventORM.description, EventORM.organizer_id).where(
            EventORM.id == event_id
        )
        return (await self.execute(stmt)).one()

    async def stages_of(self, event_id: UUID) -> list[EventStageORM]:
        stmt = (
            select(EventStageORM)
            .where(EventStageORM.event_id == event_id)
            .order_by(EventStageORM.start_at, EventStageORM.id)
        )
        return list((await self.execute(stmt)).unique().scalars().all())

    async def roster(
        self, collective_ids: Collection[UUID]
    ) -> Sequence[Row[Any]]:
        """Every member of the collectives, the former ones too, by name."""
        if not collective_ids:
            return []
        stmt = (
            select(
                MemberORM.id,
                MemberORM.collective_id,
                MemberORM.is_active,
                PersonORM.id.label("person_id"),
                PersonORM.surname,
                PersonORM.name,
                PersonORM.patronymic,
            )
            .select_from(MemberORM)
            .join(PersonORM, PersonORM.id == MemberORM.person_id)
            .where(MemberORM.collective_id.in_(collective_ids))
            .order_by(
                PersonORM.surname,
                PersonORM.name,
                PersonORM.patronymic,
                MemberORM.id,
            )
        )
        return (await self.execute(stmt)).all()

    async def roles_of_members(
        self, member_ids: Collection[UUID]
    ) -> dict[UUID, list[RolePreviewDTO]]:
        if not member_ids:
            return {}
        stmt = (
            select(MemberRoleAssociation.member_id, RoleORM.id, RoleORM.name)
            .select_from(MemberRoleAssociation)
            .join(RoleORM, RoleORM.id == MemberRoleAssociation.role_id)
            .where(MemberRoleAssociation.member_id.in_(member_ids))
            .order_by(RoleORM.name, RoleORM.id)
        )
        roles: dict[UUID, list[RolePreviewDTO]] = {}
        for member_id, role_id, name in (await self.execute(stmt)).all():
            roles.setdefault(member_id, []).append(
                RolePreviewDTO(id=role_id, name=name)
            )
        return roles

    async def roles_of_collective(self, collective_id: UUID) -> list[RoleORM]:
        stmt = (
            select(RoleORM)
            .where(RoleORM.collective_id == collective_id)
            .order_by(RoleORM.name, RoleORM.id)
        )
        return list((await self.execute(stmt)).unique().scalars().all())

    async def attendances_of(
        self, participation_ids: Collection[UUID]
    ) -> list[AttendanceORM]:
        if not participation_ids:
            return []
        stmt = select(AttendanceORM).where(
            AttendanceORM.participation_id.in_(participation_ids)
        )
        return list((await self.execute(stmt)).unique().scalars().all())

    async def members_by_ids(
        self, member_ids: Collection[UUID]
    ) -> Sequence[Row[Any]]:
        if not member_ids:
            return []
        stmt = (
            select(
                MemberORM.id,
                MemberORM.collective_id,
                MemberORM.is_active,
                PersonORM.id.label("person_id"),
                PersonORM.surname,
                PersonORM.name,
                PersonORM.patronymic,
            )
            .select_from(MemberORM)
            .join(PersonORM, PersonORM.id == MemberORM.person_id)
            .where(MemberORM.id.in_(member_ids))
        )
        return (await self.execute(stmt)).all()

    async def pending_event_ids(
        self, member_ids: Collection[UUID]
    ) -> list[UUID]:
        """Active events where one of the members is declared and nobody has
        marked it."""
        if not member_ids:
            return []
        stmt = (
            select(EventORM.id, EventORM.date)
            .select_from(AttendanceORM)
            .join(
                ParticipationORM,
                ParticipationORM.id == AttendanceORM.participation_id,
            )
            .join(EventORM, EventORM.id == ParticipationORM.event_id)
            .join(EventStatusORM, EventStatusORM.id == EventORM.status_id)
            .where(
                AttendanceORM.member_id.in_(member_ids),
                ~MARKED,
                EventStatusORM.name == "active",
            )
            .distinct()
            .order_by(EventORM.date.asc().nulls_last(), EventORM.id.asc())
            .limit(PENDING_LIMIT)
        )
        return [row.id for row in (await self.execute(stmt)).all()]

    async def stage_spans(
        self, event_ids: Collection[UUID]
    ) -> dict[UUID, tuple[datetime.datetime, datetime.datetime]]:
        if not event_ids:
            return {}
        stmt = (
            select(
                EventStageORM.event_id,
                func.min(EventStageORM.start_at),
                func.max(
                    func.coalesce(EventStageORM.end_at, EventStageORM.start_at)
                ),
            )
            .where(EventStageORM.event_id.in_(event_ids))
            .group_by(EventStageORM.event_id)
        )
        return {
            event_id: (first, last)
            for event_id, first, last in (await self.execute(stmt)).all()
        }

    async def places(
        self, location_ids: Collection[UUID]
    ) -> dict[UUID, Row[Any]]:
        if not location_ids:
            return {}
        stmt = select(
            LocationORM.id, LocationORM.name, LocationORM.lat, LocationORM.lon
        ).where(LocationORM.id.in_(location_ids))
        return {row.id: row for row in (await self.execute(stmt)).all()}

    async def participations(
        self,
        event_ids: Collection[UUID],
        collective_ids: Collection[UUID] | None,
    ) -> Sequence[Row[Any]]:
        """Who takes part in the events; every collective when ``collective_ids``
        is ``None``."""
        if not event_ids or (collective_ids is not None and not collective_ids):
            return []
        stmt = (
            select(
                ParticipationORM.id,
                ParticipationORM.event_id,
                ParticipationORM.collective_id,
                ParticipationORM.priority_degree,
                CollectiveORM.name.label("collective_name"),
            )
            .select_from(ParticipationORM)
            .join(
                CollectiveORM,
                CollectiveORM.id == ParticipationORM.collective_id,
            )
            .where(ParticipationORM.event_id.in_(event_ids))
            .order_by(CollectiveORM.name, ParticipationORM.id)
        )
        if collective_ids is not None:
            stmt = stmt.where(
                ParticipationORM.collective_id.in_(collective_ids)
            )
        return (await self.execute(stmt)).all()

    async def attendance_counts(
        self, participation_ids: Collection[UUID]
    ) -> dict[UUID, AttendanceCounts]:
        """The places of every participation: how many came, how many are declared,
        and when one of them last changed."""
        if not participation_ids:
            return {}
        stmt = (
            select(
                AttendanceORM.participation_id,
                func.count().filter(
                    AttendanceORM.is_attended.is_(True), MARKED
                ),
                func.count(),
                func.max(
                    func.coalesce(
                        AttendanceORM.edited_at, AttendanceORM.created_at
                    )
                ),
            )
            .where(AttendanceORM.participation_id.in_(participation_ids))
            .group_by(AttendanceORM.participation_id)
        )
        return {
            pid: AttendanceCounts(attended, total, latest)
            for pid, attended, total, latest in (await self.execute(stmt)).all()
        }

    async def attendances_of_members(
        self, participation_ids: Collection[UUID], member_ids: Collection[UUID]
    ) -> list[AttendanceORM]:
        if not participation_ids or not member_ids:
            return []
        stmt = select(AttendanceORM).where(
            AttendanceORM.participation_id.in_(participation_ids),
            AttendanceORM.member_id.in_(member_ids),
        )
        return list((await self.execute(stmt)).unique().scalars().all())

    async def collectives_of(self, person_id: UUID) -> Sequence[Row[Any]]:
        """The collectives the person leads or belongs to (an inactive membership
        too)."""
        stmt = (
            select(
                CollectiveORM.id,
                CollectiveORM.name,
                CollectiveORM.is_verified,
                CollectiveORM.principal_id,
                MemberORM.id.label("member_id"),
                MemberORM.is_active.label("member_is_active"),
            )
            .select_from(CollectiveORM)
            .outerjoin(
                MemberORM,
                and_(
                    MemberORM.collective_id == CollectiveORM.id,
                    MemberORM.person_id == person_id,
                ),
            )
            .where(
                or_(
                    CollectiveORM.principal_id == person_id,
                    MemberORM.id.is_not(None),
                )
            )
            .order_by(CollectiveORM.name, CollectiveORM.id)
        )
        return (await self.execute(stmt)).all()
