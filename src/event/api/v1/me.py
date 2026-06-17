from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from logging import getLogger

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses
from core.schema.pagination import SPage, SPageParam
from core.schema.user import UserJWT
from event.dependency.collective import CollectiveUOWDep
from event.dependency.member import MemberUOWDep
from event.dependency.principal import (
    verify_collective_principal,
    verify_member_person,
)
from event.dependency.role import RoleUOWDep
from event.dependency.attendance import AttendanceUOWDep
from event.dependency.me import EventComposeUOWDep, ParticipationComposeUOWDep
from event.filter.member import MemberFilter
from event.filter.role import RoleFilter
from event.models.collective import CollectiveORM
from event.models.member import MemberORM
from event.schema.attendance import (
    AttendancePatch,
    AttendancePatchData,
    AttendancePrincipalPatchData,
    AttendanceRead,
)
from event.schema.event import (
    EventPatch,
    EventPatchData,
    EventPut,
    EventPutData,
    EventRead,
)
from event.schema.member import (
    MemberCreate,
    MemberCreateData,
    MemberPatchData,
    MemberRead,
)
from event.schema.role import (
    RoleCreate,
    RolePatch,
    RolePatchData,
    RoleRead,
)
from event.schema.participation import ParticipationRead
from event.schema.stage import (
    StageCreateData,
    StagePatch,
    StagePatchData,
    StageRead,
)
from event.schema.me import (
    MeAttendanceCreateData,
    MeEventCreate,
    MeEventRead,
    MeParticipationCreate,
)
from event.service.member import MemberService
from event.service.role import RoleService
from event.service.participation import ParticipationService
from event.service.attendance import AttendanceService
from event.service.event import EventService

router = APIRouter(prefix="/me", tags=["me"])

logger = getLogger(__name__)


@router.get("/collectives", response_model=None, responses={**auth_responses()})
async def get_my_collectives(
    user: UserJWTDep,
    collective_uow: CollectiveUOWDep,
) -> list[dict]:
    async with collective_uow as uow:
        return [
            {
                "id": c.id,
                "principal_id": c.principal_id,
                "is_verified": c.is_verified,
            }
            for c in await uow.collectives.get_by_principal_id(user.person_id)
        ]


