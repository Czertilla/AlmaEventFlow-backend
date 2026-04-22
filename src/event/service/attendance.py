from logging import getLogger
from uuid import UUID

from core.service.base import BaseService, required_transaction
from event.models.attendance import AttendanceORM
from event.schema.attendance import (
    AttendanceCreate,
    AttendancePatch,
    AttendanceRead,
)
from event.uow.attendance import AttendanceUOW

logger = getLogger(__name__)


class AttendanceService(BaseService[AttendanceUOW]):
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
    async def _delete(self, attendance_id: UUID) -> None:
        await self.uow.attendances.delete_one(attendance_id)

    async def create(
        self, attendance_create: AttendanceCreate
    ) -> AttendanceRead:
        async with self.uow as uow:
            attendance = await self._create(attendance_create)
            result = AttendanceRead.model_validate(attendance)
            await uow.commit()
        return result

    async def read(self, attendance_id: UUID) -> AttendanceRead:
        async with self.uow:
            attendance = await self._read(attendance_id)
            return AttendanceRead.model_validate(attendance)

    async def patch(self, attendance_patch: AttendancePatch) -> AttendanceRead:
        async with self.uow as uow:
            attendance_data = attendance_patch.model_dump(exclude_unset=True)
            attendance = await self._update(
                attendance_patch.id, attendance_data
            )
            result = AttendanceRead.model_validate(attendance)
            await uow.commit()
        return result

    async def delete(self, attendance_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(attendance_id)
            await uow.commit()
