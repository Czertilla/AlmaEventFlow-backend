from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.pagination import SPage, SPageParam

from event.dependency.attendance import AttendanceUOWDep
from event.filter.attendance import AttendanceFilter
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


@router.get("", responses={**auth_responses()})
async def get_attendances(
    uow: AttendanceUOWDep,
    user: UserJWTDep,
    filter: AttendanceFilter = FilterDepends(AttendanceFilter),
    page_param=Depends(SPageParam),
) -> SPage[AttendanceRead]:
    return await AttendanceService(uow).search(filter, page_param)


@router.post("", responses={**auth_responses()})
async def create_attendance(
    attendance: AttendanceCreate,
    user: SuperUserJWTDep,
    uow: AttendanceUOWDep,
) -> AttendanceRead:
    return await AttendanceService(uow).create(attendance)


@router.get("/{attendance_id}", responses={**auth_responses(), **entity_not_found_responses("attendance")})
async def get_attendance(
    attendance_id: UUID, user: UserJWTDep, uow: AttendanceUOWDep
) -> AttendanceRead:
    return await AttendanceService(uow).read(attendance_id)


@router.put("/{attendance_id}", responses={**auth_responses(), **entity_not_found_responses("attendance")})
async def put_attendance(
    attendance_id: UUID,
    attendance: AttendancePutData,
    user: SuperUserJWTDep,
    uow: AttendanceUOWDep,
) -> AttendanceRead:
    return await AttendanceService(uow).put(
        AttendancePut(id=attendance_id, **attendance.model_dump())
    )


@router.patch("/{attendance_id}", responses={**auth_responses(), **entity_not_found_responses("attendance")})
async def patch_attendance(
    attendance_id: UUID,
    attendance: AttendancePatchData,
    user: SuperUserJWTDep,
    uow: AttendanceUOWDep,
) -> AttendanceRead:
    return await AttendanceService(uow).patch(
        AttendancePatch(id=attendance_id, **attendance.model_dump())
    )


@router.delete("/{attendance_id}", responses={**auth_responses(), **entity_not_found_responses("attendance")})
async def delete_attendance(
    attendance_id: UUID, user: SuperUserJWTDep, uow: AttendanceUOWDep
) -> None:
    await AttendanceService(uow).delete(attendance_id)
