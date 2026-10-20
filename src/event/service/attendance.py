from logging import getLogger
from typing import Any, cast
from uuid import UUID

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.schema.error import ErrorCode
from core.service.base import BaseService, required_transaction
from core.utils.exc.http import VancedHTTPException
from event.dto.attendance import (
    AttendanceCreateDTO,
    AttendanceDTO,
    AttendanceFilterDTO,
    AttendanceMinePatchDTO,
    AttendancePatchDTO,
    AttendancePutDTO,
)
from event.dto.me import MeAttendanceCreateDataDTO
from event.exc.event import (
    AttendanceNotExistsException,
    MemberNotExistsException,
    ParticipationNotExistsException,
)
from event.filter.attendance import AttendanceFilter
from event.models.attendance import AttendanceORM
from event.service.notification import notify_event_targets
from event.uow.attendance import AttendanceUOW
from event.uow.me import EventComposeUOW, ParticipationComposeUOW

logger = getLogger(__name__)


class AttendanceService(
    BaseService[AttendanceUOW | ParticipationComposeUOW | EventComposeUOW]
):
    @staticmethod
    def _to_dto(attendance: AttendanceORM) -> AttendanceDTO:
        return dto_from_orm(attendance, AttendanceDTO)

    @required_transaction
    async def _create(
        self, attendance_create: AttendanceCreateDTO
    ) -> AttendanceORM:
        attendance_data = dto_dict(attendance_create)
        attendance = await self.uow.attendances.add_n_return(
            data=attendance_data
        )
        await self.uow.attendances.session.flush(objects=[attendance])
        return attendance

    @required_transaction
    async def _read(self, attendance_id: UUID) -> AttendanceORM | None:
        attendance = await self.uow.attendances.get_by_id(attendance_id)
        return attendance

    @required_transaction
    async def _update(
        self,
        attendance_id: UUID,
        attendance_data: dict[str, Any],
        *,
        flush: bool = False,
    ) -> AttendanceORM:
        attendance = await self.uow.attendances.update_one(
            attendance_id, attendance_data, flush
        )
        if attendance is None:
            raise AttendanceNotExistsException()
        return attendance

    @required_transaction
    async def _upsert(self, attendance_put: AttendancePutDTO) -> AttendanceORM:
        attendance = await self.uow.attendances.upsert(dto_dict(attendance_put))
        assert attendance is not None
        return attendance

    @required_transaction
    async def _delete(self, attendance_id: UUID) -> None:
        await self.uow.attendances.delete_one(attendance_id)

    async def create(
        self, attendance_create: AttendanceCreateDTO
    ) -> AttendanceDTO:
        async with self.uow as uow:
            attendance = await self._create(attendance_create)
            result = self._to_dto(attendance)
            await uow.commit()
            await notify_event_targets(uow, attendance_ids=[attendance.id])
        return result

    async def read(self, attendance_id: UUID) -> AttendanceDTO:
        async with self.uow:
            attendance = await self._read(attendance_id)
            if attendance is None:
                raise AttendanceNotExistsException()
            return self._to_dto(attendance)

    async def patch(self, attendance_patch: AttendancePatchDTO) -> AttendanceDTO:
        async with self.uow as uow:
            attendance_data = dto_dict(attendance_patch, only_set=True)
            attendance = await self._update(
                attendance_patch.id, attendance_data
            )
            result = self._to_dto(attendance)
            await uow.commit()
        return result

    async def put(self, attendance_put: AttendancePutDTO) -> AttendanceDTO:
        async with self.uow as uow:
            attendance = await self._upsert(attendance_put)
            result = self._to_dto(attendance)
            await uow.commit()
        return result

    async def delete(self, attendance_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(attendance_id)
            await uow.commit()

    async def patch_mine(
        self,
        member_id: UUID,
        attendance_id: UUID,
        patch_data: AttendanceMinePatchDTO,
    ) -> AttendanceDTO:
        async with self.uow as uow:
            attendance = await self._read(attendance_id)
            if not attendance:
                raise AttendanceNotExistsException()
            if attendance.member_id != member_id:
                raise AttendanceNotExistsException()
            if attendance.is_verified:
                raise VancedHTTPException(
                    status_code=403, detail=ErrorCode.ATTENDANCE_ALREADY_VERIFIED
                )

            attendance_data = dto_dict(patch_data, only_set=True)
            attendance = await self._update(attendance_id, attendance_data)
            result = self._to_dto(attendance)
            await uow.commit()
        return result

    async def create_for_principal(
        self,
        collective_id: UUID,
        participation_id: UUID,
        data: MeAttendanceCreateDataDTO,
    ) -> AttendanceDTO:
        async with self.uow as uow:
            compose = cast("ParticipationComposeUOW | EventComposeUOW", uow)
            participation = await compose.participations.get_by_id(participation_id)
            if not participation or participation.collective_id != collective_id:
                raise ParticipationNotExistsException()

            member = await compose.members.get_by_id(data.member_id)
            if not member or member.collective_id != collective_id:
                raise MemberNotExistsException()

            attendance_create = AttendanceCreateDTO(
                member_id=data.member_id,
                participation_id=participation_id,
                is_attended=data.is_attended,
                is_verified=data.is_verified,
                comment=data.comment,
            )
            attendance = await self._create(attendance_create)
            result = self._to_dto(attendance)
            await uow.commit()
            await notify_event_targets(uow, attendance_ids=[attendance.id])
        return result

    async def verify_by_participation(
        self, participation_id: UUID
    ) -> list[AttendanceDTO]:
        async with self.uow as uow:
            for att in await uow.attendances.of_participation(participation_id):
                att.is_verified = True

            await uow.commit()

            attendances = await uow.attendances.of_participation(participation_id)
            return [self._to_dto(att) for att in attendances]

    async def get_mine_for_event(
        self, person_id: UUID, event_id: UUID
    ) -> list[AttendanceDTO]:
        """Resolves the caller's own attendance row(s) for ``event_id`` across
        every collective they're a member of. Self-service lookup so a caller
        (e.g. the Telegram bot's attendance buttons) can act without already
        knowing member_id/attendance_id — a person is usually in one
        collective participating in a given event, but not guaranteed to be."""
        async with self.uow as uow:
            rows = await uow.attendances.of_person_in_event(person_id, event_id)
            return [self._to_dto(row) for row in rows]

    async def search(
        self, filter: AttendanceFilterDTO, page_params: PageParamDTO = PageParamDTO()
    ) -> PageDTO[AttendanceDTO]:
        async with self.uow as uow:
            orm_filter = AttendanceFilter.from_dto(filter)
            items, total = await uow.attendances.search(orm_filter, page_params)
            return PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