@router.get(
    "/collectives/{collective_id}/members", responses={**auth_responses()}
)
async def get_my_collective_members(
    collective_id: UUID,
    uow: MemberUOWDep,
    filter: MemberFilter = FilterDepends(MemberFilter),
    page_param: SPageParam = Depends(SPageParam),
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> SPage[MemberRead]:
    filter.collective_id = collective_id
    return await MemberService(uow).search(filter, page_param)


@router.post(
    "/collectives/{collective_id}/members", responses={**auth_responses()}
)
async def create_my_collective_member(
    collective_id: UUID,
    member_data: MemberCreateData,
    uow: MemberUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> MemberRead:
    member_create = MemberCreate(
        collective_id=collective_id,
        person_id=member_data.person_id,
        roles=member_data.roles,
    )
    return await MemberService(uow).create(member_create)


@router.patch(
    "/collectives/{collective_id}/members/{member_id}",
    responses={**auth_responses()},
)
async def patch_my_collective_member(
    collective_id: UUID,
    member_id: UUID,
    member_data: MemberPatchData,
    uow: MemberUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> MemberRead:
    return await MemberService(uow).patch_roles(member_id, member_data)


@router.delete(
    "/collectives/{collective_id}/members/{member_id}",
    responses={**auth_responses()},
)
async def delete_my_collective_member(
    collective_id: UUID,
    member_id: UUID,
    uow: MemberUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> None:
    await MemberService(uow).delete(member_id)


@router.get(
    "/collectives/{collective_id}/roles", responses={**auth_responses()}
)
async def get_my_collective_roles(
    collective_id: UUID,
    uow: RoleUOWDep,
    filter: RoleFilter = FilterDepends(RoleFilter),
    page_param: SPageParam = Depends(SPageParam),
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> SPage[RoleRead]:
    filter.collective_id = collective_id
    return await RoleService(uow).search(filter, page_param)


@router.post(
    "/collectives/{collective_id}/roles", responses={**auth_responses()}
)
async def create_my_collective_role(
    collective_id: UUID,
    role_data: RoleCreate,
    uow: RoleUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> RoleRead:
    role_create = RoleCreate(
        collective_id=collective_id,
        name=role_data.name,
    )
    return await RoleService(uow).create(role_create)


@router.patch(
    "/collectives/{collective_id}/roles/{role_id}",
    responses={**auth_responses()},
)
async def patch_my_collective_role(
    collective_id: UUID,
    role_id: UUID,
    role_data: RolePatchData,
    uow: RoleUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> RoleRead:
    return await RoleService(uow).patch(
        RolePatch(id=role_id, **role_data.model_dump())
    )


@router.delete(
    "/collectives/{collective_id}/roles/{role_id}",
    responses={**auth_responses()},
)
async def delete_my_collective_role(
    collective_id: UUID,
    role_id: UUID,
    uow: RoleUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> None:
    await RoleService(uow).delete(role_id)


@router.post(
    "/collectives/{collective_id}/participations",
    responses={**auth_responses()},
)
async def create_my_collective_participation(
    collective_id: UUID,
    participation_data: MeParticipationCreate,
    uow: ParticipationComposeUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> ParticipationRead:
    return await ParticipationService(uow).create_with_attendance(
        collective_id, participation_data
    )


@router.delete(
    "/collectives/{collective_id}/participations/{event_id}",
    responses={**auth_responses()},
)
async def cancel_my_collective_participation(
    collective_id: UUID,
    event_id: UUID,
    uow: EventComposeUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> None:
    await EventService(uow).cancel_participation_for_collective(
        collective_id, event_id
    )


@router.patch(
    "/members/{member_id}/attendance/{attendance_id}",
    responses={**auth_responses()},
)
async def patch_my_attendance(
    member_id: UUID,
    attendance_id: UUID,
    attendance_data: AttendancePatchData,
    uow: AttendanceUOWDep,
    _: tuple[MemberORM, UserJWT] = Depends(verify_member_person),
) -> AttendanceRead:
    return await AttendanceService(uow).patch_mine(
        member_id, attendance_id, attendance_data
    )


@router.get(
    "/collectives/{collective_id}/attendance/{attendance_id}",
    responses={**auth_responses()},
)
async def get_my_collective_attendance(
    collective_id: UUID,
    attendance_id: UUID,
    uow: AttendanceUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> AttendanceRead:
    return await AttendanceService(uow).read(attendance_id)


@router.patch(
    "/collectives/{collective_id}/attendance/{attendance_id}",
    responses={**auth_responses()},
)
async def patch_my_collective_attendance(
    collective_id: UUID,
    attendance_id: UUID,
    attendance_data: AttendancePrincipalPatchData,
    uow: AttendanceUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> AttendanceRead:
    return await AttendanceService(uow).patch(
        AttendancePatch(id=attendance_id, **attendance_data.model_dump())
    )


@router.delete(
    "/collectives/{collective_id}/attendance/{attendance_id}",
    responses={**auth_responses()},
)
async def delete_my_collective_attendance(
    collective_id: UUID,
    attendance_id: UUID,
    uow: AttendanceUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> None:
    await AttendanceService(uow).delete(attendance_id)


@router.post(
    "/collectives/{collective_id}/participation/{participation_id}/attendance/verify",
    responses={**auth_responses()},
)
async def verify_my_collective_attendance(
    collective_id: UUID,
    participation_id: UUID,
    uow: AttendanceUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> list[AttendanceRead]:
    return await AttendanceService(uow).verify_by_participation(
        participation_id
    )


@router.post("/events", responses={**auth_responses()})
async def create_my_event(
    event_data: MeEventCreate,
    user: UserJWTDep,
    uow: EventComposeUOWDep,
) -> MeEventRead:
    return await EventService(uow).create_with_collective(event_data, user)


@router.put(
    "/collectives/{collective_id}/events/{event_id}",
    responses={**auth_responses()},
)
async def put_my_collective_event(
    collective_id: UUID,
    event_id: UUID,
    event_data: EventPutData,
    uow: EventComposeUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> EventRead:
    return await EventService(uow).put_for_collective(
        collective_id, EventPut(id=event_id, **event_data.model_dump())
    )


@router.patch(
    "/collectives/{collective_id}/events/{event_id}",
    responses={**auth_responses()},
)
async def patch_my_collective_event(
    collective_id: UUID,
    event_id: UUID,
    event_data: EventPatchData,
    uow: EventComposeUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> EventRead:
    return await EventService(uow).patch_for_collective(
        collective_id, EventPatch(id=event_id, **event_data.model_dump())
    )


@router.delete(
    "/collectives/{collective_id}/events/{event_id}",
    responses={**auth_responses()},
)
async def delete_my_collective_event(
    collective_id: UUID,
    event_id: UUID,
    uow: EventComposeUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> None:
    await EventService(uow).delete_for_collective(collective_id, event_id)


@router.post(
    "/collectives/{collective_id}/events/{event_id}/stages",
    responses={**auth_responses()},
)
async def create_my_collective_event_stage(
    collective_id: UUID,
    event_id: UUID,
    stage_data: StageCreateData,
    uow: EventComposeUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> StageRead:
    return await EventService(uow).create_stage_for_collective(
        collective_id, event_id, stage_data
    )


@router.patch(
    "/collectives/{collective_id}/stages/{stage_id}",
    responses={**auth_responses()},
)
async def patch_my_collective_event_stage(
    collective_id: UUID,
    stage_id: UUID,
    stage_data: StagePatchData,
    uow: EventComposeUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> StageRead:
    return await EventService(uow).patch_stage_for_collective(
        collective_id, StagePatch(id=stage_id, **stage_data.model_dump())
    )


@router.delete(
    "/collectives/{collective_id}/stages/{stage_id}",
    responses={**auth_responses()},
)
async def delete_my_collective_event_stage(
    collective_id: UUID,
    stage_id: UUID,
    uow: EventComposeUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> None:
    await EventService(uow).delete_stage_for_collective(collective_id, stage_id)


@router.post(
    "/collectives/{collective_id}/participation/{participation_id}/attendance",
    responses={**auth_responses()},
)
async def create_my_collective_attendance(
    collective_id: UUID,
    participation_id: UUID,
    attendance_data: MeAttendanceCreateData,
    uow: ParticipationComposeUOWDep,
    _: tuple[CollectiveORM, UserJWT] = Depends(verify_collective_principal),
) -> AttendanceRead:
    return await AttendanceService(uow).create_for_principal(
        collective_id, participation_id, attendance_data
    )
