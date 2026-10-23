from uuid import UUID

from fastapi import APIRouter

from core.dependencies.auth import UserJWTDep
from core.schema.error import (
    ErrorCode,
    auth_responses,
    detail_403,
    entity_not_found_responses,
)
from event.api.v2.schema.attendance import (
    AttendanceChanged,
    AttendanceChangeData,
    AttendanceDeclareData,
)
from event.dependency.attendance_change import AttendanceChangeUOWDep
from event.dto.member_profile import ProfileViewerDTO
from event.service.attendance_change import AttendanceChangeService

router = APIRouter(prefix="/attendances", tags=["attendance"])


@router.post(
    "",
    responses={
        **auth_responses(),
        **entity_not_found_responses("participation"),
        **detail_403(ErrorCode.NOT_COLLECTIVE_PRINCIPAL),
    },
)
async def declare_attendance(
    data: AttendanceDeclareData, user: UserJWTDep, uow: AttendanceChangeUOWDep
) -> AttendanceChanged:
    """Adds a member of the collective to the event. The new place is not marked:
    its `is_attended` is `null` until someone marks it. Only the leader of the
    collective and a superuser may; an existing place is returned unchanged."""
    viewer = ProfileViewerDTO(
        person_id=user.person_id, is_superuser=user.is_superuser
    )
    return AttendanceChanged.from_dto(
        await AttendanceChangeService(uow).declare(data.to_dto(), viewer)
    )


@router.patch(
    "/{attendance_id}",
    responses={
        **auth_responses(),
        **entity_not_found_responses("attendance"),
        **detail_403(ErrorCode.NOT_MEMBER_PERSON),
    },
)
async def change_attendance(
    attendance_id: UUID,
    data: AttendanceChangeData,
    user: UserJWTDep,
    uow: AttendanceChangeUOWDep,
) -> AttendanceChanged:
    """Marks a place, comments on it or (the leader) verifies it. One endpoint for
    whoever may: the member of the place, the leader of the collective, a superuser."""
    viewer = ProfileViewerDTO(
        person_id=user.person_id, is_superuser=user.is_superuser
    )
    return AttendanceChanged.from_dto(
        await AttendanceChangeService(uow).change(
            attendance_id, data.to_dto(), viewer
        )
    )
