from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.pagination import SPage, SPageParam
from event.dependency.member import MemberUOWDep
from event.filter.member import MemberFilter
from ...schema.member import (
    MemberCreate,
    MemberPatch,
    MemberPatchData,
    MemberPut,
    MemberPutData,
    MemberRead,
)
from event.service.member import MemberService

router = APIRouter(prefix="/members", tags=["member"])

logger = getLogger(__name__)


@router.get("")
async def get_members(
    uow: MemberUOWDep,
    user: UserJWTDep,
    filter: MemberFilter = FilterDepends(MemberFilter),
    page_param=Depends(SPageParam),
) -> SPage[MemberRead]:
    return await MemberService(uow).search(filter, page_param)


@router.post("")
async def create_member(
    member: MemberCreate, user: SuperUserJWTDep, uow: MemberUOWDep
) -> MemberRead:
    return await MemberService(uow).create(member)


@router.get("/{member_id}")
async def get_member(
    member_id: UUID, user: UserJWTDep, uow: MemberUOWDep
) -> MemberRead:
    return await MemberService(uow).read(member_id)


@router.put("/{member_id}")
async def put_member(
    member_id: UUID, member: MemberPut, user: SuperUserJWTDep, uow: MemberUOWDep
) -> MemberRead:
    return await MemberService(uow).put(
        MemberPutData(**member.model_dump(), id=member_id)
    )


@router.patch("/{member_id}")
async def patch_member(
    member_id: UUID,
    member: MemberPatch,
    user: SuperUserJWTDep,
    uow: MemberUOWDep,
) -> MemberRead:
    return await MemberService(uow).patch(
        MemberPatchData(**member.model_dump(), id=member_id)
    )


@router.delete("/{member_id}")
async def delete_member(
    member_id: UUID, user: SuperUserJWTDep, uow: MemberUOWDep
) -> None:
    await MemberService(uow).delete(member_id)
