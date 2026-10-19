import datetime
from collections import defaultdict
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Row

from core.schema.error import ErrorCode
from core.service.base import BaseService, required_transaction
from core.utils.exc.http import VancedHTTPException
from event.dto.collective_profile import (
    CollectiveInfoDTO,
    CollectiveMemberItemDTO,
    CollectiveProfileDTO,
)
from event.dto.member_profile import (
    MemberAttendanceItemDTO,
    MemberPersonDTO,
    MemberProfilePeriodDTO,
    ProfileViewerDTO,
)
from event.exc.event import CollectiveNotExistsException
from event.models.collective import CollectiveORM
from event.models.member import MemberORM
from event.service.attendance_stats import (
    by_day,
    by_event,
    by_month,
    by_type,
    rollup,
    summarize_collective,
    to_item,
)
from event.service.member_profile import COUNTED_STATUSES, DEFAULT_WINDOW_DAYS
from event.uow.collective_profile import CollectiveProfileUOW


def _person(person: Any) -> MemberPersonDTO:
    return MemberPersonDTO(
        id=person.id,
        surname=person.surname,
        name=person.name,
        patronymic=person.patronymic,
    )


class CollectiveProfileService(BaseService[CollectiveProfileUOW]):
    @required_transaction
    async def _read_collective(self, collective_id: UUID) -> CollectiveORM:
        collective = await self.uow.collectives.get(collective_id)
        if collective is None:
            raise CollectiveNotExistsException()
        return collective

    @required_transaction
    async def _access(
        self, collective: CollectiveORM, viewer: ProfileViewerDTO
    ) -> bool:
        if viewer.is_superuser:
            return True
        if viewer.person_id is not None:
            if collective.principal_id == viewer.person_id:
                return True
            memberships = await self.uow.members.get_by_person_id(viewer.person_id)
            if any(
                m.collective_id == collective.id and m.is_active for m in memberships
            ):
                return False
        raise VancedHTTPException(
            status_code=403, detail=ErrorCode.NOT_COLLECTIVE_MEMBER
        )

    @required_transaction
    async def _principal(self, collective: CollectiveORM) -> MemberPersonDTO | None:
        if collective.principal_id is None:
            return None
        person = await self.uow.persons.get(collective.principal_id)
        return _person(person) if person is not None else None

    @required_transaction
    async def _history(
        self, collective_id: UUID, date_from: datetime.date, date_to: datetime.date
    ) -> Sequence[Row[Any]]:
        return await self.uow.attendances.collective_history(
            collective_id, date_from, date_to, COUNTED_STATUSES
        )

    @required_transaction
    async def _years(self, collective_id: UUID) -> list[int]:
        return await self.uow.attendances.collective_event_years(
            collective_id, COUNTED_STATUSES
        )

    @required_transaction
    async def _members(self, collective_id: UUID) -> list[MemberORM]:
        return await self.uow.members.get_by_collective_with_person(collective_id)

    @staticmethod
    def _member_items(
        members: Sequence[MemberORM],
        by_member: dict[UUID, list[MemberAttendanceItemDTO]],
    ) -> list[CollectiveMemberItemDTO]:
        items: list[CollectiveMemberItemDTO] = []
        for member in members:
            rows = by_member.get(member.id, [])
            if not rows and not member.is_active:
                continue
            counts, past, rate = rollup(rows)
            items.append(
                CollectiveMemberItemDTO(
                    member_id=member.id,
                    person=_person(member.person),
                    is_active=member.is_active,
                    past=past,
                    rate=rate,
                    **counts,
                )
            )
        return sorted(
            items,
            key=lambda m: (m.person.surname.lower(), m.person.name.lower()),
        )

    async def read(
        self,
        collective_id: UUID,
        period: MemberProfilePeriodDTO,
        viewer: ProfileViewerDTO,
        *,
        today: datetime.date | None = None,
    ) -> CollectiveProfileDTO:
        today = today or datetime.date.today()
        date_to = period.date_to or today
        date_from = period.date_from or date_to - datetime.timedelta(
            days=DEFAULT_WINDOW_DAYS - 1
        )
        async with self.uow:
            collective = await self._read_collective(collective_id)
            can_manage = await self._access(collective, viewer)
            principal = await self._principal(collective)
            rows = await self._history(collective_id, date_from, date_to)
            years = await self._years(collective_id)
            members = await self._members(collective_id)
            info = CollectiveInfoDTO(
                id=collective.id,
                name=collective.name,
                is_verified=collective.is_verified,
                principal=principal,
                active_members=sum(member.is_active for member in members),
            )
            paired = [(row.member_id, to_item(row, today)) for row in rows]
            by_member: defaultdict[UUID, list[MemberAttendanceItemDTO]]
            by_member = defaultdict(list)
            for member_id, item in paired:
                by_member[member_id].append(item)
            member_items = self._member_items(members, by_member)
        items = [item for _, item in paired]
        return CollectiveProfileDTO(
            collective=info,
            can_manage=can_manage,
            date_from=date_from,
            date_to=date_to,
            years=years,
            summary=summarize_collective(items),
            by_type=by_type(items),
            by_month=by_month(items),
            days=by_day(items),
            events=by_event(items),
            members=member_items,
        )
