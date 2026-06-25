from logging import getLogger
from uuid import UUID

from sqlalchemy import select

from core.schema.error import ErrorCode
from core.service.base import BaseService, required_transaction
from core.schema.pagination import SPage, SPageParam, SPagination
from event.filter.attendance import AttendanceFilter
from event.models.attendance import AttendanceORM
from event.schema.attendance import (
    AttendanceCreate,
    AttendancePatch,
    AttendancePatchData,
    AttendancePut,
    AttendanceRead,
)
from event.schema.me import MeAttendanceCreateData
from event.exc.event import (
    AttendanceNotExistsException,
    MemberNotExistsException,
    ParticipationNotExistsException,
)
from event.uow.attendance import AttendanceUOW
from core.utils.exc.http import VancedHTTPException
from event.uow.me import ParticipationComposeUOW
from event.service.notification import notify_event_targets

logger = getLogger(__name__)


class AttendanceService(BaseService[AttendanceUOW | ParticipationComposeUOW]):
    @required_transaction
    async def _create(
        self, attendance_create: AttendanceCreate
    ) -> AttendanceORM:
        attendance_data = attendance_create.model_dump()
        attendance = await self.uow.attendances.add_n_return(
            data=attendance_data
        )
        await self.uow.session.flush(objects=[attendance])
        return attendance

    @required_transaction
    async def _read(self, attendance_id: UUID) -> AttendanceORM | None:
        attendance = await self.uow.attendances.get_by_id(attendance_id)
        return attendance

    @required_transaction
    async def _update(
        self, attendance_id: UUID, attendance_data: dict, *, flush: bool = False
    ) -> AttendanceORM:
        attendance = await self.uow.attendances.update_one(
            attendance_id, attendance_data, flush
        )
        return attendance

    @required_transaction
    async def _upsert(self, attendance_put: AttendancePut) -> AttendanceORM:
        return await self.uow.attendances.upsert(attendance_put.model_dump())

    @required_transaction
    async def _delete(self, attendance_id: UUID) -> None:
        await self.uow.attendances.delete_one(attendance_id)

    async def create(
        self, attendance_create: AttendanceCreate
    ) -> AttendanceRead:
        async with self.uow as uow:
            attendance = await self._create(attendance_create)
            result = AttendanceRead.model_validate(attendance)
            await uow.commit()
            await notify_event_targets(uow, attendance_ids=[attendance.id])
        return result

    async def read(self, attendance_id: UUID) -> AttendanceRead:
        async with self.uow:
            attendance = await self._read(attendance_id)
            return AttendanceRead.model_validate(attendance)

    async def patch(self, attendance_patch: AttendancePatch) -> AttendanceRead:
        async with self.uow as uow:
            attendance_data = attendance_patch.model_dump()
            attendance = await self._update(
                attendance_patch.id, attendance_data
            )
            result = AttendanceRead.model_validate(attendance)
            await uow.commit()
        return result

    async def put(self, attendance_put: AttendancePut) -> AttendanceRead:
        async with self.uow as uow:
            attendance = await self._upsert(attendance_put)
            result = AttendanceRead.model_validate(attendance)
            await uow.commit()
        return result

    async def delete(self, attendance_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(attendance_id)
            await uow.commit()

    async def patch_mine(
        self, member_id: UUID, attendance_id: UUID, patch_data: AttendancePatchData
    ) -> AttendanceRead:
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

            attendance_data = patch_data.model_dump()
            attendance = await self._update(attendance_id, attendance_data)
            result = AttendanceRead.model_validate(attendance)
            await uow.commit()
        return result

    async def create_for_principal(
        self,
        collective_id: UUID,
        participation_id: UUID,
        data: MeAttendanceCreateData,
    ) -> AttendanceRead:
        async with self.uow as uow:
            participation = await uow.participations.get_by_id(participation_id)
            if not participation or participation.collective_id != collective_id:
                raise ParticipationNotExistsException()

            member = await uow.members.get_by_id(data.member_id)
            if not member or member.collective_id != collective_id:
                raise MemberNotExistsException()

            attendance_create = AttendanceCreate(
                member_id=data.member_id,
                participation_id=participation_id,
                is_attended=data.is_attended,
                is_verified=data.is_verified,
                comment=data.comment,
            )
            attendance = await self._create(attendance_create)
            result = AttendanceRead.model_validate(attendance)
            await uow.commit()
            await notify_event_targets(uow, attendance_ids=[attendance.id])
        return result

    async def verify_by_participation(self, participation_id: UUID) -> list[AttendanceRead]:
        async with self.uow as uow:
            stmt = select(AttendanceORM).where(
                AttendanceORM.participation_id == participation_id
            )
            result = await uow.session.execute(stmt)
            attendances = result.unique().scalars().all()

            for att in attendances:
                att.is_verified = True

            await uow.commit()

            result = await uow.session.execute(stmt)
            attendances = result.unique().scalars().all()
            return [AttendanceRead.model_validate(att) for att in attendances]

    async def search(self, filter: AttendanceFilter, page_params: SPageParam = SPageParam()) -> SPage[AttendanceRead]:
        async with self.uow as uow:
            items, total = await uow.attendances.search(filter, page_params)
            return SPage(
                items=[AttendanceRead.model_validate(item) for item in items],
                pagination=SPagination(
                    page=page_params.page, limit=page_params.limit, total=total),
            )
