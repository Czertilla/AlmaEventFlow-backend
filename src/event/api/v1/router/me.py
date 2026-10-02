from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses
from core.schema.user import UserJWT
from core.schema.v1.pagination import PageParamV1, PageV1
from event.api.v1.schema.attendance import (
    AttendancePatch,
    AttendancePatchData,
    AttendancePrincipalPatchData,
    AttendanceRead,
)
from event.api.v1.schema.collective import MyCollectiveRead
from event.api.v1.schema.event import (
    EventPatch,
    EventPatchData,
    EventPut,
    EventPutData,
    EventRead,
)
from event.api.v1.schema.me import (
    MeAttendanceCreateData,
    MeEventCreate,
    MeEventRead,
    MeParticipationCreate,
)
from event.api.v1.schema.member import (
    MemberCreate,
    MemberCreateData,
    MemberPatchData,
    MemberRead,
)
from event.api.v1.schema.participation import ParticipationRead
from event.api.v1.schema.role import (
    RoleCreate,
    RolePatch,
    RolePatchData,
    RoleRead,
)
from event.api.v1.schema.stage import (
    StageCreateData,
    StagePatch,
    StagePatchData,
    StageRead,
)
from event.dependency.attendance import AttendanceUOWDep
from event.dependency.collective import CollectiveUOWDep
from event.dependency.me import EventComposeUOWDep, ParticipationComposeUOWDep
from event.dependency.member import MemberUOWDep
from event.dependency.principal import (
    verify_collective_principal,
    verify_member_person,
)
from event.dependency.role import RoleUOWDep
from event.dto.principal import CollectivePrincipalDTO, MemberIdentityDTO
from event.filter.member import MemberFilter
from event.filter.role import RoleFilter
from event.service.attendance import AttendanceService
from event.service.collective import CollectiveService
from event.service.event import EventService
from event.service.member import MemberService
from event.service.participation import ParticipationService
from event.service.role import RoleService

router = APIRouter(prefix="/me", tags=["me"])

logger = getLogger(__name__)


@router.get("/collectives", responses={**auth_responses()})
async def get_my_collectives(
    user: UserJWTDep,
    uow: CollectiveUOWDep,
) -> list[MyCollectiveRead]:
    collectives = await CollectiveService(uow).get_my_collectives(
        user.person_id
    )
    return [MyCollectiveRead.from_dto(c) for c in collectives]


@router.get("/members", responses={**auth_responses()})
async def get_my_members(
    user: UserJWTDep,
    uow: MemberUOWDep,
) -> list[MemberRead]:
    """Членства текущего пользователя во всех коллективах (для роли участника)."""
    members = await MemberService(uow).get_my_members(user.person_id)
    return [MemberRead.from_dto(m) for m in members]


