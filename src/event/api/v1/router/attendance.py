from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.filter.depends import FilterDepends
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from event.api.v1.schema.attendance import (
    AttendanceCreate,
    AttendancePatch,
    AttendancePatchData,
    AttendancePut,
    AttendancePutData,
    AttendanceRead,
)
from event.dependency.attendance import AttendanceUOWDep
from event.filter.attendance import AttendanceFilter
from event.service.attendance import AttendanceService

logger = getLogger(__name__)


router = APIRouter(prefix="/attendances", tags=["attendance"])


@router.get("", responses={**auth_responses()})
async def get_attendances(
    uow: AttendanceUOWDep,
    user: UserJWTDep,
    filter: AttendanceFilter = FilterDepends(AttendanceFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[AttendanceRead]:
    return PageV1[AttendanceRead].from_dto(
        await AttendanceService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.post("", responses={**auth_responses()})
async def create_attendance(
    attendance: AttendanceCreate,
    user: SuperUserJWTDep,
    uow: AttendanceUOWDep,
) -> AttendanceRead:
    return AttendanceRead.from_dto(
        await AttendanceService(uow).create(attendance.to_dto())
    )


@router.get(
    "/{attendance_id}",
    responses={**auth_responses(), **entity_not_found_responses("attendance")},
)
async def get_attendance(
    attendance_id: UUID, user: UserJWTDep, uow: AttendanceUOWDep
) -> AttendanceRead:
    return AttendanceRead.from_dto(
        await AttendanceService(uow).read(attendance_id)
    )


@router.put(
    "/{attendance_id}",
    responses={**auth_responses(), **entity_not_found_responses("attendance")},
)
async def put_attendance(
    attendance_id: UUID,
    attendance: AttendancePutData,
    user: SuperUserJWTDep,
    uow: AttendanceUOWDep,
) -> AttendanceRead:
    result = await AttendanceService(uow).put(
        AttendancePut(id=attendance_id, **attendance.model_dump()).to_dto()
    )
    return AttendanceRead.from_dto(result)


@router.patch(
    "/{attendance_id}",
    responses={**auth_responses(), **entity_not_found_responses("attendance")},
)
async def patch_attendance(
    attendance_id: UUID,
    attendance: AttendancePatchData,
    user: SuperUserJWTDep,
    uow: AttendanceUOWDep,
) -> AttendanceRead:
    result = await AttendanceService(uow).patch(
        AttendancePatch(id=attendance_id, **attendance.model_dump()).to_dto()
    )
    return AttendanceRead.from_dto(result)


@router.delete(
    "/{attendance_id}",
    responses={**auth_responses(), **entity_not_found_responses("attendance")},
)
async def delete_attendance(
    attendance_id: UUID, user: SuperUserJWTDep, uow: AttendanceUOWDep
) -> None:
    await AttendanceService(uow).delete(attendance_id)
