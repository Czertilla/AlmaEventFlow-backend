from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.filter.depends import FilterDepends
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from event.api.v1.schema.member import (
    MemberCreate,
    MemberPatch,
    MemberPatchData,
    MemberPut,
    MemberPutData,
    MemberRead,
)
from event.dependency.member import MemberUOWDep
from event.filter.member import MemberFilter
from event.service.member import MemberService

router = APIRouter(prefix="/members", tags=["member"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def get_members(
    uow: MemberUOWDep,
    user: UserJWTDep,
    filter: MemberFilter = FilterDepends(MemberFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[MemberRead]:
    return PageV1[MemberRead].from_dto(
        await MemberService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.post("", responses={**auth_responses()})
async def create_member(
    member: MemberCreate, user: SuperUserJWTDep, uow: MemberUOWDep
) -> MemberRead:
    return MemberRead.from_dto(await MemberService(uow).create(member.to_dto()))


@router.get(
    "/{member_id}",
    responses={**auth_responses(), **entity_not_found_responses("member")},
)
async def get_member(
    member_id: UUID, user: UserJWTDep, uow: MemberUOWDep
) -> MemberRead:
    return MemberRead.from_dto(await MemberService(uow).read(member_id))


@router.put(
    "/{member_id}",
    responses={**auth_responses(), **entity_not_found_responses("member")},
)
async def put_member(
    member_id: UUID, member: MemberPutData, user: SuperUserJWTDep, uow: MemberUOWDep
) -> MemberRead:
    result = await MemberService(uow).put(
        MemberPut(id=member_id, **member.model_dump()).to_dto()
    )
    return MemberRead.from_dto(result)


@router.patch(
    "/{member_id}",
    responses={**auth_responses(), **entity_not_found_responses("member")},
)
async def patch_member(
    member_id: UUID,
    member: MemberPatchData,
    user: SuperUserJWTDep,
    uow: MemberUOWDep,
) -> MemberRead:
    result = await MemberService(uow).patch(
        MemberPatch(id=member_id, **member.model_dump()).to_dto()
    )
    return MemberRead.from_dto(result)


@router.delete(
    "/{member_id}",
    responses={**auth_responses(), **entity_not_found_responses("member")},
)
async def delete_member(
    member_id: UUID, user: SuperUserJWTDep, uow: MemberUOWDep
) -> None:
    await MemberService(uow).delete(member_id)