@router.get(
    "/collectives/{collective_id}/members", responses={**auth_responses()}
)
async def get_my_collective_members(
    collective_id: UUID,
    uow: MemberUOWDep,
    filter: MemberFilter = FilterDepends(MemberFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> PageV1[MemberRead]:
    filter.collective_id = collective_id
    return PageV1[MemberRead].from_dto(
        await MemberService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.post(
    "/collectives/{collective_id}/members", responses={**auth_responses()}
)
async def create_my_collective_member(
    collective_id: UUID,
    member_data: MemberCreateData,
    uow: MemberUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> MemberRead:
    member_create = MemberCreate(
        collective_id=collective_id,
        person_id=member_data.person_id,
        roles=member_data.roles,
    )
    result = await MemberService(uow).create(member_create.to_dto())
    return MemberRead.from_dto(result)


@router.patch(
    "/collectives/{collective_id}/members/{member_id}",
    responses={**auth_responses()},
)
async def patch_my_collective_member(
    collective_id: UUID,
    member_id: UUID,
    member_data: MemberPatchData,
    uow: MemberUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> MemberRead:
    result = await MemberService(uow).patch_roles(
        member_id, member_data.to_dto()
    )
    return MemberRead.from_dto(result)


@router.delete(
    "/collectives/{collective_id}/members/{member_id}",
    responses={**auth_responses()},
)
async def delete_my_collective_member(
    collective_id: UUID,
    member_id: UUID,
    uow: MemberUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> None:
    await MemberService(uow).delete(member_id)


@router.get(
    "/collectives/{collective_id}/roles", responses={**auth_responses()}
)
async def get_my_collective_roles(
    collective_id: UUID,
    uow: RoleUOWDep,
    filter: RoleFilter = FilterDepends(RoleFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> PageV1[RoleRead]:
    filter.collective_id = collective_id
    return PageV1[RoleRead].from_dto(
        await RoleService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.post(
    "/collectives/{collective_id}/roles", responses={**auth_responses()}
)
async def create_my_collective_role(
    collective_id: UUID,
    role_data: RoleCreate,
    uow: RoleUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> RoleRead:
    role_create = RoleCreate(
        collective_id=collective_id,
        name=role_data.name,
    )
    result = await RoleService(uow).create(role_create.to_dto())
    return RoleRead.from_dto(result)


@router.patch(
    "/collectives/{collective_id}/roles/{role_id}",
    responses={**auth_responses()},
)
async def patch_my_collective_role(
    collective_id: UUID,
    role_id: UUID,
    role_data: RolePatchData,
    uow: RoleUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> RoleRead:
    result = await RoleService(uow).patch(
        RolePatch(id=role_id, **role_data.model_dump()).to_dto()
    )
    return RoleRead.from_dto(result)


@router.delete(
    "/collectives/{collective_id}/roles/{role_id}",
    responses={**auth_responses()},
)
async def delete_my_collective_role(
    collective_id: UUID,
    role_id: UUID,
    uow: RoleUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
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
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> ParticipationRead:
    result = await ParticipationService(uow).create_with_attendance(
        collective_id, participation_data.to_dto()
    )
    return ParticipationRead.from_dto(result)


@router.delete(
    "/collectives/{collective_id}/participations/{event_id}",
    responses={**auth_responses()},
)
async def cancel_my_collective_participation(
    collective_id: UUID,
    event_id: UUID,
    uow: EventComposeUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> None:
    await EventService(uow).cancel_participation_for_collective(
        collective_id, event_id
    )


@router.get(
    "/events/{event_id}/attendance", responses={**auth_responses()}
)
async def get_my_event_attendance(
    event_id: UUID,
    user: UserJWTDep,
    uow: AttendanceUOWDep,
) -> list[AttendanceRead]:
    """Resolves the current user's own attendance row(s) for this event,
    without needing to already know member_id/attendance_id — e.g. for the
    Telegram bot's "mark my attendance" buttons, which only carry the
    event_id in their callback data."""
    if user.person_id is None:
        return []
    attendances = await AttendanceService(uow).get_mine_for_event(
        user.person_id, event_id
    )
    return [AttendanceRead.from_dto(a) for a in attendances]


@router.patch(
    "/members/{member_id}/attendance/{attendance_id}",
    responses={**auth_responses()},
)
async def patch_my_attendance(
    member_id: UUID,
    attendance_id: UUID,
    attendance_data: AttendancePatchData,
    uow: AttendanceUOWDep,
    _: tuple[MemberIdentityDTO, UserJWT] = Depends(verify_member_person),
) -> AttendanceRead:
    result = await AttendanceService(uow).patch_mine(
        member_id, attendance_id, attendance_data.to_dto()
    )
    return AttendanceRead.from_dto(result)


@router.get(
    "/collectives/{collective_id}/attendance/{attendance_id}",
    responses={**auth_responses()},
)
async def get_my_collective_attendance(
    collective_id: UUID,
    attendance_id: UUID,
    uow: AttendanceUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> AttendanceRead:
    return AttendanceRead.from_dto(
        await AttendanceService(uow).read(attendance_id)
    )


@router.patch(
    "/collectives/{collective_id}/attendance/{attendance_id}",
    responses={**auth_responses()},
)
async def patch_my_collective_attendance(
    collective_id: UUID,
    attendance_id: UUID,
    attendance_data: AttendancePrincipalPatchData,
    uow: AttendanceUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> AttendanceRead:
    result = await AttendanceService(uow).patch(
        AttendancePatch(id=attendance_id, **attendance_data.model_dump()).to_dto()
    )
    return AttendanceRead.from_dto(result)


@router.delete(
    "/collectives/{collective_id}/attendance/{attendance_id}",
    responses={**auth_responses()},
)
async def delete_my_collective_attendance(
    collective_id: UUID,
    attendance_id: UUID,
    uow: AttendanceUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
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
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> list[AttendanceRead]:
    attendances = await AttendanceService(uow).verify_by_participation(
        participation_id
    )
    return [AttendanceRead.from_dto(a) for a in attendances]


@router.post("/events", responses={**auth_responses()})
async def create_my_event(
    event_data: MeEventCreate,
    user: UserJWTDep,
    uow: EventComposeUOWDep,
) -> MeEventRead:
    result = await EventService(uow).create_with_collective(
        event_data.to_dto(), user
    )
    return MeEventRead.from_dto(result)


@router.get(
    "/collectives/{collective_id}/templates",
    responses={**auth_responses()},
)
async def get_my_collective_templates(
    collective_id: UUID,
    uow: EventComposeUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> list[EventRead]:
    """The collective's ``status=template`` events -- what a principal
    picks from via ``MeEventCreate.template_id`` when creating a new
    event, instead of filling every field out by hand."""
    events = await EventService(uow).get_templates_for_collective(
        collective_id
    )
    return [EventRead.from_dto(e) for e in events]


@router.put(
    "/collectives/{collective_id}/events/{event_id}",
    responses={**auth_responses()},
)
async def put_my_collective_event(
    collective_id: UUID,
    event_id: UUID,
    event_data: EventPutData,
    uow: EventComposeUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> EventRead:
    result = await EventService(uow).put_for_collective(
        collective_id,
        EventPut(id=event_id, **event_data.model_dump()).to_dto(),
    )
    return EventRead.from_dto(result)


@router.patch(
    "/collectives/{collective_id}/events/{event_id}",
    responses={**auth_responses()},
)
async def patch_my_collective_event(
    collective_id: UUID,
    event_id: UUID,
    event_data: EventPatchData,
    uow: EventComposeUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> EventRead:
    result = await EventService(uow).patch_for_collective(
        collective_id,
        EventPatch(id=event_id, **event_data.model_dump()).to_dto(),
    )
    return EventRead.from_dto(result)


@router.delete(
    "/collectives/{collective_id}/events/{event_id}",
    responses={**auth_responses()},
)
async def delete_my_collective_event(
    collective_id: UUID,
    event_id: UUID,
    uow: EventComposeUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
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
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> StageRead:
    result = await EventService(uow).create_stage_for_collective(
        collective_id, event_id, stage_data.to_dto()
    )
    return StageRead.from_dto(result)


@router.patch(
    "/collectives/{collective_id}/stages/{stage_id}",
    responses={**auth_responses()},
)
async def patch_my_collective_event_stage(
    collective_id: UUID,
    stage_id: UUID,
    stage_data: StagePatchData,
    uow: EventComposeUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> StageRead:
    result = await EventService(uow).patch_stage_for_collective(
        collective_id,
        StagePatch(id=stage_id, **stage_data.model_dump()).to_dto(),
    )
    return StageRead.from_dto(result)


@router.delete(
    "/collectives/{collective_id}/stages/{stage_id}",
    responses={**auth_responses()},
)
async def delete_my_collective_event_stage(
    collective_id: UUID,
    stage_id: UUID,
    uow: EventComposeUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
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
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> AttendanceRead:
    result = await AttendanceService(uow).create_for_principal(
        collective_id, participation_id, attendance_data.to_dto()
    )
    return AttendanceRead.from_dto(result)
