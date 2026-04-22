from uuid import UUID
from fastapi import APIRouter
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep

from event.dependency.attendance import AttendanceUOWDep
from event.service.attendance import AttendanceService

from ...schema.attendance import (
    AttendanceCreate,
    AttendancePatch,
    AttendancePatchData,
    AttendancePut,
    AttendancePutData,
    AttendanceRead,
)


logger = getLogger(__name__)


router = APIRouter(prefix="/attendances", tags=["attendance"])


@router.post("")
async def create_attendance(
    attendance: AttendanceCreate,
    user=SuperUserJWTDep,
    uow=AttendanceUOWDep,
) -> AttendanceRead:
    return await AttendanceService(uow).create(attendance)


@router.get("/{attendance_id}")
async def get_attendance(
    attendance_id: UUID, user=UserJWTDep, uow=AttendanceUOWDep
) -> AttendanceRead:
    return await AttendanceService(uow).read(attendance_id)


@router.put("/{attendance_id}")
async def put_attendance(
    attendance_id: UUID,
    attendance: AttendancePutData,
    user=SuperUserJWTDep,
    uow=AttendanceUOWDep,
) -> AttendanceRead:
    return await AttendanceService(uow).put(
        AttendancePut(**attendance.model_dump(), id=attendance_id)
    )


@router.patch("/{attendance_id}")
async def patch_attendance(
    attendance_id: UUID,
    attendance: AttendancePatchData,
    user=SuperUserJWTDep,
    uow=AttendanceUOWDep,
) -> AttendanceRead:
    return await AttendanceService(uow).patch(
        AttendancePatch(**attendance.model_dump(), id=attendance_id)
    )


@router.delete("/{attendance_id}")
async def delete_attendance(
    attendance_id: UUID, user=SuperUserJWTDep, uow=AttendanceUOWDep
) -> None:
    await AttendanceService(uow).delete(attendance_id)
