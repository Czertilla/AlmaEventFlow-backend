import datetime
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Row

from core.schema.error import ErrorCode
from core.service.base import BaseService, required_transaction
from core.utils.exc.http import VancedHTTPException
from event.dto.member import MemberDTO
from event.dto.member_profile import (
    MemberPersonDTO,
    MemberProfileDTO,
    MemberProfilePeriodDTO,
    ProfileViewerDTO,
)
from event.dto.role import RolePreviewDTO
from event.enum.status import EventStatusEnumV1
from event.exc.event import MemberNotExistsException
from event.models.member import MemberORM
from event.service.attendance_stats import (
    by_month,
    by_type,
    summarize,
    to_item,
)
from event.uow.member_profile import MemberProfileUOW

COUNTED_STATUSES = (EventStatusEnumV1.active, EventStatusEnumV1.archived)
DEFAULT_WINDOW_DAYS = 365


class MemberProfileService(BaseService[MemberProfileUOW]):
    @staticmethod
    def _to_member(member: MemberORM) -> MemberDTO:
        return MemberDTO(
            id=member.id,
            collective_id=member.collective_id,
            person_id=member.person_id,
            is_active=member.is_active,
            roles=[RolePreviewDTO(id=r.id, name=r.name) for r in member.roles],
            created_at=member.created_at,
            edited_at=member.edited_at,
        )

    @required_transaction
    async def _read_member(self, member_id: UUID) -> MemberORM:
        member = await self.uow.members.get_with_details(member_id)
        if member is None:
            raise MemberNotExistsException()
        return member

    @required_transaction
    async def _access(
        self, member: MemberORM, viewer: ProfileViewerDTO
    ) -> tuple[bool, bool]:
        """Returns (can_manage, can_see_comments), or refuses the viewer."""
        if viewer.is_superuser:
            return True, True
        if viewer.person_id is not None:
            collective = await self.uow.collectives.get(member.collective_id)
            if collective is not None and collective.principal_id == viewer.person_id:
                return True, True
            if member.person_id == viewer.person_id:
                return False, True
            memberships = await self.uow.members.get_by_person_id(viewer.person_id)
            if any(
                m.collective_id == member.collective_id and m.is_active
                for m in memberships
            ):
                return False, False
        raise VancedHTTPException(
            status_code=403, detail=ErrorCode.NOT_COLLECTIVE_MEMBER
        )

    @required_transaction
    async def _history(
        self,
        member: MemberORM,
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> Sequence[Row[Any]]:
        return await self.uow.attendances.member_history(
            member.id, member.collective_id, date_from, date_to, COUNTED_STATUSES
        )

    @required_transaction
    async def _years(self, member: MemberORM) -> list[int]:
        return await self.uow.attendances.member_event_years(
            member.id, member.collective_id, COUNTED_STATUSES
        )

    async def read(
        self,
        member_id: UUID,
        period: MemberProfilePeriodDTO,
        viewer: ProfileViewerDTO,
        *,
        today: datetime.date | None = None,
    ) -> MemberProfileDTO:
        today = today or datetime.date.today()
        date_to = period.date_to or today
        date_from = period.date_from or date_to - datetime.timedelta(
            days=DEFAULT_WINDOW_DAYS - 1
        )
        async with self.uow:
            member = await self._read_member(member_id)
            can_manage, show_comments = await self._access(member, viewer)
            rows = await self._history(member, date_from, date_to)
            years = await self._years(member)
            member_dto = self._to_member(member)
            person = MemberPersonDTO(
                id=member.person.id,
                surname=member.person.surname,
                name=member.person.name,
                patronymic=member.person.patronymic,
            )
        items = [to_item(row, today, show_comments) for row in rows]
        return MemberProfileDTO(
            member=member_dto,
            person=person,
            can_manage=can_manage,
            date_from=date_from,
            date_to=date_to,
            years=years,
            summary=summarize(items),
            by_type=by_type(items),
            by_month=by_month(items),
            items=items,
        )
